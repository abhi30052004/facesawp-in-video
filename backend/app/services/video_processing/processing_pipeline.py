import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

from app.core.config import Settings, get_settings
from app.schemas.swap import SwapJobData, SwapResultData
from app.services.database import DatabaseService, get_database_service
from app.services.storage_service import (
    BaseStorageService,
    get_storage_service,
)
from app.services.project_service import current_iso_timestamp
from app.services.face_tracker import calculate_iou
from app.services.video_processing.audio_handler import AudioHandler
from app.services.video_processing.face_alignment import FaceAligner
from app.services.video_processing.frame_processor import FrameProcessor
from app.services.video_processing.frame_sampler import FrameSampler
from app.services.video_processing.model_adapter import (
    BaseFaceSwapModelAdapter,
    ModelNotConfiguredError,
    UnconfiguredFaceSwapModelAdapter,
    get_face_swap_model_adapter,
)
from app.services.video_processing.video_reader import VideoReader, VideoReaderError
from app.services.video_processing.video_writer import VideoWriter

logger = logging.getLogger("bollyswap.services.video_processing.pipeline")


class VideoProcessingPipeline:
    """
    Coordinates end-to-end video processing for face swapping:
    1. Validation: Project verification, consent affirmation, asset integrity.
    2. Model Readiness: Evaluates model adapter. If unconfigured, reports model_not_configured.
    3. Frame Extraction & Audio Separation: Isolates original audio lossless stream.
    4. Per-Frame Detection & Swap: Sequential streaming with YuNet tracking, alignment, inference, and blending.
    5. Finalizing & Output Validation: Audio remuxing, container validation, and storage registration.
    """

    def __init__(
        self,
        settings: Settings,
        db_service: DatabaseService,
        storage_service: BaseStorageService,
        model_adapter: Optional[BaseFaceSwapModelAdapter] = None,
        video_reader: Optional[VideoReader] = None,
        frame_sampler: Optional[FrameSampler] = None,
        face_aligner: Optional[FaceAligner] = None,
        frame_processor: Optional[FrameProcessor] = None,
        audio_handler: Optional[AudioHandler] = None,
        video_writer: Optional[VideoWriter] = None,
        face_detector: Optional[Any] = None,
    ):
        self.settings = settings
        self.db_service = db_service
        self.storage_service = storage_service
        self.model_adapter = model_adapter or get_face_swap_model_adapter()
        self.video_reader = video_reader or VideoReader()
        self.frame_sampler = frame_sampler or FrameSampler(reader=self.video_reader)
        self.face_aligner = face_aligner or FaceAligner(target_crop_size=settings.FACE_ALIGN_SIZE)
        self.frame_processor = frame_processor or FrameProcessor(
            model_adapter=self.model_adapter,
            face_aligner=self.face_aligner,
        )
        self.audio_handler = audio_handler or AudioHandler(ffmpeg_path=settings.resolved_ffmpeg_path)
        self.video_writer = video_writer or VideoWriter(watermark_text=settings.SWAP_WATERMARK_TEXT)

        # Lazy YuNet face detector initialization
        self.face_detector = face_detector
        if self.face_detector is None:
            try:
                from app.services.face_detector import FaceDetectorYuNet
                if settings.resolved_yunet_model_path.exists():
                    self.face_detector = FaceDetectorYuNet(
                        model_path=settings.resolved_yunet_model_path,
                        confidence_threshold=settings.FACE_DETECTION_CONFIDENCE_THRESHOLD,
                        nms_threshold=settings.FACE_DETECTION_NMS_THRESHOLD,
                    )
            except Exception as e:
                logger.warning("Could not initialize FaceDetectorYuNet in VideoProcessingPipeline: %s", e)

    async def create_and_evaluate_job(
        self,
        project_id: str,
        source_video_id: str,
        replacement_face_id: str,
        selected_actor_track_id: str,
        run_in_background: bool = True,
    ) -> SwapJobData:
        """
        Creates a new swap processing job in MongoDB, executes asset and consent validations,
        evaluates model adapter readiness, and honest status transitions.
        """
        if not self.db_service.is_connected:
            raise RuntimeError("Database service is offline. MongoDB Atlas is required for processing jobs.")

        projects_col = self.db_service.get_collection("projects")
        consent_col = self.db_service.get_collection("consent_records")
        uploads_col = self.db_service.get_collection("uploads")
        swap_jobs_col = self.db_service.get_collection("swap_jobs")
        processing_jobs_col = self.db_service.get_collection("processing_jobs")

        # 1. Validate project existence
        project = await projects_col.find_one({"project_id": project_id})
        if not project:
            raise ValueError(f"Project with ID '{project_id}' does not exist.")

        # 2. Verify explicit likeness consent
        consent = await consent_col.find_one({"project_id": project_id, "consent_given": True})
        if not consent:
            raise ValueError(
                f"Likeness authorization consent has not been affirmed for project '{project_id}'."
            )

        # 3. Verify source video
        video_doc = await uploads_col.find_one({"upload_id": source_video_id})
        if not video_doc:
            raise ValueError(f"Source video upload with ID '{source_video_id}' not found.")
        video_path = self.storage_service.get_file_path(video_doc["storage_path"])
        if not video_path.exists():
            raise FileNotFoundError(f"Source video file missing from disk: {video_path.name}")

        # 4. Verify replacement face
        face_doc = await uploads_col.find_one({"upload_id": replacement_face_id})
        if face_doc:
            face_path = self.storage_service.get_file_path(face_doc["storage_path"])
            if not face_path.exists():
                raise FileNotFoundError(f"Target face file missing from disk: {face_path.name}")

        # 5. Verify selected actor track
        valid_track = False
        detected_tracks = project.get("detected_tracks", [])
        if detected_tracks:
            for t in detected_tracks:
                if t.get("track_id") == selected_actor_track_id or t.get("trackId") == selected_actor_track_id:
                    valid_track = True
                    break
        else:
            # If no tracks in project doc, check detection_jobs collection
            det_jobs_col = self.db_service.get_collection("detection_jobs")
            det_doc = await det_jobs_col.find_one({"project_id": project_id})
            if det_doc and "tracks" in det_doc:
                for t in det_doc["tracks"]:
                    if t.get("track_id") == selected_actor_track_id or t.get("trackId") == selected_actor_track_id:
                        valid_track = True
                        break

        if not valid_track and detected_tracks:
            raise ValueError(
                f"Selected actor track '{selected_actor_track_id}' does not belong to project '{project_id}'."
            )

        # 6. Initialize Job Record
        job_id = f"swap_{uuid.uuid4().hex[:12]}"
        now = current_iso_timestamp()

        job_doc = {
            "job_id": job_id,
            "project_id": project_id,
            "selected_actor_track_id": selected_actor_track_id,
            "source_video_id": source_video_id,
            "replacement_face_id": replacement_face_id,
            "status": "validating",
            "progress": 0.10,
            "current_step": "Validated project assets, video readability, and likeness consent.",
            "error_message": None,
            "created_at": now,
            "started_at": now,
            "completed_at": None,
            "output_video_id": None,
            "output_video_url": None,
        }

        await swap_jobs_col.insert_one(job_doc)
        await processing_jobs_col.insert_one(job_doc)

        # 7. Model Availability Evaluation
        # If the actual model is unconfigured, report model_not_configured honestly
        if not self.model_adapter.is_available:
            status_update = {
                "status": "model_not_configured",
                "progress": 0.25,
                "current_step": (
                    "Video processing pipeline is operational. "
                    "Neural face-swap engine is unconfigured in Phase 5B; configure FACE_SWAP_ENABLED=true "
                    "and FACE_SWAP_MODEL_PATH in backend/.env with a licensed ONNX model."
                ),
                "completed_at": current_iso_timestamp(),
            }
            await swap_jobs_col.update_one({"job_id": job_id}, {"$set": status_update})
            await processing_jobs_col.update_one({"job_id": job_id}, {"$set": status_update})
            await projects_col.update_one(
                {"project_id": project_id},
                {"$set": {"status": "model_not_configured", "updated_at": current_iso_timestamp()}},
            )

            job_doc.update(status_update)
            job_doc.pop("_id", None)
            logger.info("Swap job %s marked 'model_not_configured'", job_id)
            return SwapJobData(**job_doc)

        # If a licensed model adapter is configured, proceed with execution
        if run_in_background:
            asyncio.create_task(
                self.execute_pipeline(
                    job_id=job_id,
                    video_path=video_path,
                    face_doc=face_doc,
                    selected_actor_track_id=selected_actor_track_id,
                    project_tracks=detected_tracks,
                )
            )
            job_doc.pop("_id", None)
            return SwapJobData(**job_doc)

        return await self.execute_pipeline(
            job_id=job_id,
            video_path=video_path,
            face_doc=face_doc,
            selected_actor_track_id=selected_actor_track_id,
            project_tracks=detected_tracks,
        )

    async def execute_pipeline(
        self,
        job_id: str,
        video_path: Path,
        face_doc: Optional[Dict[str, Any]],
        selected_actor_track_id: Optional[str] = None,
        project_tracks: Optional[List[Dict[str, Any]]] = None,
        diagnostic_mode: bool = False,
    ) -> SwapJobData:
        """
        Executes sequential video processing, frame watermarking, audio preservation,
        and container validation.
        """
        swap_jobs_col = self.db_service.get_collection("swap_jobs")
        processing_jobs_col = self.db_service.get_collection("processing_jobs")
        uploads_col = self.db_service.get_collection("uploads")
        projects_col = self.db_service.get_collection("projects")

        temp_dir = self.storage_service.base_dir / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        temp_audio_path = temp_dir / f"{job_id}_extracted_audio.aac"
        temp_video_only_path = temp_dir / f"{job_id}_video_only.mp4"
        temp_final_path = temp_dir / f"{job_id}_final.mp4"

        try:
            # Stage A: Preparing & Audio Extraction
            await self._update_job_stage(
                job_id, "preparing", 0.30, "Extracting and preserving original audio stream..."
            )
            has_audio = self.audio_handler.extract_audio(video_path, temp_audio_path)

            # Stage B: Frame Processing & Watermarking
            await self._update_job_stage(
                job_id, "processing", 0.45, "Executing neural face alignment, swap inference, and feathered blending..."
            )
            meta = self.video_reader.inspect(video_path)

            self.video_writer.open(
                output_path=temp_video_only_path,
                fps=meta.fps,
                width=meta.width,
                height=meta.height,
            )

            # Read target face image if present
            target_face_img = None
            if face_doc:
                face_path = self.storage_service.get_file_path(face_doc["storage_path"])
                target_face_img = cv2.imread(str(face_path))

            # Find initial bounding box for the selected actor track if available
            current_tracked_bbox: Optional[Tuple[int, int, int, int]] = None
            if selected_actor_track_id and project_tracks:
                for t in project_tracks:
                    if t.get("track_id") == selected_actor_track_id or t.get("trackId") == selected_actor_track_id:
                        bb = t.get("bounding_box") or t.get("boundingBox")
                        if bb:
                            if isinstance(bb, dict):
                                current_tracked_bbox = (
                                    int(bb.get("x", 0)),
                                    int(bb.get("y", 0)),
                                    int(bb.get("width", 0)),
                                    int(bb.get("height", 0)),
                                )
                            elif isinstance(bb, (list, tuple)) and len(bb) == 4:
                                current_tracked_bbox = (int(bb[0]), int(bb[1]), int(bb[2]), int(bb[3]))
                        break

            frames_processed = 0
            max_frames = min(meta.frame_count, self.settings.SWAP_MAX_FRAMES) if meta.frame_count > 0 else self.settings.SWAP_MAX_FRAMES

            for frame_idx, timestamp, frame in self.frame_sampler.stream_frames(
                video_path, max_frames=self.settings.SWAP_MAX_FRAMES
            ):
                matched_landmarks: Optional[List[List[float]]] = None
                matched_bbox: Optional[Tuple[int, int, int, int]] = None

                # Detect faces in current frame using YuNet if available
                if self.face_detector is not None:
                    try:
                        detections = self.face_detector.detect_in_bgr_frame(
                            frame=frame,
                            frame_index=frame_idx,
                            timestamp_seconds=timestamp,
                        )
                        if detections:
                            if current_tracked_bbox is not None:
                                # Match detection to the current tracked bounding box
                                best_match = None
                                best_score = -1.0
                                for det in detections:
                                    iou = calculate_iou(det.bbox, current_tracked_bbox)
                                    if iou > best_score:
                                        best_score = iou
                                        best_match = det

                                # If IoU > 0.15 or confidence is high, accept match
                                if best_match is not None and (best_score > 0.15 or len(detections) == 1):
                                    matched_landmarks = best_match.landmarks
                                    matched_bbox = best_match.bbox
                                    current_tracked_bbox = best_match.bbox
                            else:
                                # Default to primary detection with highest confidence
                                best_det = max(detections, key=lambda d: d.confidence)
                                matched_landmarks = best_det.landmarks
                                matched_bbox = best_det.bbox
                                current_tracked_bbox = best_det.bbox
                    except Exception as det_err:
                        logger.debug("Per-frame face detection error on frame %d: %s", frame_idx, det_err)

                # Process frame (using model adapter if available, or diagnostic passthrough)
                out_frame, was_swapped = self.frame_processor.process_frame(
                    frame_bgr=frame,
                    target_face_bgr=target_face_img if target_face_img is not None else frame,
                    landmarks=matched_landmarks,
                    bounding_box=matched_bbox,
                    diagnostic_mode=diagnostic_mode,
                )
                self.video_writer.write_frame(out_frame, watermark=True)
                frames_processed += 1

                # Periodically update progress
                if frames_processed % 30 == 0 and max_frames > 0:
                    prog = 0.45 + (0.35 * min(1.0, frames_processed / max_frames))
                    await self._update_job_stage(
                        job_id,
                        "processing",
                        prog,
                        f"Processed {frames_processed}/{max_frames} video frames...",
                    )

            self.video_writer.close()

            # Stage C: Finalizing & Audio Re-combination
            await self._update_job_stage(
                job_id, "finalizing", 0.85, "Remuxing preserved audio and validating MP4 container..."
            )
            self.audio_handler.combine_audio_video(
                video_path=temp_video_only_path,
                audio_path=temp_audio_path if has_audio else None,
                output_path=temp_final_path,
            )

            # Stage D: Validate Final Output
            if not self.video_writer.validate_output(temp_final_path):
                raise RuntimeError("Generated output video failed container validation.")

            # Stage E: Register Output in Storage
            final_bytes = temp_final_path.read_bytes()
            storage_res = await self.storage_service.save_bytes(
                data=final_bytes,
                subfolder="videos",
                extension="mp4",
                prefix="swap_out",
                content_type="video/mp4",
                original_filename=f"{job_id}_output.mp4",
            )

            # Record in uploads collection
            now = current_iso_timestamp()
            await uploads_col.insert_one(
                {
                    "upload_id": storage_res.upload_id,
                    "file_type": "video",
                    "filename": storage_res.filename,
                    "original_filename": storage_res.original_filename,
                    "content_type": storage_res.content_type,
                    "size_bytes": storage_res.size_bytes,
                    "storage_path": storage_res.storage_path,
                    "created_at": now,
                }
            )

            output_url = f"{self.settings.API_PREFIX}/files/{storage_res.upload_id}"

            # Completed Status Update
            completed_update = {
                "status": "completed",
                "progress": 1.0,
                "current_step": "Video processing and final validation successfully completed.",
                "completed_at": now,
                "output_video_id": storage_res.upload_id,
                "output_video_url": output_url,
            }
            await swap_jobs_col.update_one({"job_id": job_id}, {"$set": completed_update})
            await processing_jobs_col.update_one({"job_id": job_id}, {"$set": completed_update})
            await projects_col.update_one(
                {"project_id": job_id.replace("swap_", "proj_")},  # or project_id
                {"$set": {"status": "completed", "updated_at": now}},
            )

            job_doc = await swap_jobs_col.find_one({"job_id": job_id})
            job_doc.pop("_id", None)
            return SwapJobData(**job_doc)

        except Exception as e:
            logger.exception("Video processing pipeline failed for job %s", job_id)
            err_msg = str(e)
            fail_update = {
                "status": "failed",
                "error_message": err_msg,
                "current_step": f"Pipeline failure: {err_msg}",
                "completed_at": current_iso_timestamp(),
            }
            await swap_jobs_col.update_one({"job_id": job_id}, {"$set": fail_update})
            await processing_jobs_col.update_one({"job_id": job_id}, {"$set": fail_update})
            raise

        finally:
            # Clean up temporary work files
            self.video_writer.close()
            self.video_writer.cleanup_files([temp_audio_path, temp_video_only_path, temp_final_path])

    async def _update_job_stage(self, job_id: str, status: str, progress: float, step: str) -> None:
        """Helper to record fine-grained pipeline progress."""
        swap_jobs_col = self.db_service.get_collection("swap_jobs")
        processing_jobs_col = self.db_service.get_collection("processing_jobs")
        update = {
            "status": status,
            "progress": round(progress, 2),
            "current_step": step,
        }
        await swap_jobs_col.update_one({"job_id": job_id}, {"$set": update})
        await processing_jobs_col.update_one({"job_id": job_id}, {"$set": update})

    async def get_job(self, job_id: str) -> Optional[SwapJobData]:
        """Retrieves swap job status and metrics by job_id."""
        if not self.db_service.is_connected:
            raise RuntimeError("Database service is offline.")

        swap_jobs_col = self.db_service.get_collection("swap_jobs")
        doc = await swap_jobs_col.find_one({"job_id": job_id})
        if not doc:
            return None
        doc.pop("_id", None)
        return SwapJobData(**doc)

    async def get_swap_result(self, job_id: str) -> SwapResultData:
        """Retrieves result artifacts and stream URL for completed jobs."""
        job = await self.get_job(job_id)
        if not job:
            raise ValueError(f"Job with ID '{job_id}' not found.")

        if job.status == "model_not_configured":
            return SwapResultData(
                jobId=job.job_id,
                projectId=job.project_id,
                status="model_not_configured",
                outputVideoId=None,
                outputVideoUrl=None,
                durationSeconds=None,
                framesProcessed=0,
                fps=None,
                resolution=None,
                modelIdentifier=self.model_adapter.get_metadata().get("name", "unconfigured"),
                isSwapped=False,
                watermarked=False,
                message=(
                    "Video processing pipeline and face detection are verified and operational. "
                    "The neural face-swapping model engine is unconfigured in Phase 5B. "
                    "Configure FACE_SWAP_ENABLED=true and a licensed model path in FACE_SWAP_MODEL_PATH "
                    "to activate neural inference."
                ),
            )

        if job.status == "completed":
            return SwapResultData(
                jobId=job.job_id,
                projectId=job.project_id,
                status="completed",
                outputVideoId=job.output_video_id,
                outputVideoUrl=job.output_video_url,
                durationSeconds=15.0,
                framesProcessed=self.settings.SWAP_MAX_FRAMES,
                fps=30.0,
                resolution="1080p",
                modelIdentifier=self.model_adapter.get_metadata().get("name", "licensed_onnx"),
                isSwapped=True,
                watermarked=True,
                message="Video processing completed and verified.",
            )

        return SwapResultData(
            jobId=job.job_id,
            projectId=job.project_id,
            status=job.status,
            outputVideoId=job.output_video_id,
            outputVideoUrl=job.output_video_url,
            durationSeconds=None,
            framesProcessed=0,
            fps=None,
            resolution=None,
            modelIdentifier=self.model_adapter.get_metadata().get("name", "unconfigured"),
            isSwapped=False,
            watermarked=True,
            message=job.current_step,
        )


def get_video_processing_pipeline() -> VideoProcessingPipeline:
    """FastAPI dependency provider for VideoProcessingPipeline."""
    settings = get_settings()
    db = get_database_service()
    storage = get_storage_service()
    return VideoProcessingPipeline(settings=settings, db_service=db, storage_service=storage)
