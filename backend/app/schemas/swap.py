from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.common import ApiResponse


class SwapJobCreateRequest(BaseModel):
    """Payload to request video face-swap processing pipeline execution."""
    project_id: str = Field(alias="projectId", description="Associated Project ID")
    source_video_id: str = Field(alias="sourceVideoId", description="Uploaded source video file ID")
    replacement_face_id: str = Field(alias="replacementFaceId", description="Target actor replacement image ID")
    selected_actor_track_id: str = Field(default="actor_1", alias="selectedActorTrackId", description="Candidate actor track to replace")

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "replacementFaceId" not in data and "replacement_face_id" not in data:
                if "targetFaceId" in data:
                    data["replacementFaceId"] = data["targetFaceId"]
                elif "target_face_id" in data:
                    data["replacement_face_id"] = data["target_face_id"]
            if "selectedActorTrackId" not in data and "selected_actor_track_id" not in data:
                if "selectedTrackId" in data:
                    data["selectedActorTrackId"] = data["selectedTrackId"]
                elif "selected_track_id" in data:
                    data["selected_actor_track_id"] = data["selected_track_id"]
                else:
                    data["selectedActorTrackId"] = "actor_1"
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class SwapJobData(BaseModel):
    """Detailed progress and execution status of a face swap processing pipeline job."""
    job_id: str = Field(alias="jobId")
    project_id: str = Field(alias="projectId")
    selected_actor_track_id: Optional[str] = Field(default="actor_1", alias="selectedActorTrackId")
    source_video_id: Optional[str] = Field(default="", alias="sourceVideoId")
    replacement_face_id: Optional[str] = Field(default="", alias="replacementFaceId")
    status: str = Field(
        description="queued, validating, preparing, processing, finalizing, completed, failed, model_not_configured"
    )
    progress: float = Field(default=0.0, description="Real execution progress from 0.0 to 1.0")
    current_step: str = Field(default="Initialized", alias="currentStep")
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    started_at: Optional[str] = Field(default=None, alias="startedAt")
    completed_at: Optional[str] = Field(default=None, alias="completedAt")
    output_video_id: Optional[str] = Field(default=None, alias="outputVideoId")
    output_video_url: Optional[str] = Field(default=None, alias="outputVideoUrl")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class SwapJobResponse(ApiResponse[SwapJobData]):
    """Standardized response envelope for face swap job triggers and status polls."""
    pass


class SwapResultData(BaseModel):
    """Result details and streaming artifacts for a completed video swap pipeline job."""
    job_id: str = Field(alias="jobId")
    project_id: str = Field(alias="projectId")
    status: str
    output_video_id: Optional[str] = Field(default=None, alias="outputVideoId")
    output_video_url: Optional[str] = Field(default=None, alias="outputVideoUrl")
    duration_seconds: Optional[float] = Field(default=None, alias="durationSeconds")
    frames_processed: int = Field(default=0, alias="framesProcessed")
    fps: Optional[float] = None
    resolution: Optional[str] = None
    model_identifier: str = Field(default="unconfigured", alias="modelIdentifier")
    is_swapped: bool = Field(default=False, alias="isSwapped")
    watermarked: bool = Field(default=True)
    message: str

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class SwapResultResponse(ApiResponse[SwapResultData]):
    """Standardized response envelope for retrieving swapped video output artifacts."""
    pass
