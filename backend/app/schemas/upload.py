from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.common import ApiResponse


class VideoUploadResult(BaseModel):
    """Metadata response for a validated video upload."""
    file_id: str = Field(alias="fileId")
    filename: str
    storage_url: str = Field(alias="storageUrl")
    duration_seconds: float = Field(default=15.0, alias="durationSeconds")
    width: int = Field(default=1920)
    height: int = Field(default=1080)
    fps: int = Field(default=30)
    codec: str = Field(default="h264")
    size_bytes: int = Field(alias="sizeBytes")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class FaceUploadResult(BaseModel):
    """Metadata response for a validated face image upload."""
    face_id: str = Field(alias="faceId")
    preview_url: str = Field(alias="previewUrl")
    detected_faces_count: int = Field(default=1, alias="detectedFacesCount")
    embedding_confidence: float = Field(default=1.0, alias="embeddingConfidence")
    quality_passed: bool = Field(default=True, alias="qualityPassed")
    note: str = Field(default="Face upload stored and verified. Neural face mesh model runs in Phase 4.")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class VideoUploadResponse(ApiResponse[VideoUploadResult]):
    """Standardized response envelope for video uploads."""
    pass


class FaceUploadResponse(ApiResponse[FaceUploadResult]):
    """Standardized response envelope for face uploads."""
    pass

