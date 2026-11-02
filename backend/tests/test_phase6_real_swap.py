"""
Phase 6 — Real Neural Face Replacement Verification Tests.
Guarantees real neural inference via Inswapper 128 and ArcFace ResNet-50.
Verifies that outputs are genuinely neural swapped and container valid.
"""

from pathlib import Path
import cv2
import numpy as np
import pytest

from app.core.config import get_settings
from app.services.face_detector import FaceDetectorYuNet
from app.services.face_swap.face_swap_engine import (
    FaceSwapEngine,
    FaceSwapEngineConfig,
)
from app.services.face_swap.model_loader import FaceSwapModelLoader
from app.services.face_swap.model_validator import ModelValidator
from app.services.video_processing.model_adapter import (
    LicensedFaceSwapModelAdapter,
    get_face_swap_model_adapter,
)
from app.services.video_processing.processing_pipeline import VideoProcessingPipeline
from app.services.storage_service import LocalStorageService
from app.services.database import DatabaseService


@pytest.fixture
def models_dir() -> Path:
    settings = get_settings()
    return Path(settings.resolved_face_swap_model_path).parent


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


def test_model_validator_checks(models_dir):
    """Verifies that model validator verifies real weights and SHA-256."""
    inswapper_path = models_dir / "inswapper_128.onnx"
    arcface_path = models_dir / "w600k_r50.onnx"

    assert inswapper_path.exists(), "inswapper_128.onnx must exist"
    assert arcface_path.exists(), "w600k_r50.onnx must exist"

    validator = ModelValidator()
    report = validator.validate_engine(inswapper_path, arcface_path)

    assert report.is_valid is True
    assert report.status == "ready"
    assert report.inswapper_valid is True
    assert report.arcface_valid is True
    assert report.provider_valid is True
    assert report.inswapper_sha256 is not None
    assert report.arcface_sha256 is not None
    assert report.inswapper_size_bytes > 500 * 1024 * 1024  # > 500 MB
    assert report.arcface_size_bytes > 150 * 1024 * 1024    # > 150 MB


def test_model_loader_and_emap(models_dir):
    """Verifies that model loader initializes sessions and extracts 512x512 EMAP."""
    inswapper_path = models_dir / "inswapper_128.onnx"
    arcface_path = models_dir / "w600k_r50.onnx"

    loader = FaceSwapModelLoader(inswapper_path, arcface_path, provider="CPUExecutionProvider")
    bundle = loader.load()

    assert bundle.swap_session is not None
    assert bundle.recognition_session is not None
    assert bundle.emap.shape == (512, 512)
    assert any(i["name"] in ("target", "input") for i in bundle.swap_inputs)
    assert any(i["name"] in ("source", "source_emb") for i in bundle.swap_inputs)
    assert len(bundle.swap_outputs) >= 1

    loader.unload()


def test_neural_single_frame_swap(models_dir, fixtures_dir):
    """
    Verifies real neural face swap on a single video frame.
    Confirms non-simulated inference where the output face differs from the original.
    """
    inswapper_path = models_dir / "inswapper_128.onnx"
    arcface_path = models_dir / "w600k_r50.onnx"
    yunet_path = models_dir / "face_detection_yunet_2023mar.onnx"

    detector = FaceDetectorYuNet(yunet_path)

    # 1. Load source face image and detect landmarks
    source_img_path = fixtures_dir / "test_face.jpg"
    assert source_img_path.exists()
    source_img = cv2.imread(str(source_img_path))
    assert source_img is not None

    source_dets = detector.detect_in_bgr_frame(source_img, 0, 0.0)
    assert len(source_dets) >= 1, "Face must be detected in test_face.jpg"
    source_lm = source_dets[0].landmarks

    # 2. Initialize Neural Face Swap Engine
    config = FaceSwapEngineConfig(
        inswapper_path=inswapper_path,
        arcface_path=arcface_path,
        provider="CPUExecutionProvider",
        intra_op_num_threads=4,
    )
    engine = FaceSwapEngine(config)
    assert engine.initialize() is True

    # 3. Extract source identity latent vector (512-D)
    latent = engine.compute_source_identity(source_img, source_lm)
    assert latent.shape == (1, 512)
    assert np.isclose(np.linalg.norm(latent), 1.0, atol=1e-3)

    # 4. Read first frame of face video
    video_path = fixtures_dir / "face_video.mp4"
    assert video_path.exists()
    cap = cv2.VideoCapture(str(video_path))
    ret, frame = cap.read()
    cap.release()
    assert ret is True and frame is not None

    target_dets = detector.detect_in_bgr_frame(frame, 0, 0.0)
    assert len(target_dets) >= 1, "Target actor face must be detected in video frame"
    target_lm = target_dets[0].landmarks

    # 5. Execute neural frame swap
    swapped_frame, was_swapped = engine.process_frame(frame, target_lm, latent)
    assert was_swapped is True
    assert swapped_frame.shape == frame.shape

    # 6. Verify genuine neural transformation (not identical, not mock)
    diff = cv2.absdiff(frame, swapped_frame)
    total_diff = float(np.sum(diff))
    max_diff = int(np.max(diff))
    assert total_diff > 1000.0, f"Swapped frame must differ from original (got diff {total_diff})"
    assert max_diff > 10, f"Max pixel change must exceed noise threshold (got max {max_diff})"

    engine.cleanup()


def test_adapter_integration(models_dir, fixtures_dir):
    """Verifies LicensedFaceSwapModelAdapter reports ready and executes swap_face."""
    adapter = get_face_swap_model_adapter()
    assert adapter.is_available is True

    meta = adapter.get_metadata()
    assert meta["status"] == "ready"
    assert "inswapper_128" in meta["name"]
    assert meta["provider"] == "CPUExecutionProvider"

    # Test swap_face
    img1 = cv2.imread(str(fixtures_dir / "test_face.jpg"))
    img2 = cv2.resize(img1, (128, 128))
    out = adapter.swap_face(source_aligned=img2, target_face=img1)
    assert out is not None
    assert out.shape == img2.shape


SCRATCH_DIR = Path("backend/storage/test_scratch")


@pytest.mark.anyio
async def test_real_video_pipeline_end_to_end(fixtures_dir):
    """
    Executes a real end-to-end video processing run with genuine face swap,
    audio handling, watermarking, and container validation.
    """
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    storage = LocalStorageService(base_dir=SCRATCH_DIR)

    # Mock DB service with in-memory collection dictionary
    collections = {}

    class MockCollection:
        def __init__(self, name):
            self.name = name
            self.docs = []

        async def insert_one(self, doc):
            self.docs.append(dict(doc))
            return type("Result", (), {"inserted_id": "1"})()

        async def update_one(self, filt, update):
            for d in self.docs:
                if all(d.get(k) == v for k, v in filt.items()):
                    d.update(update.get("$set", {}))
                    return

        async def find_one(self, filt):
            for d in self.docs:
                if all(d.get(k) == v for k, v in filt.items()):
                    return dict(d)
            return None

    class MockDB:
        is_connected = True

        def get_collection(self, name):
            if name not in collections:
                collections[name] = MockCollection(name)
            return collections[name]

    mock_db = MockDB()

    # Save target face to storage
    face_img = cv2.imread(str(fixtures_dir / "test_face.jpg"))
    _, face_buf = cv2.imencode(".jpg", face_img)
    saved_face = await storage.save_bytes(
        data=face_buf.tobytes(),
        subfolder="faces",
        extension="jpg",
        content_type="image/jpeg",
        original_filename="test_face.jpg",
    )

    face_doc = {
        "upload_id": saved_face.upload_id,
        "storage_path": saved_face.storage_path,
    }

    adapter = get_face_swap_model_adapter()
    assert adapter.is_available is True

    pipeline = VideoProcessingPipeline(
        settings=settings,
        db_service=mock_db,
        storage_service=storage,
        model_adapter=adapter,
    )

    job_id = "test_real_swap_job"
    video_path = fixtures_dir / "face_video.mp4"

    # Pre-populate swap job
    await mock_db.get_collection("swap_jobs").insert_one({
        "job_id": job_id,
        "project_id": "test_proj_1",
        "selected_actor_track_id": "track_1",
        "source_video_id": "test_vid_1",
        "replacement_face_id": saved_face.upload_id,
        "status": "validating",
        "progress": 0.1,
    })

    result = await pipeline.execute_pipeline(
        job_id=job_id,
        video_path=video_path,
        face_doc=face_doc,
        diagnostic_mode=False,
    )

    assert result.status == "completed"
    assert result.progress == 1.0
    assert result.output_video_id is not None

    # Verify output video file on disk
    upload_doc = await mock_db.get_collection("uploads").find_one({"upload_id": result.output_video_id})
    assert upload_doc is not None
    out_path = storage.get_file_path(upload_doc["storage_path"])
    assert out_path.exists()
    assert out_path.stat().st_size > 1000

    # Verify output video is playable
    cap = cv2.VideoCapture(str(out_path))
    assert cap.isOpened()
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    ret, out_frame = cap.read()
    cap.release()

    assert ret is True
    assert frame_count > 0
    assert fps > 0
