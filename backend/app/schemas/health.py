from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.common import ApiResponse


class HealthData(BaseModel):
    """
    Structured health and telemetry metrics for BollySwap AI.
    Compatible with frontend HealthCheckResponse type contracts.
    """
    status: str = Field(
        default="online",
        description="System health status ('online', 'degraded', 'offline')",
    )
    version: str = Field(
        description="Current application version",
    )
    environment: str = Field(
        description="Deployment runtime environment (e.g. 'development', 'production')",
    )
    groq_configured: bool = Field(
        description="Whether a valid Groq API key is present in configuration",
    )
    groq_model: str = Field(
        description="Designated Groq language/intelligence model",
    )
    ai_worker_status: str = Field(
        default="ready",
        description="AI worker engine status (e.g. 'ready', 'processing', 'offline')",
    )
    database_connected: bool = Field(
        default=False,
        alias="databaseConnected",
        description="Whether the MongoDB Atlas database cluster is connected and responsive",
    )
    database_status: str = Field(
        default="disconnected",
        alias="databaseStatus",
        description="Database connectivity status ('connected', 'disconnected', 'unconfigured')",
    )
    database_name: Optional[str] = Field(
        default=None,
        alias="databaseName",
        description="Target database identifier without credentials",
    )
    gpu_workers_available: int = Field(
        default=0,
        alias="gpuWorkersAvailable",
        description="Available GPU instances in production cluster",
    )
    avg_queue_wait_sec: float = Field(
        default=0.0,
        alias="avgQueueWaitSec",
        description="Average queue wait duration in seconds",
    )
    active_model: str = Field(
        default="BollyMesh-v2.4-NeuralBlend",
        alias="activeModel",
        description="Designated face-swapping neural pipeline architecture",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class HealthResponse(ApiResponse[HealthData]):
    """Standardized API response for health checks."""
    pass
