from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.common import ApiResponse


class VideoMetadataDetail(BaseModel):
    """Detailed metadata extracted from video container via OpenCV."""
    width: int
    height: int
    fps: float
    duration_seconds: float = Field(alias="durationSeconds")
    frame_count: int = Field(alias="frameCount")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class FaceBoundingBox(BaseModel):
    """Normalized or pixel coordinates for detected face bounding box."""
    x: int
    y: int
    width: int
    height: int

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class FaceTrackItem(BaseModel):
    """Face detection track hypothesis across sampled video frames."""
    track_id: str = Field(alias="trackId", description="Unique track hypothesis ID, e.g. track_1")
    label: str = Field(description="Display label, e.g. Actor #1")
    confidence: float = Field(description="Detection confidence score (0.0 - 1.0)")
    thumbnail_file_id: str = Field(alias="thumbnailFileId", description="Storage file ID of representative face thumbnail")
    thumbnail_url: str = Field(alias="thumbnailUrl", description="API URL for retrieving cropped thumbnail")
    occurrences: int = Field(description="Count of sampled frames this actor appeared in")
    timestamps: List[float] = Field(default_factory=list, description="Timestamps in seconds where this face was detected")
    bounding_box: FaceBoundingBox = Field(alias="boundingBox", description="Representative bounding box")
    landmarks: Optional[List[List[float]]] = Field(default=None, description="5 facial landmark coordinates [x, y]")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class FaceDetectRequest(BaseModel):
    """Request payload to initiate real YuNet face detection on video footage."""
    project_id: str = Field(alias="projectId", description="Associated Project ID")
    video_id: str = Field(alias="videoId", description="Upload ID of the source video")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class DetectionResultData(BaseModel):
    """Results and tracking hypotheses from OpenCV YuNet video analysis."""
    detection_job_id: str = Field(alias="detectionJobId")
    project_id: str = Field(alias="projectId")
    video_id: str = Field(alias="videoId")
    detection_status: str = Field(
        alias="detectionStatus",
        description="queued, extracting_frames, detecting_faces, grouping_tracks, completed, failed"
    )
    progress: float = Field(default=0.0)
    current_stage: str = Field(default="Initialized", alias="currentStage")
    video_metadata: Optional[VideoMetadataDetail] = Field(default=None, alias="videoMetadata")
    sampled_frame_count: int = Field(default=0, alias="sampledFrameCount")
    detected_face_count: int = Field(default=0, alias="detectedFaceCount")
    tracks: List[FaceTrackItem] = Field(default_factory=list)
    selected_track_id: Optional[str] = Field(default=None, alias="selectedTrackId")
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    created_at: str = Field(alias="createdAt")
    completed_at: Optional[str] = Field(default=None, alias="completedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class FaceDetectResponse(ApiResponse[DetectionResultData]):
    """Standardized response envelope for face detection trigger and results."""
    pass


class DetectionJobResponse(ApiResponse[DetectionResultData]):
    """Standardized response envelope for polling face detection job status."""
    pass


class TrackSelectionRequest(BaseModel):
    """Payload to select which detected actor track to replace."""
    selected_track_id: str = Field(alias="selectedTrackId", description="Track ID to replace, e.g. track_1")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class TrackSelectionResultData(BaseModel):
    """Details of the affirmed actor selection for a project."""
    project_id: str = Field(alias="projectId")
    selected_track_id: str = Field(alias="selectedTrackId")
    selected_track: Optional[FaceTrackItem] = Field(default=None, alias="selectedTrack")
    message: str

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class TrackSelectionResponse(ApiResponse[TrackSelectionResultData]):
    """Standardized response envelope for actor selection affirmation."""
    pass


class ProjectFacesResponse(ApiResponse[DetectionResultData]):
    """Standardized response envelope for retrieving detected faces of a project."""
    pass

