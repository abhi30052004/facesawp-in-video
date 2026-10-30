from datetime import datetime, timezone
from typing import Any, Dict, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


def current_iso_timestamp() -> str:
    """Returns current UTC ISO-8601 formatted timestamp string."""
    return datetime.now(timezone.utc).isoformat()


class ApiResponse(BaseModel, Generic[T]):
    """
    Standard envelope response matching frontend ApiResponse<T> contract.
    """
    success: bool = True
    data: T
    message: Optional[str] = None
    timestamp: str = Field(default_factory=current_iso_timestamp)


class ApiErrorDetail(BaseModel):
    """Structured error payload details."""
    error_code: str
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ApiErrorResponse(BaseModel):
    """Standard error response format."""
    success: bool = False
    error: ApiErrorDetail
    timestamp: str = Field(default_factory=current_iso_timestamp)

