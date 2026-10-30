import hashlib
import io
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.services.database import DatabaseService, get_database_service
from app.services.storage_service import LocalStorageService, get_storage_service
from app.services.detection_service import DetectionService, get_detection_service
from app.services.face_detector import FaceDetectorYuNet, DetectedFace
from app.services.face_tracker import FaceTracker, FaceTrackHypothesis, calculate_iou
from app.services.video_service import VideoService, VideoProcessingError, SampledFrame
import cv2
import numpy as np


FIXTURES_DIR = Path(__file__).parent / "fixtures"
MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "face_detection_yunet_2023mar.onnx"
PINNED_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"


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

    async def update_one(self, query, update):
        for doc in self.docs:
            match = all(doc.get(k) == v for k, v in query.items())
            if match:
                if "$set" in update:
                    doc.update(update["$set"])
                res = MagicMock()
                res.modified_count = 1
                return res
        res = MagicMock()
        res.modified_count = 0
        return res

    async def find_one(self, query, sort=None):
        docs_to_search = reversed(self.docs) if sort else self.docs
        for doc in docs_to_search:
            match = all(doc.get(k) == v for k, v in query.items())
            if match:
                return dict(doc)
        return None

    def find(self, query=None):
        docs_copy = [dict(d) for d in self.docs]

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
            "detection_jobs": InMemoryAsyncCollection(),
        }

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def status(self) -> str:
        return "connected" if self._connected else "disconnected"

    def get_collection(self, name: str):
        if name not in self._collections:
            self._collections[name] = InMemoryAsyncCollection()
        return self._collections[name]


@pytest.fixture(scope="module")
def ensure_fixtures():
    """Ensures test fixtures exist for video and face detection tests."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    test_face_path = FIXTURES_DIR / "test_face.jpg"
    no_face_path = FIXTURES_DIR / "no_face_video.mp4"
    face_video_path = FIXTURES_DIR / "face_video.mp4"

    # 1. Download or synthesize test face if not present
    if not test_face_path.exists():
        import urllib.request
        url = "https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg"
        urllib.request.urlretrieve(url, test_face_path)

    # 2. Synthesize no-face video if not present
    if not no_face_path.exists():
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(no_face_path), fourcc, 30.0, (320, 240))
        for i in range(45):
            writer.write(np.full((240, 320, 3), (i * 5) % 255, dtype=np.uint8))
        writer.release()

    # 3. Synthesize face video if not present
    if not face_video_path.exists():
        test_img = cv2.imread(str(test_face_path))
        face_crop = cv2.resize(test_img, (140, 140))
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(face_video_path), fourcc, 30.0, (320, 240))
        for _ in range(45):
            canvas = np.zeros((240, 320, 3), dtype=np.uint8)
            canvas[50:190, 90:230] = face_crop
            writer.write(canvas)
        writer.release()

    return {
        "face_img": test_face_path,
        "no_face_video": no_face_path,
        "face_video": face_video_path,
    }


@pytest.fixture
def mock_storage():
    """Provides isolated test storage inside the workspace."""
    test_storage_dir = Path("backend/storage/test_scratch_p4")
    test_storage_dir.mkdir(parents=True, exist_ok=True)
    service = LocalStorageService(base_dir=test_storage_dir)
    yield service
    if test_storage_dir.exists():
        shutil.rmtree(test_storage_dir, ignore_errors=True)


@pytest.fixture
def mock_db():
    return InMemoryDatabaseService(connected=True)


@pytest.fixture
def test_app(mock_db, mock_storage):
    """Configures FastAPI test application with isolated dependencies."""
    app_instance = create_app()

    app_instance.dependency_overrides[get_database_service] = lambda: mock_db
    app_instance.dependency_overrides[get_storage_service] = lambda: mock_storage

    def override_detection_service():
        settings = get_settings()
        return DetectionService(
            settings=settings,
            db_service=mock_db,
            storage_service=mock_storage,
        )

    app_instance.dependency_overrides[get_detection_service] = override_detection_service

    yield app_instance
    app_instance.dependency_overrides.clear()


# ==============================================================================
# Model and Checksum Verification Tests
# ==============================================================================

def test_yunet_model_availability_and_checksum():
    """Verifies that the official YuNet ONNX model exists and matches pinned SHA-256."""
    assert MODEL_PATH.exists(), f"Model file missing at: {MODEL_PATH}"
    actual_sha = hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()
    assert actual_sha == PINNED_SHA256, f"YuNet SHA-256 mismatch! Got {actual_sha}, expected {PINNED_SHA256}"

    license_file = MODEL_PATH.parent / "LICENSE_YUNET.txt"
    assert license_file.exists(), "YuNet license attribution notice missing."
    assert "OpenCV Zoo" in license_file.read_text()


# ==============================================================================
# Video Processing Service Tests
# ==============================================================================

def test_video_metadata_extraction(ensure_fixtures):
    """Tests OpenCV VideoCapture metadata extraction."""
    service = VideoService()
    meta = service.inspect_video(ensure_fixtures["no_face_video"])
    assert meta.width == 320
    assert meta.height == 240
    assert meta.fps == 30.0
    assert meta.frame_count >= 45
    assert meta.duration_seconds >= 1.5


def test_frame_sampling(ensure_fixtures):
    """Tests frame sampling interval and frame limits."""
    service = VideoService(sample_interval_seconds=0.5, max_sampled_frames=10)
    sampled = service.sample_frames(ensure_fixtures["no_face_video"])
    assert len(sampled) > 0
    assert len(sampled) <= 10
    first_frame = sampled[0]
    assert first_frame.frame_index == 0
    assert first_frame.timestamp_seconds == 0.0
    assert first_frame.image.shape == (240, 320, 3)


def test_corrupted_video_handling(mock_storage):
    """Tests that unreadable or corrupted files raise a clean VideoProcessingError."""
    corrupted_file = mock_storage.base_dir / "corrupted.mp4"
    corrupted_file.write_bytes(b"NOT_A_REAL_VIDEO_HEADER_DATA_123456789")

    service = VideoService()
    with pytest.raises(VideoProcessingError):
        service.inspect_video(corrupted_file)

    with pytest.raises(VideoProcessingError):
        service.sample_frames(corrupted_file)


# ==============================================================================
# Real Face Detection Model Inference Tests
# ==============================================================================

def test_real_yunet_inference_on_face_image(ensure_fixtures):
    """Executes real YuNet face detection on standard portrait image."""
    detector = FaceDetectorYuNet(model_path=MODEL_PATH, confidence_threshold=0.6)
    img = cv2.imread(str(ensure_fixtures["face_img"]))
    assert img is not None

    frame = SampledFrame(
        frame_index=0,
        timestamp_seconds=0.0,
        image=img,
        original_width=img.shape[1],
        original_height=img.shape[0],
        scale_factor=1.0,
    )

    detected = detector.detect_in_frame(frame)
    assert len(detected) >= 1
    face = detected[0]
    assert face.confidence > 0.6
    assert len(face.bbox) == 4
    assert face.bbox[2] > 20 and face.bbox[3] > 20  # width, height
    assert len(face.landmarks) == 5
    assert len(face.thumbnail_bytes) > 100  # Valid JPEG buffer


def test_real_yunet_inference_on_no_face(ensure_fixtures):
    """Executes YuNet detection on a blank image, ensuring no false positives."""
    detector = FaceDetectorYuNet(model_path=MODEL_PATH, confidence_threshold=0.6)
    blank = np.zeros((240, 320, 3), dtype=np.uint8)

    frame = SampledFrame(
        frame_index=0,
        timestamp_seconds=0.0,
        image=blank,
        original_width=320,
        original_height=240,
        scale_factor=1.0,
    )

    detected = detector.detect_in_frame(frame)
    assert len(detected) == 0


# ==============================================================================
# Face Tracking & IoU Grouping Tests
# ==============================================================================

def test_iou_calculation():
    """Tests bounding box IoU calculation accuracy."""
    box_a = (10, 10, 50, 50)
    box_b = (10, 10, 50, 50)
    assert calculate_iou(box_a, box_b) == 1.0

    box_c = (100, 100, 50, 50)
    assert calculate_iou(box_a, box_c) == 0.0

    box_d = (35, 10, 50, 50)
    iou = calculate_iou(box_a, box_d)
    assert 0.0 < iou < 1.0


def test_track_clustering_continuous_and_separate():
    """Tests that overlapping continuous detections cluster into 1 track and distant ones separate."""
    tracker = FaceTracker(iou_threshold=0.25, max_time_gap_seconds=3.0)

    det1 = DetectedFace(
        frame_index=0,
        timestamp_seconds=0.0,
        confidence=0.92,
        bbox=(50, 50, 100, 100),
        landmarks=[[60, 60], [80, 60], [70, 75], [65, 90], [85, 90]],
        thumbnail_bytes=b"dummy1",
    )
    # Consecutive frame: slight motion, high overlap
    det2 = DetectedFace(
        frame_index=30,
        timestamp_seconds=1.0,
        confidence=0.88,
        bbox=(54, 52, 98, 98),
        landmarks=[[64, 62], [84, 62], [74, 77], [69, 92], [89, 92]],
        thumbnail_bytes=b"dummy2",
    )
    # Second person on screen: different location
    det3 = DetectedFace(
        frame_index=30,
        timestamp_seconds=1.0,
        confidence=0.85,
        bbox=(200, 50, 80, 80),
        landmarks=[[210, 60], [230, 60], [220, 75], [215, 90], [235, 90]],
        thumbnail_bytes=b"dummy3",
    )

    tracks = tracker.cluster_tracks([det1, det2, det3])
    assert len(tracks) == 2
    # First track should be the main actor with 2 detections
    assert tracks[0].track_id == "track_1"
    assert tracks[0].occurrences == 2
    assert "Principal Subject" in tracks[0].label
    # Second track should be Actor #2 with 1 detection
    assert tracks[1].track_id == "track_2"
    assert tracks[1].occurrences == 1


# ==============================================================================
# API Endpoints Integration Tests
# ==============================================================================

def test_detect_faces_endpoint_real_pipeline(test_app, mock_db, mock_storage, ensure_fixtures):
    """End-to-end integration test of POST /api/v1/faces/detect using real YuNet inference."""
    client = TestClient(test_app)

    # 1. Register a video file in mock storage & mock DB
    shutil.copy(ensure_fixtures["face_video"], mock_storage.base_dir / "face_video.mp4")
    mock_db.get_collection("uploads").docs.append({
        "upload_id": "vid_integration_test",
        "file_type": "video",
        "filename": "face_video.mp4",
        "storage_path": "face_video.mp4",
        "content_type": "video/mp4",
        "size_bytes": 1024,
    })
    mock_db.get_collection("projects").docs.append({
        "project_id": "proj_p4_test",
        "title": "Phase 4 Test Movie",
        "status": "uploaded",
    })

    # 2. Trigger face detection
    payload = {
        "projectId": "proj_p4_test",
        "videoId": "vid_integration_test",
    }
    response = client.post("/api/v1/faces/detect", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()["data"]

    assert data["projectId"] == "proj_p4_test"
    assert data["videoId"] == "vid_integration_test"
    assert data["detectionStatus"] == "completed"
    assert data["progress"] == 1.0
    assert data["detectedFaceCount"] >= 1
    assert len(data["tracks"]) >= 1

    first_track = data["tracks"][0]
    assert first_track["trackId"] == "track_1"
    assert first_track["confidence"] > 0.6
    assert first_track["thumbnailFileId"].startswith("thumb_")
    assert "/api/v1/files/" in first_track["thumbnailUrl"]
    assert len(first_track["timestamps"]) >= 1

    # 3. Verify track selection persistence
    select_payload = {"selectedTrackId": "track_1"}
    select_res = client.post("/api/v1/projects/proj_p4_test/faces/select", json=select_payload)
    assert select_res.status_code == 200
    assert select_res.json()["data"]["selectedTrackId"] == "track_1"

    # 4. Verify GET /api/v1/projects/{project_id}/faces
    faces_res = client.get("/api/v1/projects/proj_p4_test/faces")
    assert faces_res.status_code == 200
    assert faces_res.json()["data"]["selectedTrackId"] == "track_1"
    assert len(faces_res.json()["data"]["tracks"]) >= 1

    # 5. Verify GET /api/v1/faces/detect/{job_id}
    job_id = data["detectionJobId"]
    job_res = client.get(f"/api/v1/faces/detect/{job_id}")
    assert job_res.status_code == 200
    assert job_res.json()["data"]["detectionJobId"] == job_id


def test_detect_faces_invalid_video_returns_404(test_app):
    """POST /api/v1/faces/detect with unknown video ID returns 404."""
    client = TestClient(test_app)
    response = client.post(
        "/api/v1/faces/detect",
        json={"projectId": "proj_unknown", "videoId": "vid_nonexistent"},
    )
    assert response.status_code == 404


def test_select_nonexistent_track_returns_400(test_app, mock_db):
    """POST /api/v1/projects/{id}/faces/select with invalid track returns 400."""
    client = TestClient(test_app)
    mock_db.get_collection("projects").docs.append({
        "project_id": "proj_empty",
        "title": "Empty Project",
    })
    response = client.post(
        "/api/v1/projects/proj_empty/faces/select",
        json={"selectedTrackId": "track_invalid_999"},
    )
    assert response.status_code == 400


def test_get_nonexistent_detection_job_returns_404(test_app):
    """GET /api/v1/faces/detect/{id} with unknown job returns 404."""
    client = TestClient(test_app)
    response = client.get("/api/v1/faces/detect/job_nonexistent")
    assert response.status_code == 404


def test_database_offline_returns_503_for_detection(test_app, mock_db):
    """Endpoints return 503 when MongoDB is disconnected."""
    client = TestClient(test_app)
    mock_db._connected = False

    res1 = client.post(
        "/api/v1/faces/detect",
        json={"projectId": "proj_1", "videoId": "vid_1"},
    )
    assert res1.status_code == 503

    res2 = client.get("/api/v1/faces/detect/job_1")
    assert res2.status_code == 503

    res3 = client.get("/api/v1/projects/proj_1/faces")
    assert res3.status_code == 503
