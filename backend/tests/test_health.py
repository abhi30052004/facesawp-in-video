from fastapi.testclient import TestClient


def test_root_health_returns_200(client: TestClient):
    """Verify that GET /health returns HTTP 200 with structured health metrics."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert data["data"]["status"] in ("online", "degraded")
    assert data["data"]["version"] in ("0.2.0", "0.3.0")
    assert "environment" in data["data"]
    assert "groq_configured" in data["data"]
    assert "ai_worker_status" in data["data"]
    assert "databaseConnected" in data["data"] or "database_connected" in data["data"]
    assert "databaseStatus" in data["data"] or "database_status" in data["data"]


def test_api_v1_health_returns_200_and_compatible_fields(client: TestClient):
    """
    Verify that GET /api/v1/health returns HTTP 200 and matches the frontend contracts:
    status, version, gpuWorkersAvailable, avgQueueWaitSec, activeModel, databaseConnected.
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True

    health_data = payload["data"]
    assert health_data["status"] in ("online", "degraded")
    assert health_data["version"] in ("0.2.0", "0.3.0")
    assert health_data["activeModel"] == "BollyMesh-v2.4-NeuralBlend"
    assert health_data["gpuWorkersAvailable"] == 0
    assert health_data["avgQueueWaitSec"] == 0.0
    assert "groq_configured" in health_data
    assert "databaseConnected" in health_data or "database_connected" in health_data


def test_health_does_not_leak_secrets(client: TestClient):
    """Ensure health endpoints never expose API keys, database strings or passwords."""
    for path in ["/health", "/api/v1/health"]:
        response = client.get(path)
        content = response.text.lower()
        # Verify secret tokens and connection strings are absent
        assert "gsk_" not in content
        assert "mongodb+srv://" not in content
        assert "abhijitve" not in content
