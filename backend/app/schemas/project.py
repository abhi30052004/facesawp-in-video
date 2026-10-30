from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.common import ApiResponse


class ConsentRequest(BaseModel):
    """Payload to record verified likeness authorization consent."""
    project_id: str = Field(alias="projectId", description="Associated Project ID")
    consent_given: bool = Field(alias="consentGiven", description="Must be true to authorize")
    consent_text_version: str = Field(default="v1.0", alias="consentTextVersion")
    affirmation: str = Field(
        default="I affirm that I own the rights or have authorized likeness consent to synthesize this persona.",
        description="Affirmation statement",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ConsentRecordData(BaseModel):
    """Stored consent record details."""
    consent_id: str = Field(alias="consentId")
    project_id: str = Field(alias="projectId")
    consent_given: bool = Field(alias="consentGiven")
    consent_text_version: str = Field(alias="consentTextVersion")
    affirmation: str
    created_at: str = Field(alias="createdAt")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class JobResponseData(BaseModel):
    """Status and progress metrics for a processing job."""
    job_id: str = Field(alias="jobId")
    project_id: str = Field(alias="projectId")
    status: str = Field(description="uploaded, queued, detecting_faces, awaiting_face_selection, processing, completed, failed")
    progress: float = Field(default=0.0)
    current_stage: str = Field(default="Asset Ingestion Complete", alias="currentStage")
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ProjectCreateRequest(BaseModel):
    """Payload to create a new BollySwap project."""
    title: str = Field(default="Cinematic Project", description="Project name")
    original_video_id: str = Field(alias="originalVideoId", description="Upload ID of the source video")
    replacement_face_id: str = Field(alias="replacementFaceId", description="Upload ID or preset ID of the target face")
    user_id: Optional[str] = Field(default=None, alias="userId")
    consent_confirmed: bool = Field(default=True, alias="consentConfirmed")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ProjectResponseData(BaseModel):
    """Detailed metadata for a project."""
    project_id: str = Field(alias="projectId")
    user_id: Optional[str] = Field(default=None, alias="userId")
    title: str
    original_video_id: str = Field(alias="originalVideoId")
    replacement_face_id: str = Field(alias="replacementFaceId")
    status: str
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")
    active_job: Optional[JobResponseData] = Field(default=None, alias="activeJob")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ProjectCreateResponse(ApiResponse[ProjectResponseData]):
    pass


class ProjectListResponse(ApiResponse[List[ProjectResponseData]]):
    pass


class ProjectDetailResponse(ApiResponse[ProjectResponseData]):
    pass


class JobDetailResponse(ApiResponse[JobResponseData]):
    pass


class ConsentResponse(ApiResponse[ConsentRecordData]):
    pass

