from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.common import ApiResponse


class GroqTestRequest(BaseModel):
    """Payload for triggering a live minimal Groq connection test."""
    prompt: Optional[str] = Field(
        default="Ping from BollySwap AI backend.",
        description="Test prompt to verify Groq API inference and connectivity",
        max_length=200,
    )


class GroqTestResult(BaseModel):
    """Outcome metrics of the Groq test verification call."""
    model: str = Field(description="Groq model utilized for test")
    response_text: str = Field(description="Response returned by the model")
    latency_ms: float = Field(description="Round-trip API call latency in milliseconds")
    tokens_used: Optional[int] = Field(default=None, description="Total tokens consumed in test")
    finish_reason: Optional[str] = Field(default=None, description="Completion finish reason")


class GroqTestResponse(ApiResponse[GroqTestResult]):
    """Standardized API response for Groq connectivity test."""
    pass

