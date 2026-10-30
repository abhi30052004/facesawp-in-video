from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Union
import json
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings for BollySwap AI Backend.
    Loads configurations from environment variables and .env file.
    """
    APP_NAME: str = "BollySwap AI"
    APP_VERSION: str = "0.3.0"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Server & API
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_PREFIX: str = "/api/v1"

    # Frontend & CORS
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Groq AI Service Configuration
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "qwen/qwen3.8-27b"
    GROQ_TIMEOUT_SECONDS: float = 10.0

    # MongoDB Atlas Database Configuration
    MONGODB_URI: Optional[str] = None
    DATABASE_NAME: str = "bollyswap"

    # Storage Configuration (Local Filesystem with Cloudflare R2 Abstraction)
    STORAGE_DIR: str = "storage"
    MAX_VIDEO_SIZE_BYTES: int = 100 * 1024 * 1024   # 100 MB
    MAX_IMAGE_SIZE_BYTES: int = 10 * 1024 * 1024    # 10 MB

    # AI Face Detection Configuration (OpenCV YuNet - CPU Only)
    YUNET_MODEL_PATH: str = "models/face_detection_yunet_2023mar.onnx"
    FACE_DETECTION_CONFIDENCE_THRESHOLD: float = 0.6
    FACE_DETECTION_NMS_THRESHOLD: float = 0.3
    VIDEO_SAMPLE_INTERVAL_SECONDS: float = 1.5
    VIDEO_MAX_SAMPLED_FRAMES: int = 30
    VIDEO_MAX_FRAME_DIMENSION: int = 1280

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[List[str], str]) -> List[str]:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                try:
                    return json.loads(value)
                except Exception:
                    pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("GROQ_MODEL", mode="before")
    @classmethod
    def validate_groq_model(cls, value: Optional[str]) -> str:
        if not value or value.strip() == "" or "YOUR_AVAILABLE" in value:
            return "qwen/qwen3.8-27b"
        return value.strip()

    @property
    def is_groq_configured(self) -> bool:
        """Returns True only if a real non-placeholder Groq API key is present."""
        if not self.GROQ_API_KEY:
            return False
        cleaned = self.GROQ_API_KEY.strip()
        if cleaned == "" or cleaned.startswith("YOUR_"):
            return False
        return True

    @property
    def masked_groq_api_key(self) -> str:
        """Safely formats the Groq API key without exposing secrets."""
        if not self.is_groq_configured or not self.GROQ_API_KEY:
            return "Not Configured"
        key = self.GROQ_API_KEY.strip()
        if len(key) <= 8:
            return "***"
        return f"{key[:4]}...{key[-4:]}"

    @property
    def is_mongodb_configured(self) -> bool:
        """Returns True if MONGODB_URI is provided and non-placeholder."""
        if not self.MONGODB_URI:
            return False
        cleaned = self.MONGODB_URI.strip()
        return cleaned != "" and not cleaned.startswith("YOUR_")

    @property
    def resolved_storage_dir(self) -> Path:
        """Resolves absolute path for local storage directory."""
        path = Path(self.STORAGE_DIR)
        if not path.is_absolute():
            # Resolve relative to the backend directory
            base_dir = Path(__file__).resolve().parent.parent.parent
            path = base_dir / self.STORAGE_DIR
        return path

    @property
    def resolved_yunet_model_path(self) -> Path:
        """Resolves absolute path for the OpenCV YuNet ONNX model."""
        path = Path(self.YUNET_MODEL_PATH)
        if not path.is_absolute():
            base_dir = Path(__file__).resolve().parent.parent.parent
            path = base_dir / self.YUNET_MODEL_PATH
        return path


@lru_cache()
def get_settings() -> Settings:
    """Cached accessor for application settings."""
    return Settings()
