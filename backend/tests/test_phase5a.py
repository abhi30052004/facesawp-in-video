import io
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.services.database import DatabaseService, get_database_service
from app.services.storage_service import LocalStorageService, get_storage_service
from app.services.video_processing import (
    AudioHandler,
    AudioProcessingError,
    FaceAligner,
    FrameProcessor,
    FrameSampler,
    ModelNotConfiguredError,
    UnconfiguredFaceSwapModelAdapter,
    VideoProcessingPipeline,
    VideoReader,
    VideoReaderError,
    VideoStreamMetadata,
    VideoWriter,
    VideoWriterError,
    get_video_processing_pipeline,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class InMemoryAsyncCollection:
    """Mock MongoDB async collection for deterministic testing."""
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
            "swap_jobs": InMemoryAsyncCollection(),
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
    """Ensures test fixtures exist for Phase 5A video pipeline testing."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    audio_video_path = FIXTURES_DIR / "audio_video.mp4"
    no_face_path = FIXTURES_DIR / "no_face_video.mp4"
    test_face_path = FIXTURES_DIR / "test_face.jpg"

    # Create synthetic test face if missing
    if not test_face_path.exists():
        import urllib.request
        url = "https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg"
        urllib.request.urlretrieve(url, test_face_path)

    # Create synthetic no_face_video if missing
    if not no_face_path.exists():
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(no_face_path), fourcc, 30.0, (320, 240))
        for i in range(45):
            writer.write(np.full((240, 320, 3), (i * 5) % 255, dtype=np.uint8))
        writer.release()

    # Create synthetic audio_video with FFmpeg if missing
    if not audio_video_path.exists():
        import subprocess, imageio_ffmpeg
        cmd = [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-c:v", "libx264", "-c:a", "aac",
            str(audio_video_path)
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    return {
        "audio_video": audio_video_path,
        "no_face_video": no_face_path,
        "test_face": test_face_path,
    }


@pytest.fixture
def mock_storage():
    """Provides isolated test storage inside the workspace."""
    test_storage_dir = Path("backend/storage/test_scratch_p5a")
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

    def override_pipeline():
        settings = get_settings()
        return VideoProcessingPipeline(
            settings=settings,
            db_service=mock_db,
            storage_service=mock_storage,
            model_adapter=UnconfiguredFaceSwapModelAdapter(),
        )

    app_instance.dependency_overrides[get_video_processing_pipeline] = override_pipeline

    yield app_instance
    app_instance.dependency_overrides.clear()


# ==============================================================================
# 1. Real MP4 Metadata Extraction
# ==============================================================================

def test_real_mp4_metadata_extraction(ensure_fixtures):
    """Verifies that VideoReader extracts accurate metadata from real video containers."""
    reader = VideoReader()
    meta = reader.inspect(ensure_fixtures["audio_video"])

    assert meta.width == 320
    assert meta.height == 240
    assert meta.fps == 30.0
    assert meta.frame_count >= 30
    assert meta.duration_seconds >= 1.0
    assert meta.codec != ""


# ==============================================================================
# 2. Invalid Video Rejection
# ==============================================================================

def test_invalid_video_rejection(mock_storage):
    """Verifies that non-video files or corrupted containers are rejected."""
    reader = VideoReader()

    # A: Corrupted file with fake extension
    corrupted_file = mock_storage.base_dir / "fake_video.mp4"
    corrupted_file.write_bytes(b"MALICIOUS_SCRIPT_CONTENT_NOT_A_VIDEO")

    with pytest.raises(VideoReaderError) as exc_info:
        reader.inspect(corrupted_file)
    assert exc_info.value.error_code == "INVALID_SIGNATURE"

    # B: Non-existent file
    missing_file = mock_storage.base_dir / "does_not_exist.mp4"
    with pytest.raises(VideoReaderError) as exc_info:
        reader.inspect(missing_file)
    assert exc_info.value.error_code == "FILE_NOT_FOUND"


# ==============================================================================
# 3. Frame Reading and Timestamp Preservation
# ==============================================================================

def test_frame_reading_and_timestamp_preservation(ensure_fixtures):
    """Verifies sequential frame streaming without buffering all frames into RAM."""
    sampler = FrameSampler()
    frames = list(sampler.stream_frames(ensure_fixtures["audio_video"], max_frames=5))

    assert len(frames) == 5
    for idx, (f_idx, ts, img) in enumerate(frames):
        assert f_idx == idx
        assert ts == round(idx / 30.0, 3)
        assert img.shape == (240, 320, 3)


# ==============================================================================
# 4. Face Alignment & Metadata
# ==============================================================================

def test_face_alignment_and_inverse_mapping(ensure_fixtures):
    """Verifies 5-point facial landmark alignment and inverse coordinate transformation."""
    aligner = FaceAligner(target_crop_size=256)
    test_img = cv2.imread(str(ensure_fixtures["test_face"]))
    assert test_img is not None

    # Realistic 5 landmarks in Lena
    landmarks = [
        [220.0, 205.0],  # right eye
        [280.0, 205.0],  # left eye
        [250.0, 245.0],  # nose
        [230.0, 285.0],  # right mouth
        [270.0, 285.0],  # left mouth
    ]

    res = aligner.align_face(test_img, landmarks, bounding_box=(200, 180, 100, 120))
    assert res.aligned_face.shape == (256, 256, 3)
    assert res.metadata.crop_size == 256
    assert res.metadata.affine_matrix.shape == (2, 3)
    assert res.metadata.inverse_affine_matrix.shape == (2, 3)

    # Test reverse mapping (unalign)
    warped, mask = aligner.unalign_face(
        res.aligned_face,
        res.metadata.inverse_affine_matrix,
        test_img.shape[:2],
    )
    assert warped.shape == test_img.shape
    assert mask.shape == test_img.shape[:2]
    assert np.count_nonzero(mask) > 0


# ==============================================================================
# 5. Missing Model Handling
# ==============================================================================

def test_missing_model_handling():
    """Verifies that unconfigured model adapter honestly reports status and blocks fake swaps."""
    adapter = UnconfiguredFaceSwapModelAdapter()
    assert adapter.is_available is False

    meta = adapter.get_metadata()
    assert meta["status"] == "model_not_configured"
    assert "Phase 5B" in meta["description"]

    # Attempting to call swap_face raises ModelNotConfiguredError
    dummy = np.zeros((256, 256, 3), dtype=np.uint8)
    with pytest.raises(ModelNotConfiguredError) as exc_info:
        adapter.swap_face(dummy, dummy)
    assert exc_info.value.error_code == "MODEL_NOT_CONFIGURED"


# ==============================================================================
# 6. Audio Extraction & Preservation
# ==============================================================================

def test_audio_extraction_and_remuxing(ensure_fixtures, mock_storage):
    """Verifies FFmpeg audio stream extraction and container remuxing."""
    handler = AudioHandler()

    # Video with audio
    assert handler.has_audio(ensure_fixtures["audio_video"]) is True
    # Video without audio
    assert handler.has_audio(ensure_fixtures["no_face_video"]) is False

    # Extract audio
    out_audio = mock_storage.base_dir / "extracted.aac"
    extracted = handler.extract_audio(ensure_fixtures["audio_video"], out_audio)
    assert extracted is True
    assert out_audio.exists() and out_audio.stat().st_size > 0

    # Combine with silent video
    out_remux = mock_storage.base_dir / "remuxed.mp4"
    remuxed = handler.combine_audio_video(
        video_path=ensure_fixtures["no_face_video"],
        audio_path=out_audio,
        output_path=out_remux,
    )
    assert remuxed is True
    assert out_remux.exists() and out_remux.stat().st_size > 0
    assert handler.has_audio(out_remux) is True


# ==============================================================================
# 7. Output Validation & Watermark
# ==============================================================================

def test_output_validation_and_watermark(mock_storage):
    """Verifies video container output validation and AI-generated watermark overlay."""
    writer = VideoWriter(watermark_text="BollySwap AI • Synthetic Media")
    temp_video = mock_storage.base_dir / "watermarked_test.mp4"

    writer.open(temp_video, fps=30.0, width=320, height=240)
    for _ in range(15):
        frame = np.full((240, 320, 3), 120, dtype=np.uint8)
        writer.write_frame(frame, watermark=True)
    writer.close()

    assert writer.validate_output(temp_video) is True

    # Validate failure on empty file
    empty_file = mock_storage.base_dir / "empty.mp4"
    empty_file.write_bytes(b"")
    assert writer.validate_output(empty_file) is False


# ==============================================================================
# 8. Temporary Failure Cleanup
# ==============================================================================

def test_failure_cleanup(mock_storage):
    """Verifies that temporary work files are cleaned up safely."""
    temp_a = mock_storage.base_dir / "temp_a.tmp"
    temp_b = mock_storage.base_dir / "temp_b.tmp"
    temp_a.write_bytes(b"data1")
    temp_b.write_bytes(b"data2")

    VideoWriter.cleanup_files([temp_a, temp_b, Path("non_existent_file.tmp")])
    assert not temp_a.exists()
    assert not temp_b.exists()


# ==============================================================================
# 9. Consent Enforcement
# ==============================================================================

def test_consent_enforcement_in_pipeline(mock_db, mock_storage, ensure_fixtures):
    """Verifies that swap processing strictly requires likeness consent affirmation."""
    import asyncio
    settings = get_settings()
    pipeline = VideoProcessingPipeline(
        settings=settings,
        db_service=mock_db,
        storage_service=mock_storage,
        model_adapter=UnconfiguredFaceSwapModelAdapter(),
    )

    # Setup project WITHOUT consent
    mock_db.get_collection("projects").docs.append({
        "project_id": "proj_no_consent",
        "title": "Unauthorized Project",
    })

    with pytest.raises(ValueError) as exc_info:
        asyncio.run(
            pipeline.create_and_evaluate_job(
                project_id="proj_no_consent",
                source_video_id="vid_sample",
                replacement_face_id="face_sample",
                selected_actor_track_id="track_1",
            )
        )
    assert "Likeness authorization consent has not been affirmed" in str(exc_info.value)


# ==============================================================================
# 10. Job Status Transitions & Honest Phase 5A Evaluation
# ==============================================================================

def test_job_status_transition_to_model_not_configured(mock_db, mock_storage, ensure_fixtures):
    """Verifies pipeline transitions to 'model_not_configured' with honest progress < 1.0."""
    import asyncio
    settings = get_settings()
    pipeline = VideoProcessingPipeline(
        settings=settings,
        db_service=mock_db,
        storage_service=mock_storage,
        model_adapter=UnconfiguredFaceSwapModelAdapter(),
    )

    # Register project, consent, video, replacement face
    shutil.copy(ensure_fixtures["audio_video"], mock_storage.base_dir / "source.mp4")
    shutil.copy(ensure_fixtures["test_face"], mock_storage.base_dir / "face.jpg")

    mock_db.get_collection("projects").docs.append({
        "project_id": "proj_p5a_valid",
        "title": "Phase 5A Project",
        "detected_tracks": [{"track_id": "track_1", "label": "Actor #1"}],
    })
    mock_db.get_collection("consent_records").docs.append({
        "project_id": "proj_p5a_valid",
        "consent_given": True,
    })
    mock_db.get_collection("uploads").docs.append({
        "upload_id": "vid_source_1",
        "storage_path": "source.mp4",
    })
    mock_db.get_collection("uploads").docs.append({
        "upload_id": "face_target_1",
        "storage_path": "face.jpg",
    })

    job = asyncio.run(
        pipeline.create_and_evaluate_job(
            project_id="proj_p5a_valid",
            source_video_id="vid_source_1",
            replacement_face_id="face_target_1",
            selected_actor_track_id="track_1",
        )
    )

    assert job.status == "model_not_configured"
    assert job.progress < 1.0
    assert "Phase 5B" in job.current_step
    assert job.output_video_id is None  # No fake output generated


# ==============================================================================
# 11. API Endpoints Integration (POST /swaps/create, GET /swaps/{id}, GET /swaps/{id}/result)
# ==============================================================================

def test_swap_api_endpoints_integration(test_app, mock_db, mock_storage, ensure_fixtures):
    """Tests /swaps/create, /swaps/{id}, and /swaps/{id}/result endpoints."""
    client = TestClient(test_app)

    shutil.copy(ensure_fixtures["audio_video"], mock_storage.base_dir / "source.mp4")
    shutil.copy(ensure_fixtures["test_face"], mock_storage.base_dir / "face.jpg")

    mock_db.get_collection("projects").docs.append({
        "project_id": "proj_api_test",
        "title": "API Test Project",
        "detected_tracks": [{"track_id": "track_1", "label": "Actor #1"}],
    })
    mock_db.get_collection("consent_records").docs.append({
        "project_id": "proj_api_test",
        "consent_given": True,
    })
    mock_db.get_collection("uploads").docs.append({
        "upload_id": "vid_source_api",
        "storage_path": "source.mp4",
    })
    mock_db.get_collection("uploads").docs.append({
        "upload_id": "face_target_api",
        "storage_path": "face.jpg",
    })

    # 1. Trigger POST /api/v1/swaps/create
    payload = {
        "projectId": "proj_api_test",
        "sourceVideoId": "vid_source_api",
        "replacementFaceId": "face_target_api",
        "selectedActorTrackId": "track_1",
    }
    create_res = client.post("/api/v1/swaps/create", json=payload)
    assert create_res.status_code == 200, create_res.text
    create_data = create_res.json()["data"]

    assert create_data["status"] == "model_not_configured"
    assert create_data["progress"] == 0.25
    assert create_data["outputVideoId"] is None
    job_id = create_data["jobId"]

    # 2. Poll GET /api/v1/swaps/{job_id}
    job_res = client.get(f"/api/v1/swaps/{job_id}")
    assert job_res.status_code == 200
    assert job_res.json()["data"]["jobId"] == job_id
    assert job_res.json()["data"]["status"] == "model_not_configured"

    # 3. Fetch GET /api/v1/swaps/{job_id}/result
    result_res = client.get(f"/api/v1/swaps/{job_id}/result")
    assert result_res.status_code == 200
    res_data = result_res.json()["data"]
    assert res_data["status"] == "model_not_configured"
    assert res_data["isSwapped"] is False
    assert "Phase 5B" in res_data["message"]

    # 4. Unknown job returns 404
    missing_res = client.get("/api/v1/swaps/swap_nonexistent")
    assert missing_res.status_code == 404
