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
    FRONTEND_URL: str = "https://facesawp-in-video.vercel.app"
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://facesawp-in-video.vercel.app",
        "https://bollyswap.vercel.app",
    ]

    # Groq AI Service Configuration
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "qwen/qwen3.8-27b"
    GROQ_TIMEOUT_SECONDS: float = 10.0

    # MongoDB Atlas Database Configuration
    MONGODB_URI: Optional[str] = None
    DATABASE_NAME: str = "bollyswap"

    # Storage Configuration (Local Filesystem with Cloudflare R2 / S3 Abstraction)
    STORAGE_BACKEND: str = "local"
    STORAGE_DIR: str = "storage"
    MAX_VIDEO_SIZE_BYTES: int = 100 * 1024 * 1024   # 100 MB
    MAX_IMAGE_SIZE_BYTES: int = 10 * 1024 * 1024    # 10 MB

    # Cloudflare R2 / S3 Storage Credentials
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET_NAME: Optional[str] = None
    R2_PUBLIC_URL: Optional[str] = None
    S3_ENDPOINT_URL: Optional[str] = None
    S3_REGION_NAME: str = "auto"

    # AI Face Detection Configuration (OpenCV YuNet - CPU Only)
    YUNET_MODEL_PATH: str = "models/face_detection_yunet_2023mar.onnx"
    FACE_DETECTION_CONFIDENCE_THRESHOLD: float = 0.6
    FACE_DETECTION_NMS_THRESHOLD: float = 0.3
    VIDEO_SAMPLE_INTERVAL_SECONDS: float = 1.5
    VIDEO_MAX_SAMPLED_FRAMES: int = 30
    VIDEO_MAX_FRAME_DIMENSION: int = 1280

    # Video Processing Pipeline & Face Swapping (Phase 5A & 5B)
    SWAP_MAX_FRAMES: int = 300
    SWAP_PROCESSING_TIMEOUT_SECONDS: float = 120.0
    SWAP_WATERMARK_TEXT: str = "BollySwap AI • Synthetic Media"
    FACE_ALIGN_SIZE: int = 256
    FACE_SWAP_MODEL_NAME: str = "unconfigured"
    FFMPEG_PATH: Optional[str] = None
    FFPROBE_PATH: Optional[str] = None
    FACEFUSION_DIR: Optional[str] = None
    FACEFUSION_MODEL_DIR: Optional[str] = None
    PUBLIC_BACKEND_URL: Optional[str] = None
    API_ACCESS_KEY: Optional[str] = None
    MAX_ACTIVE_SWAP_JOBS: int = 2

    # AI Face Swap Engine Configuration (Phase 5B & Phase 6 - ONNX Runtime CPU)
    FACE_SWAP_ENABLED: bool = True
    FACE_SWAP_MODEL_PATH: Optional[str] = "models/inswapper_128.onnx"
    FACE_SWAP_ARCFACE_PATH: Optional[str] = "models/w600k_r50.onnx"
    FACE_SWAP_MODEL_LICENSE: str = "InsightFace-NonCommercial-Research"
    FACE_SWAP_PROVIDER: str = "CPUExecutionProvider"
    FACE_SWAP_INPUT_SIZE: int = 128

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", str(Path(__file__).resolve().parent.parent.parent / ".env")),
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

    @property
    def resolved_face_swap_model_path(self) -> Optional[Path]:
        """Resolves absolute path for the configured face-swap ONNX model, if any."""
        if not self.FACE_SWAP_MODEL_PATH:
            return None
        path = Path(self.FACE_SWAP_MODEL_PATH)
        if not path.is_absolute():
            base_dir = Path(__file__).resolve().parent.parent.parent
            path = base_dir / self.FACE_SWAP_MODEL_PATH
        return path

    @property
    def resolved_arcface_model_path(self) -> Optional[Path]:
        """Resolves absolute path for the ArcFace 512-D identity extractor ONNX model."""
        if not self.FACE_SWAP_ARCFACE_PATH:
            return None
        path = Path(self.FACE_SWAP_ARCFACE_PATH)
        if not path.is_absolute():
            base_dir = Path(__file__).resolve().parent.parent.parent
            path = base_dir / self.FACE_SWAP_ARCFACE_PATH
        return path

    @property
    def resolved_ffmpeg_path(self) -> str:
        """Finds FFmpeg binary via configuration, PATH, WinGet, or imageio_ffmpeg."""
        import shutil
        import os
        import glob
        if self.FFMPEG_PATH and Path(self.FFMPEG_PATH).exists():
            return self.FFMPEG_PATH
        found = shutil.which("ffmpeg")
        if found:
            return found
        # Check standard WinGet installation dynamically using LOCALAPPDATA
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            pattern = os.path.join(local_app_data, "Microsoft", "WinGet", "Packages", "*Gyan.FFmpeg*", "**", "ffmpeg.exe")
            matches = glob.glob(pattern, recursive=True)
            if matches and Path(matches[0]).exists():
                return matches[0]
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass
        return "ffmpeg"

    @property
    def resolved_ffprobe_path(self) -> str:
        """Finds FFprobe binary via configuration, PATH, or WinGet."""
        import shutil
        import os
        import glob
        if self.FFPROBE_PATH and Path(self.FFPROBE_PATH).exists():
            return self.FFPROBE_PATH
        found = shutil.which("ffprobe")
        if found:
            return found
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            pattern = os.path.join(local_app_data, "Microsoft", "WinGet", "Packages", "*Gyan.FFmpeg*", "**", "ffprobe.exe")
            matches = glob.glob(pattern, recursive=True)
            if matches and Path(matches[0]).exists():
                return matches[0]
        return "ffprobe"

    @property
    def resolved_facefusion_dir(self) -> Path:
        """Resolves absolute directory of FaceFusion engine."""
        if self.FACEFUSION_DIR:
            p = Path(self.FACEFUSION_DIR)
            if p.exists():
                return p.resolve()
        # Fallback to sibling facefusion folder in repo root
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        return repo_root / "facefusion"

    @property
    def resolved_model_dir(self) -> Path:
        """Resolves directory where FaceFusion models are cached."""
        if self.FACEFUSION_MODEL_DIR:
            p = Path(self.FACEFUSION_MODEL_DIR)
            if p.exists():
                return p.resolve()
        return self.resolved_facefusion_dir / ".assets" / "models"


@lru_cache()
def get_settings() -> Settings:
    """Cached accessor for application settings."""
    return Settings()
