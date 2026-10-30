import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import Settings, get_settings
from app.schemas.detection import (
    DetectionResultData,
    FaceBoundingBox,
    FaceTrackItem,
    TrackSelectionResultData,
    VideoMetadataDetail,
)
from app.services.database import DatabaseService, get_database_service
from app.services.face_detector import FaceDetectorYuNet
from app.services.face_tracker import FaceTracker
from app.services.project_service import current_iso_timestamp
from app.services.storage_service import (
    BaseStorageService,
    get_storage_service,
)
from app.services.video_service import VideoProcessingError, VideoService

logger = logging.getLogger("bollyswap.services.detection")


class DetectionService:
    """
    Coordinates end-to-end video face detection, OpenCV YuNet inference,
    track hypothesis clustering, thumbnail storage, and MongoDB synchronization.
    """

    def __init__(
        self,
        settings: Settings,
        db_service: DatabaseService,
        storage_service: BaseStorageService,
        video_service: Optional[VideoService] = None,
        face_detector: Optional[FaceDetectorYuNet] = None,
        face_tracker: Optional[FaceTracker] = None,
    ):
        self.settings = settings
        self.db_service = db_service
        self.storage_service = storage_service
        self.video_service = video_service or VideoService(
            sample_interval_seconds=settings.VIDEO_SAMPLE_INTERVAL_SECONDS,
            max_sampled_frames=settings.VIDEO_MAX_SAMPLED_FRAMES,
            max_frame_dimension=settings.VIDEO_MAX_FRAME_DIMENSION,
        )
        self.face_detector = face_detector
        self.face_tracker = face_tracker or FaceTracker()

    def _get_detector(self) -> FaceDetectorYuNet:
        """Lazy initializer for YuNet detector to support test mocking if needed."""
        if self.face_detector is None:
            self.face_detector = FaceDetectorYuNet(
                model_path=self.settings.resolved_yunet_model_path,
                confidence_threshold=self.settings.FACE_DETECTION_CONFIDENCE_THRESHOLD,
                nms_threshold=self.settings.FACE_DETECTION_NMS_THRESHOLD,
            )
        return self.face_detector

    async def run_detection(
        self,
        project_id: str,
        video_id: str,
        force_reprocess: bool = False,
    ) -> DetectionResultData:
        """
        Executes real AI face detection on the uploaded video:
        1. Checks for existing completed detection job (prevents redundant processing)
        2. Inspects video and extracts sampled frames
        3. Runs YuNet face detection on sampled frames
        4. Clusters continuous face tracks (IoU + temporal)
        5. Generates and stores bounded thumbnails
        6. Persists structured results to MongoDB
        """
        if not self.db_service.is_connected:
            raise RuntimeError("Database service is offline. MongoDB Atlas is required for detection jobs.")

        jobs_col = self.db_service.get_collection("detection_jobs")
        projects_col = self.db_service.get_collection("projects")
        uploads_col = self.db_service.get_collection("uploads")

        # 1. Check existing completed job for this project/video unless force_reprocess is True
        if not force_reprocess:
            existing = await jobs_col.find_one(
                {"project_id": project_id, "video_id": video_id, "detection_status": "completed"}
            )
            if existing:
                existing.pop("_id", None)
                logger.info("Found existing completed detection job: %s", existing.get("detection_job_id"))
                return DetectionResultData(**existing)

        # 2. Retrieve video upload metadata
        video_doc = await uploads_col.find_one({"upload_id": video_id})
        if not video_doc:
            raise ValueError(f"Video with ID '{video_id}' was not found in storage records.")

        video_path = self.storage_service.get_file_path(video_doc["storage_path"])
        if not video_path.exists():
            raise FileNotFoundError(f"Source video file not found at path: {video_path.name}")

        detection_job_id = f"det_{uuid.uuid4().hex[:12]}"
        now = current_iso_timestamp()

        # Initialize job record in MongoDB
        job_record = {
            "detection_job_id": detection_job_id,
            "project_id": project_id,
            "video_id": video_id,
            "detection_status": "extracting_frames",
            "progress": 0.15,
            "current_stage": "Extracting and sampling video frames",
            "created_at": now,
            "completed_at": None,
            "tracks": [],
            "sampled_frame_count": 0,
            "detected_face_count": 0,
            "selected_track_id": None,
            "error_message": None,
        }
        await jobs_col.insert_one(job_record)

        try:
            # Stage A: Video inspection & frame extraction
            metadata = self.video_service.inspect_video(video_path)
            meta_detail = VideoMetadataDetail(
                width=metadata.width,
                height=metadata.height,
                fps=metadata.fps,
                durationSeconds=metadata.duration_seconds,
                frameCount=metadata.frame_count,
            )

            sampled_frames = self.video_service.sample_frames(video_path)
            await jobs_col.update_one(
                {"detection_job_id": detection_job_id},
                {
                    "$set": {
                        "detection_status": "detecting_faces",
                        "progress": 0.45,
                        "current_stage": f"Running YuNet face detection across {len(sampled_frames)} sampled frames",
                        "video_metadata": meta_detail.model_dump(by_alias=True),
                        "sampled_frame_count": len(sampled_frames),
                    }
                },
            )

            # Stage B: YuNet Face Detection
            detector = self._get_detector()
            all_detections = detector.detect_in_video_frames(sampled_frames)

            await jobs_col.update_one(
                {"detection_job_id": detection_job_id},
                {
                    "$set": {
                        "detection_status": "grouping_tracks",
                        "progress": 0.75,
                        "current_stage": f"Grouping {len(all_detections)} face detections into actor track hypotheses",
                        "detected_face_count": len(all_detections),
                    }
                },
            )

            # Stage C: Face Tracking & Thumbnail Storage
            track_hypotheses = self.face_tracker.cluster_tracks(all_detections)
            final_tracks: List[FaceTrackItem] = []

            for track in track_hypotheses:
                rep_det = track.representative_detection

                # Save cropped thumbnail bytes via Storage abstraction
                thumb_storage = await self.storage_service.save_bytes(
                    data=rep_det.thumbnail_bytes,
                    subfolder="faces",
                    extension="jpg",
                    prefix=f"thumb_{track.track_id}",
                    content_type="image/jpeg",
                    original_filename=f"{track.track_id}_rep.jpg",
                )

                # Persist thumbnail upload record in uploads collection
                await uploads_col.insert_one(
                    {
                        "upload_id": thumb_storage.upload_id,
                        "file_type": "thumbnail",
                        "filename": thumb_storage.filename,
                        "original_filename": thumb_storage.original_filename,
                        "content_type": thumb_storage.content_type,
                        "size_bytes": thumb_storage.size_bytes,
                        "storage_path": thumb_storage.storage_path,
                        "created_at": current_iso_timestamp(),
                    }
                )

                thumbnail_url = f"{self.settings.API_PREFIX}/files/{thumb_storage.upload_id}"

                final_tracks.append(
                    FaceTrackItem(
                        trackId=track.track_id,
                        label=track.label,
                        confidence=track.average_confidence,
                        thumbnailFileId=thumb_storage.upload_id,
                        thumbnailUrl=thumbnail_url,
                        occurrences=track.occurrences,
                        timestamps=track.timestamps,
                        boundingBox=FaceBoundingBox(
                            x=rep_det.bbox[0],
                            y=rep_det.bbox[1],
                            width=rep_det.bbox[2],
                            height=rep_det.bbox[3],
                        ),
                        landmarks=rep_det.landmarks,
                    )
                )

            # Default selected track to the first track if any tracks were detected
            default_selected_track = final_tracks[0].track_id if final_tracks else None
            completed_time = current_iso_timestamp()

            result_data = DetectionResultData(
                detectionJobId=detection_job_id,
                projectId=project_id,
                videoId=video_id,
                detectionStatus="completed",
                progress=1.0,
                currentStage="Face detection and actor track grouping complete",
                videoMetadata=meta_detail,
                sampledFrameCount=len(sampled_frames),
                detectedFaceCount=len(all_detections),
                tracks=final_tracks,
                selectedTrackId=default_selected_track,
                createdAt=now,
                completedAt=completed_time,
            )

            # Update detection job in MongoDB
            await jobs_col.update_one(
                {"detection_job_id": detection_job_id},
                {"$set": result_data.model_dump(by_alias=True)},
            )

            # Update project in MongoDB with detected tracks and default track selection
            await projects_col.update_one(
                {"project_id": project_id},
                {
                    "$set": {
                        "detected_tracks": [t.model_dump(by_alias=True) for t in final_tracks],
                        "selected_actor_track_id": default_selected_track,
                        "detection_job_id": detection_job_id,
                        "status": "awaiting_face_selection" if final_tracks else "no_faces_detected",
                        "updated_at": completed_time,
                    }
                },
            )

            logger.info(
                "Face detection completed for project %s: %d tracks, %d faces",
                project_id,
                len(final_tracks),
                len(all_detections),
            )
            return result_data

        except Exception as e:
            logger.exception("Face detection pipeline failed for project %s", project_id)
            err_msg = str(e) or type(e).__name__
            await jobs_col.update_one(
                {"detection_job_id": detection_job_id},
                {
                    "$set": {
                        "detection_status": "failed",
                        "error_message": err_msg,
                        "current_stage": f"Failed: {err_msg}",
                        "completed_at": current_iso_timestamp(),
                    }
                },
            )
            raise

    async def get_detection_job(self, detection_job_id: str) -> Optional[DetectionResultData]:
        """Retrieves face detection job status and results by detection_job_id."""
        if not self.db_service.is_connected:
            raise RuntimeError("Database service is offline.")

        jobs_col = self.db_service.get_collection("detection_jobs")
        doc = await jobs_col.find_one({"detection_job_id": detection_job_id})
        if not doc:
            return None

        doc.pop("_id", None)
        return DetectionResultData(**doc)

    async def get_project_faces(self, project_id: str) -> Optional[DetectionResultData]:
        """Retrieves latest face detection results and selected track for a project."""
        if not self.db_service.is_connected:
            raise RuntimeError("Database service is offline.")

        jobs_col = self.db_service.get_collection("detection_jobs")
        doc = await jobs_col.find_one({"project_id": project_id}, sort=[("created_at", -1)])
        if not doc:
            return None

        doc.pop("_id", None)

        # Sync with project's currently selected track if updated
        projects_col = self.db_service.get_collection("projects")
        proj = await projects_col.find_one({"project_id": project_id})
        if proj and proj.get("selected_actor_track_id"):
            doc["selected_track_id"] = proj.get("selected_actor_track_id")

        return DetectionResultData(**doc)

    async def select_actor_track(
        self,
        project_id: str,
        selected_track_id: str,
    ) -> TrackSelectionResultData:
        """
        Affirms which detected actor track in the video the user wants to replace.
        Validates that the track ID belongs to the project's detection results.
        """
        if not self.db_service.is_connected:
            raise RuntimeError("Database service is offline.")

        projects_col = self.db_service.get_collection("projects")
        project_doc = await projects_col.find_one({"project_id": project_id})
        if not project_doc:
            raise ValueError(f"Project with ID '{project_id}' not found.")

        # Find detection results for this project
        jobs_col = self.db_service.get_collection("detection_jobs")
        detection_doc = await jobs_col.find_one({"project_id": project_id}, sort=[("created_at", -1)])

        matched_track: Optional[FaceTrackItem] = None
        if detection_doc and "tracks" in detection_doc:
            for t in detection_doc["tracks"]:
                if t.get("track_id") == selected_track_id or t.get("trackId") == selected_track_id:
                    matched_track = FaceTrackItem(**t)
                    break

        if matched_track is None:
            raise ValueError(
                f"Track ID '{selected_track_id}' does not belong to project '{project_id}'."
            )

        now = current_iso_timestamp()
        # Persist selection in both collections
        await projects_col.update_one(
            {"project_id": project_id},
            {
                "$set": {
                    "selected_actor_track_id": selected_track_id,
                    "updated_at": now,
                }
            },
        )

        if detection_doc:
            await jobs_col.update_one(
                {"detection_job_id": detection_doc["detection_job_id"]},
                {"$set": {"selected_track_id": selected_track_id}},
            )

        logger.info("Selected actor track '%s' for project %s", selected_track_id, project_id)
        return TrackSelectionResultData(
            projectId=project_id,
            selectedTrackId=selected_track_id,
            selectedTrack=matched_track,
            message=f"Actor track '{selected_track_id}' selected for replacement.",
        )


def get_detection_service() -> DetectionService:
    """FastAPI dependency provider for DetectionService."""
    settings = get_settings()
    db = get_database_service()
    storage = get_storage_service()
    return DetectionService(settings=settings, db_service=db, storage_service=storage)

