from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from groq import (
    AuthenticationError,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
)
import httpx

from app.core.config import Settings, get_settings
from app.main import app
from app.services.groq_service import GroqService, get_groq_service


def test_groq_test_missing_api_key_returns_400(client: TestClient):
    """
    Verify that invoking /api/v1/groq/test with an unconfigured API key
    returns HTTP 400 and does not leak secrets.
    """
    unconfigured_settings = Settings(
        GROQ_API_KEY="",
        GROQ_MODEL="llama-3.3-70b-versatile",
    )
    app.dependency_overrides[get_settings] = lambda: unconfigured_settings

    try:
        response = client.post("/api/v1/groq/test", json={"prompt": "Test connectivity"})
        assert response.status_code == 400
        payload = response.json()
        assert payload["success"] is False
        assert payload["error"]["error_code"] == "GROQ_NOT_CONFIGURED"
        assert "GROQ_API_KEY" in payload["error"]["message"]
        # Ensure no internal secrets leaked
        assert "gsk_" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_groq_test_placeholder_api_key_returns_400(client: TestClient):
    """
    Verify that placeholder keys like YOUR_GROQ_API_KEY produce a clean 400.
    """
    placeholder_settings = Settings(
        GROQ_API_KEY="YOUR_GROQ_API_KEY",
        GROQ_MODEL="llama-3.3-70b-versatile",
    )
    app.dependency_overrides[get_settings] = lambda: placeholder_settings

    try:
        response = client.post("/api/v1/groq/test", json={})
        assert response.status_code == 400
        payload = response.json()
        assert payload["success"] is False
        assert payload["error"]["error_code"] == "GROQ_NOT_CONFIGURED"
    finally:
        app.dependency_overrides.clear()


def test_groq_test_success_with_mock(client: TestClient):
    """
    Verify successful Groq inference mock without executing paid live requests.
    """
    mock_choice = MagicMock()
    mock_choice.message.content = "BollySwap Neural Director is fully synchronized."
    mock_choice.finish_reason = "stop"

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_completion.usage = MagicMock()
    mock_completion.usage.total_tokens = 18

    mock_groq_client = MagicMock()
    mock_groq_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    configured_settings = Settings(
        GROQ_API_KEY="gsk_mock_test_key_for_unit_tests_only_9999",
        GROQ_MODEL="llama-3.3-70b-versatile",
    )
    mock_service = GroqService(settings=configured_settings, client=mock_groq_client)

    app.dependency_overrides[get_settings] = lambda: configured_settings
    app.dependency_overrides[get_groq_service] = lambda: mock_service

    try:
        response = client.post(
            "/api/v1/groq/test",
            json={"prompt": "Director action call"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["data"]["model"] == "llama-3.3-70b-versatile"
        assert payload["data"]["response_text"] == "BollySwap Neural Director is fully synchronized."
        assert payload["data"]["tokens_used"] == 18
        assert payload["data"]["latency_ms"] >= 0
        assert "gsk_" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_groq_test_authentication_error_with_mock(client: TestClient):
    """
    Verify that an upstream AuthenticationError returns a clean HTTP 401 without exposing keys.
    """
    mock_groq_client = MagicMock()
    request_dummy = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response_dummy = httpx.Response(401, request=request_dummy)
    mock_groq_client.chat.completions.create = AsyncMock(
        side_effect=AuthenticationError(
            message="Invalid API Key provided",
            response=response_dummy,
            body={"error": {"message": "Invalid API Key"}},
        )
    )

    configured_settings = Settings(
        GROQ_API_KEY="gsk_mock_invalid_key_9999",
        GROQ_MODEL="llama-3.3-70b-versatile",
    )
    mock_service = GroqService(settings=configured_settings, client=mock_groq_client)

    app.dependency_overrides[get_settings] = lambda: configured_settings
    app.dependency_overrides[get_groq_service] = lambda: mock_service

    try:
        response = client.post("/api/v1/groq/test", json={"prompt": "Test auth failure"})
        assert response.status_code == 401
        payload = response.json()
        assert payload["success"] is False
        assert payload["error"]["error_code"] == "GROQ_AUTH_ERROR"
        assert "Groq authentication failed" in payload["error"]["message"]
        # Absolute secret isolation check
        assert "gsk_" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_groq_test_timeout_error_with_mock(client: TestClient):
    """
    Verify that an upstream APITimeoutError returns a clean HTTP 504.
    """
    mock_groq_client = MagicMock()
    request_dummy = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    mock_groq_client.chat.completions.create = AsyncMock(
        side_effect=APITimeoutError(request=request_dummy)
    )

    configured_settings = Settings(
        GROQ_API_KEY="gsk_mock_test_key_9999",
        GROQ_MODEL="llama-3.3-70b-versatile",
    )
    mock_service = GroqService(settings=configured_settings, client=mock_groq_client)

    app.dependency_overrides[get_settings] = lambda: configured_settings
    app.dependency_overrides[get_groq_service] = lambda: mock_service

    try:
        response = client.post("/api/v1/groq/test", json={})
        assert response.status_code == 504
        payload = response.json()
        assert payload["success"] is False
        assert payload["error"]["error_code"] == "GROQ_TIMEOUT"
        assert "timed out" in payload["error"]["message"]
    finally:
        app.dependency_overrides.clear()


def test_groq_test_connection_error_with_mock(client: TestClient):
    """
    Verify that an upstream APIConnectionError returns HTTP 502 without exposing stack traces.
    """
    mock_groq_client = MagicMock()
    request_dummy = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    mock_groq_client.chat.completions.create = AsyncMock(
        side_effect=APIConnectionError(request=request_dummy)
    )

    configured_settings = Settings(
        GROQ_API_KEY="gsk_mock_test_key_9999",
        GROQ_MODEL="llama-3.3-70b-versatile",
    )
    mock_service = GroqService(settings=configured_settings, client=mock_groq_client)

    app.dependency_overrides[get_settings] = lambda: configured_settings
    app.dependency_overrides[get_groq_service] = lambda: mock_service

    try:
        response = client.post("/api/v1/groq/test", json={})
        assert response.status_code == 502
        payload = response.json()
        assert payload["success"] is False
        assert payload["error"]["error_code"] == "GROQ_CONNECTION_ERROR"
    finally:
        app.dependency_overrides.clear()

