import io
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from app.services.database import DatabaseService, get_database_service
from app.services.storage_service import LocalStorageService, get_storage_service
from app.services.project_service import ProjectService, get_project_service


# Standard Valid Magic Byte Sequences for Testing
VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
VALID_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 100
VALID_MP4_BYTES = b"\x00\x00\x00 ftypisom\x00\x00\x02\x00isomiso2avc1mp41" + b"\x00" * 200
INVALID_TEXT_BYTES = b"This is a fake text file claiming to be video or image"


class InMemoryAsyncCollection:
    """Mock MongoDB async collection for offline deterministic test execution."""
    def __init__(self):
        self.docs = []

    async def insert_one(self, doc):
        stored = dict(doc)
        stored["_id"] = f"mock_{len(self.docs)}"
        self.docs.append(stored)
        res = MagicMock()
        res.inserted_id = stored["_id"]
        return res

    async def find_one(self, query, sort=None):
        for doc in reversed(self.docs) if sort else self.docs:
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                res = dict(doc)
                return res
        return None

    def find(self, query=None):
        docs_copy = [dict(d) for d in self.docs]
        cursor = MagicMock()

        class MockCursor:
            def __init__(self, items):
                self.items = items

            def sort(self, *args, **kwargs):
                return self

            def skip(self, n):
                self.items = self.items[n:]
                return self

            def limit(self, n):
                self.items = self.items[:n]
                return self

            def __aiter__(self):
                self._iter = iter(self.items)
                return self

            async def __anext__(self):
                try:
                    return next(self._iter)
                except StopIteration:
                    raise StopAsyncIteration

        return MockCursor(docs_copy)

    async def create_index(self, *args, **kwargs):
        return "idx_created"


class InMemoryDatabaseService(DatabaseService):
    """Mock database service using in-memory mock collections."""
    def __init__(self, connected: bool = True):
        super().__init__()
        self._connected = connected
        self._status_message = "Mocked in-memory DB"
        self._collections = {
            "projects": InMemoryAsyncCollection(),
            "processing_jobs": InMemoryAsyncCollection(),
            "consent_records": InMemoryAsyncCollection(),
            "uploads": InMemoryAsyncCollection(),
        }

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def status(self) -> str:
        return "connected" if self._connected else "disconnected"

    def get_collection(self, name: str):
        if not self._connected:
            raise RuntimeError("Database is disconnected")
        if name not in self._collections:
            self._collections[name] = InMemoryAsyncCollection()
        return self._collections[name]

    async def connect(self, uri, db_name="bollyswap"):
        self._connected = True

    async def disconnect(self):
        self._connected = False

    async def ping(self):
        return self._connected


@pytest.fixture
def mock_storage():
    """Provides a temporary isolated local storage directory inside workspace."""
    test_dir = Path(__file__).resolve().parent.parent / "storage" / "test_scratch"
    test_dir.mkdir(parents=True, exist_ok=True)
    service = LocalStorageService(base_dir=test_dir)
    yield service
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def mock_db_service():
    """Provides an in-memory mock database service."""
    return InMemoryDatabaseService(connected=True)


@pytest.fixture
def phase3_client(mock_storage, mock_db_service):
    """Test client with isolated storage and in-memory mock database."""
    proj_service = ProjectService(db_service=mock_db_service)

    app.dependency_overrides[get_storage_service] = lambda: mock_storage
    app.dependency_overrides[get_database_service] = lambda: mock_db_service
    app.dependency_overrides[get_project_service] = lambda: proj_service

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# -------------------------------------------------------------
# 1. MongoDB Connection Lifecycle Tests
# -------------------------------------------------------------

def test_mongodb_lifecycle_mock():
    """Verify database connection lifecycle handling and disconnection."""
    db_mock = InMemoryDatabaseService(connected=False)
    assert db_mock.is_connected is False
    assert db_mock.status == "disconnected"

    # Connect
    import asyncio
    asyncio.run(db_mock.connect("mock://localhost"))
    assert db_mock.is_connected is True
    assert db_mock.status == "connected"

    # Disconnect
    asyncio.run(db_mock.disconnect())
    assert db_mock.is_connected is False
    assert db_mock.status == "disconnected"


# -------------------------------------------------------------
# 2. File Upload Tests (Video & Face)
# -------------------------------------------------------------

def test_successful_video_upload(phase3_client: TestClient):
    """Verify uploading a valid MP4 video creates a storage file and returns metadata."""
    file_content = VALID_MP4_BYTES
    files = {"file": ("scene_01.mp4", io.BytesIO(file_content), "video/mp4")}

    response = phase3_client.post("/api/v1/videos/upload", files=files)
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["fileId"].startswith("vid_")
    assert data["filename"] == "scene_01.mp4"
    assert "/files/vid_" in data["storageUrl"]
    assert data["sizeBytes"] == len(file_content)


def test_successful_face_upload_png(phase3_client: TestClient):
    """Verify uploading a valid PNG face photo succeeds."""
    file_content = VALID_PNG_BYTES
    files = {"file": ("actor_portrait.png", io.BytesIO(file_content), "image/png")}

    response = phase3_client.post("/api/v1/faces/upload", files=files)
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["faceId"].startswith("face_")
    assert data["qualityPassed"] is True
    assert "/files/face_" in data["previewUrl"]


def test_successful_face_upload_jpg(phase3_client: TestClient):
    """Verify uploading a valid JPEG face photo succeeds."""
    file_content = VALID_JPEG_BYTES
    files = {"file": ("lead_face.jpg", io.BytesIO(file_content), "image/jpeg")}

    response = phase3_client.post("/api/v1/faces/upload", files=files)
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["faceId"].startswith("face_")


def test_upload_invalid_extension_rejected(phase3_client: TestClient):
    """Verify rejecting disallowed extensions (e.g. .exe or .txt)."""
    files = {"file": ("malicious.exe", io.BytesIO(b"MZ...fake"), "application/octet-stream")}
    response = phase3_client.post("/api/v1/videos/upload", files=files)
    assert response.status_code == 400
    assert response.json()["error"]["error_code"] == "INVALID_EXTENSION"


def test_upload_invalid_signature_rejected(phase3_client: TestClient):
    """Verify rejecting a file with an .mp4 extension but text/corrupt content."""
    files = {"file": ("spoofed.mp4", io.BytesIO(INVALID_TEXT_BYTES), "video/mp4")}
    response = phase3_client.post("/api/v1/videos/upload", files=files)
    assert response.status_code == 400
    assert response.json()["error"]["error_code"] == "INVALID_FILE_SIGNATURE"


def test_upload_oversized_image_rejected(phase3_client: TestClient, mock_storage):
    """Verify rejecting image uploads that exceed the 10MB limit."""
    # Create dummy 1KB JPEG
    oversized_bytes = VALID_JPEG_BYTES + (b"\x00" * 1024)
    files = {"file": ("huge_photo.jpg", io.BytesIO(oversized_bytes), "image/jpeg")}

    # Mock max image size setting to 500 bytes
    custom_settings = Settings(MAX_IMAGE_SIZE_BYTES=500)
    app.dependency_overrides[get_settings] = lambda: custom_settings

    response = phase3_client.post("/api/v1/faces/upload", files=files)
    assert response.status_code == 413
    assert response.json()["error"]["error_code"] == "FILE_TOO_LARGE"


# -------------------------------------------------------------
# 3. Consent Tracking Tests
# -------------------------------------------------------------

def test_consent_recording_success(phase3_client: TestClient):
    """Verify recording likeness consent returns HTTP 200 and stores record."""
    payload = {
        "projectId": "proj_demo_test_01",
        "consentGiven": True,
        "consentTextVersion": "v1.0",
        "affirmation": "I affirm that I hold rights to synthesize this actor.",
    }
    response = phase3_client.post("/api/v1/consent", json=payload)
    assert response.status_code == 200

    data = response.json()["data"]
    assert data["projectId"] == "proj_demo_test_01"
    assert data["consentGiven"] is True
    assert data["consentId"].startswith("cst_")


def test_consent_recording_rejected_if_false(phase3_client: TestClient):
    """Verify that consentGiven=False is rejected with HTTP 400."""
    payload = {
        "projectId": "proj_demo_test_02",
        "consentGiven": False,
    }
    response = phase3_client.post("/api/v1/consent", json=payload)
    assert response.status_code == 400


# -------------------------------------------------------------
# 4. Project and Job Creation & Retrieval Tests
# -------------------------------------------------------------

def test_project_creation_and_job_initialization(phase3_client: TestClient):
    """
    Verify creating a project automatically initializes an honest job in 'uploaded' state.
    """
    project_payload = {
        "title": "Mumbai Monsoon Duet",
        "originalVideoId": "vid_mock_12345",
        "replacementFaceId": "face_mock_67890",
        "consentConfirmed": True,
    }

    response = phase3_client.post("/api/v1/projects", json=project_payload)
    assert response.status_code == 201

    payload = response.json()
    assert payload["success"] is True
    proj_data = payload["data"]
    assert proj_data["projectId"].startswith("proj_")
    assert proj_data["title"] == "Mumbai Monsoon Duet"
    assert proj_data["status"] == "uploaded"

    active_job = proj_data["activeJob"]
    assert active_job is not None
    assert active_job["jobId"].startswith("job_")
    assert active_job["status"] == "uploaded"
    assert active_job["progress"] == 0.0

    # Test Project Retrieval by ID
    get_res = phase3_client.get(f"/api/v1/projects/{proj_data['projectId']}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["projectId"] == proj_data["projectId"]

    # Test Job Retrieval by ID
    job_res = phase3_client.get(f"/api/v1/jobs/{active_job['jobId']}")
    assert job_res.status_code == 200
    assert job_res.json()["data"]["jobId"] == active_job["jobId"]
    assert job_res.json()["data"]["status"] == "uploaded"


def test_list_projects(phase3_client: TestClient):
    """Verify retrieving list of projects."""
    response = phase3_client.get("/api/v1/projects")
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert isinstance(response.json()["data"], list)


# -------------------------------------------------------------
# 5. Database Unavailable Graceful Behavior Tests
# -------------------------------------------------------------

def test_database_offline_behavior(mock_storage):
    """Verify that when database is unavailable, endpoints return graceful 503 errors."""
    offline_db = InMemoryDatabaseService(connected=False)
    proj_service = ProjectService(db_service=offline_db)

    app.dependency_overrides[get_storage_service] = lambda: mock_storage
    app.dependency_overrides[get_database_service] = lambda: offline_db
    app.dependency_overrides[get_project_service] = lambda: proj_service

    try:
        with TestClient(app) as offline_client:
            # Health check reports degraded / disconnected rather than crashing
            health_res = offline_client.get("/api/v1/health")
            assert health_res.status_code == 200
            assert health_res.json()["data"]["databaseConnected"] is False
            assert health_res.json()["data"]["databaseStatus"] == "disconnected"

            # Project creation returns 503
            proj_res = offline_client.post(
                "/api/v1/projects",
                json={
                    "title": "Offline Project",
                    "originalVideoId": "vid_1",
                    "replacementFaceId": "face_1",
                    "consentConfirmed": True,
                },
            )
            assert proj_res.status_code == 503
            assert "Database unavailable" in proj_res.json()["error"]["message"]
    finally:
        app.dependency_overrides.clear()
