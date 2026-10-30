import logging
import time
from typing import Optional
from fastapi import Depends
import httpx
from groq import (
    AsyncGroq,
    AuthenticationError,
    APIConnectionError,
    RateLimitError,
    APIStatusError,
    APITimeoutError,
)

from app.core.config import Settings, get_settings
from app.schemas.groq import GroqTestResult

logger = logging.getLogger("bollyswap.services.groq")


class GroqConfigurationError(Exception):
    """Raised when Groq API credentials are missing or invalid."""
    def __init__(self, message: str = "Groq API key is not configured. Please set GROQ_API_KEY in backend/.env"):
        super().__init__(message)
        self.message = message


class GroqServiceError(Exception):
    """Raised when Groq service invocation fails without leaking secrets."""
    def __init__(self, status_code: int, error_code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message


class GroqService:
    """
    Service wrapper for interacting with Groq language models.
    Provides robust timeout handling, sanitized exception masking, and dependency injection.
    """

    def __init__(self, settings: Settings, client: Optional[AsyncGroq] = None):
        self.settings = settings
        self._client = client

    def _get_client(self) -> AsyncGroq:
        """Instantiates or returns the configured AsyncGroq client."""
        if self._client is not None:
            return self._client

        if not self.settings.is_groq_configured or not self.settings.GROQ_API_KEY:
            raise GroqConfigurationError(
                "Groq API key is not configured. Please provide a valid GROQ_API_KEY in the environment or backend/.env file."
            )

        return AsyncGroq(
            api_key=self.settings.GROQ_API_KEY,
            timeout=httpx.Timeout(self.settings.GROQ_TIMEOUT_SECONDS, connect=5.0),
        )

    async def test_connection(self, prompt: str = "Ping from BollySwap AI backend.") -> GroqTestResult:
        """
        Executes a minimal live completion request to verify Groq API connectivity and inference.
        Never exposes the API key or raw sensitive headers.
        """
        client = self._get_client()
        model = self.settings.GROQ_MODEL

        start_time = time.perf_counter()

        try:
            logger.info("Executing Groq connectivity test with model '%s'", model)
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                max_tokens=25,
                temperature=0.2,
            )

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            choice = response.choices[0] if response.choices else None
            response_text = choice.message.content.strip() if (choice and choice.message.content) else "OK"
            finish_reason = choice.finish_reason if choice else "stop"
            tokens_used = response.usage.total_tokens if response.usage else None

            logger.info("Groq connectivity test succeeded in %sms (tokens: %s)", latency_ms, tokens_used)

            return GroqTestResult(
                model=model,
                response_text=response_text,
                latency_ms=latency_ms,
                tokens_used=tokens_used,
                finish_reason=finish_reason,
            )

        except AuthenticationError:
            logger.warning("Groq authentication failure for model %s", model)
            raise GroqServiceError(
                status_code=401,
                error_code="GROQ_AUTH_ERROR",
                message="Groq authentication failed. Please verify that your GROQ_API_KEY is valid and has not expired.",
            )

        except APITimeoutError:
            logger.warning("Groq request timed out after %ss", self.settings.GROQ_TIMEOUT_SECONDS)
            raise GroqServiceError(
                status_code=504,
                error_code="GROQ_TIMEOUT",
                message=f"Request to Groq API timed out after {self.settings.GROQ_TIMEOUT_SECONDS} seconds.",
            )

        except APIConnectionError:
            logger.warning("Failed to connect to Groq API host")
            raise GroqServiceError(
                status_code=502,
                error_code="GROQ_CONNECTION_ERROR",
                message="Could not connect to the Groq API server. Please check network connectivity.",
            )

        except RateLimitError:
            logger.warning("Groq rate limit exceeded for model %s", model)
            raise GroqServiceError(
                status_code=429,
                error_code="GROQ_RATE_LIMITED",
                message="Groq API rate limit reached. Please wait briefly before retrying.",
            )

        except APIStatusError as e:
            status = e.status_code if hasattr(e, "status_code") else 500
            logger.error("Groq API returned error status HTTP %s", status)
            raise GroqServiceError(
                status_code=status,
                error_code="GROQ_API_ERROR",
                message=f"Groq API returned HTTP {status}. Service temporarily unavailable.",
            )

        except httpx.TimeoutException:
            logger.warning("HTTPX timeout connecting to Groq")
            raise GroqServiceError(
                status_code=504,
                error_code="GROQ_TIMEOUT",
                message="Network timeout while awaiting response from Groq API.",
            )

        except GroqConfigurationError:
            raise

        except Exception as e:
            logger.exception("Unexpected error during Groq test request: %s", type(e).__name__)
            raise GroqServiceError(
                status_code=500,
                error_code="GROQ_UNEXPECTED_ERROR",
                message="An unexpected error occurred while communicating with the Groq service.",
            )


def get_groq_service(settings: Settings = Depends(get_settings)) -> GroqService:
    """FastAPI dependency for obtaining a GroqService instance."""
    return GroqService(settings=settings)

