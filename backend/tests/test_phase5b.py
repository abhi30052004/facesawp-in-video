import asyncio
from pathlib import Path
import cv2
import numpy as np
import pytest
import onnx
from onnx import helper, TensorProto

from app.core.config import Settings, get_settings
from app.services.database import DatabaseService
from app.services.storage_service import LocalStorageService
from app.services.face_tracker import calculate_iou
from app.services.video_processing.audio_handler import AudioHandler
from app.services.video_processing.face_alignment import FaceAligner
from app.services.video_processing.frame_processor import (
    FrameProcessor,
    TemporalFaceTracker,
    blend_face_composite,
    match_color_stats,
)
from app.services.video_processing.model_adapter import (
    LicensedFaceSwapModelAdapter,
    ModelNotConfiguredError,
    UnconfiguredFaceSwapModelAdapter,
    get_face_swap_model_adapter,
)
from app.services.video_processing.processing_pipeline import VideoProcessingPipeline
from app.services.video_processing.video_reader import VideoReader
from app.services.video_processing.video_writer import VideoWriter

SCRATCH_DIR = Path("backend/storage/test_scratch")


@pytest.fixture(autouse=True)
def ensure_scratch_dir():
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    yield
    # Cleanup scratch files
    for item in SCRATCH_DIR.glob("*"):
        if item.is_file():
            try:
                item.unlink(missing_ok=True)
            except Exception:
                pass


def create_minimal_onnx_model(output_path: Path) -> Path:
    """Builds a verified, lightweight valid ONNX face-swap model for CPU inference testing."""
    input_target = helper.make_tensor_value_info("target", TensorProto.FLOAT, [1, 3, 128, 128])
    input_source = helper.make_tensor_value_info("source", TensorProto.FLOAT, [1, 3, 128, 128])
    output = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 3, 128, 128])

    # Simple blend graph: output = (target + source) * 0.5
    add_node = helper.make_node("Add", ["target", "source"], ["sum_out"])
    const_half = helper.make_tensor("half_val", TensorProto.FLOAT, [1], [0.5])
    mul_node = helper.make_node("Mul", ["sum_out", "half_val"], ["output"])

    graph = helper.make_graph(
        [add_node, mul_node],
        "test_swap_graph",
        [input_target, input_source],
        [output],
        [const_half],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 14)], ir_version=10)
    onnx.checker.check_model(model)
    onnx.save(model, str(output_path))
    return output_path


def create_synthetic_mp4_video(file_path: Path, frame_count: int = 15, width: int = 640, height: int = 480) -> Path:
    """Generates an MP4 video clip for deterministic test execution."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(file_path), fourcc, 30.0, (width, height))
    for i in range(frame_count):
        # Create a background frame with gradient
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :] = (i * 10 % 255, 80, 140)
        # Add an identifiable rectangle
        cv2.rectangle(frame, (100, 100), (250, 250), (200, 200, 200), -1)
        writer.write(frame)
    writer.release()
    return file_path


class MockMongoDBCollection:
    """In-memory mock for MongoDB collections used during isolated unit tests."""
    def __init__(self):
        self._docs = {}

    async def insert_one(self, doc):
        doc_copy = doc.copy()
        key = doc.get("project_id") or doc.get("job_id") or doc.get("upload_id") or doc.get("consent_id")
        self._docs[key] = doc_copy
        return doc_copy

    async def find_one(self, query):
        for doc in self._docs.values():
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                return doc.copy()
        return None

    async def update_one(self, query, update):
        doc = await self.find_one(query)
        if doc and "$set" in update:
            doc.update(update["$set"])
            key = doc.get("project_id") or doc.get("job_id") or doc.get("upload_id") or doc.get("consent_id")
            self._docs[key] = doc
        return doc


class MockDatabaseService(DatabaseService):
    """Mock database returning in-memory collections."""
    def __init__(self):
        super().__init__()
        self._is_connected = True
        self._collections = {
            "projects": MockMongoDBCollection(),
            "consent_records": MockMongoDBCollection(),
            "uploads": MockMongoDBCollection(),
            "swap_jobs": MockMongoDBCollection(),
            "processing_jobs": MockMongoDBCollection(),
            "detection_jobs": MockMongoDBCollection(),
        }

    @property
    def is_connected(self) -> bool:
        return True

    def get_collection(self, name: str):
        if name not in self._collections:
            self._collections[name] = MockMongoDBCollection()
        return self._collections[name]


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_settings_configuration():
    """Verifies that Phase 5B settings are defined and resolve correctly."""
    settings = Settings(
        FACE_SWAP_ENABLED=True,
        FACE_SWAP_MODEL_PATH="models/test_model.onnx",
        FACE_SWAP_MODEL_LICENSE="Apache-2.0",
        FACE_SWAP_PROVIDER="CPUExecutionProvider",
        FACE_SWAP_INPUT_SIZE=128,
    )
    assert settings.FACE_SWAP_ENABLED is True
    assert settings.FACE_SWAP_PROVIDER == "CPUExecutionProvider"
    assert settings.FACE_SWAP_INPUT_SIZE == 128
    assert settings.resolved_face_swap_model_path.name == "test_model.onnx"


def test_unconfigured_model_adapter():
    """Ensures UnconfiguredFaceSwapModelAdapter reports honest status and refuses mock inference."""
    adapter = UnconfiguredFaceSwapModelAdapter(reason="License unconfigured in demo environment.")
    assert adapter.is_available is False
    assert adapter.initialize() is False

    meta = adapter.get_metadata()
    assert meta["status"] == "model_not_configured"
    assert meta["name"] == "unconfigured"

    # Calling swap_face must raise ModelNotConfiguredError
    dummy_source = np.zeros((256, 256, 3), dtype=np.uint8)
    dummy_target = np.zeros((256, 256, 3), dtype=np.uint8)
    with pytest.raises(ModelNotConfiguredError) as exc_info:
        adapter.swap_face(dummy_source, dummy_target)
    assert "unconfigured" in str(exc_info.value).lower()


def test_licensed_model_adapter_lifecycle():
    """Verifies complete lifecycle of LicensedFaceSwapModelAdapter using real ONNX Runtime CPU execution."""
    onnx_file = SCRATCH_DIR / "test_swap_model.onnx"
    create_minimal_onnx_model(onnx_file)

    adapter = LicensedFaceSwapModelAdapter(
        model_path=onnx_file,
        license_name="MIT-Permissive",
        provider="CPUExecutionProvider",
        input_size=128,
    )

    # 1. Initialize
    initialized = adapter.initialize()
    assert initialized is True
    assert adapter.is_available is True

    # 2. Metadata inspection
    meta = adapter.get_metadata()
    assert meta["status"] == "ready"
    assert meta["provider"] == "CPUExecutionProvider"
    assert "target" in meta["input_nodes"]
    assert "source" in meta["input_nodes"]
    assert "output" in meta["output_nodes"]

    # 3. Input Validation
    valid_source = np.full((256, 256, 3), 120, dtype=np.uint8)
    valid_target = np.full((256, 256, 3), 200, dtype=np.uint8)
    assert adapter.validate_inputs(valid_source, valid_target) is True
    assert adapter.validate_inputs(None, valid_target) is False
    assert adapter.validate_inputs(np.zeros((10, 10, 3)), valid_target) is False  # too small

    # 4. Neural Inference
    swapped = adapter.swap_face(valid_source, valid_target)
    assert isinstance(swapped, np.ndarray)
    assert swapped.shape == (256, 256, 3)
    assert swapped.dtype == np.uint8
    # Blended value should be between source (120) and target (200)
    assert 130 <= int(swapped[128, 128, 0]) <= 190

    # 5. Cleanup
    adapter.cleanup()
    assert adapter.is_available is False


def test_reinhard_color_transfer():
    """Verifies that Reinhard LAB color transfer harmonizes lighting and skin tone."""
    # Source image: cool blue-tinted face
    source_bgr = np.zeros((100, 100, 3), dtype=np.uint8)
    source_bgr[:, :] = (200, 50, 50)  # BGR: high blue, low red

    # Target video face: warm orange/gold scene
    target_bgr = np.zeros((100, 100, 3), dtype=np.uint8)
    target_bgr[:, :] = (50, 150, 220)  # BGR: high red, moderate green, low blue

    matched = match_color_stats(source_bgr, target_bgr)
    assert matched.shape == (100, 100, 3)
    assert matched.dtype == np.uint8

    # In matched image, the red channel (index 2) should be higher than source red
    assert matched[:, :, 2].mean() > source_bgr[:, :, 2].mean()
    # In matched image, the blue channel (index 0) should be lower than source blue
    assert matched[:, :, 0].mean() < source_bgr[:, :, 0].mean()


def test_feathered_mask_generation():
    """Verifies that FaceAligner generates smooth continuous feathered masks."""
    mask = FaceAligner.create_feathered_mask(crop_size=256, blur_kernel_size=25, blur_sigma=9.0)
    assert mask.shape == (256, 256)
    assert mask.dtype == np.uint8

    # Center of face ellipse should be full white (255)
    assert mask[130, 128] == 255

    # Outer corners should be zero (0)
    assert mask[0, 0] == 0
    assert mask[0, 255] == 0
    assert mask[255, 0] == 0
    assert mask[255, 255] == 0

    # Gradient border region should have intermediate values (smooth transition, not binary)
    intermediate_vals = mask[(mask > 10) & (mask < 240)]
    assert len(intermediate_vals) > 500


def test_temporal_face_tracker():
    """Verifies that TemporalFaceTracker smooths jitter and interpolates brief 1-2 frame occlusions."""
    tracker = TemporalFaceTracker(smoothing_factor=0.70, max_missed_frames=2)

    # Frame 1: Initial detection
    bbox1 = (100, 100, 80, 80)
    lm1 = [[110.0, 120.0], [150.0, 120.0], [130.0, 140.0], [115.0, 160.0], [145.0, 160.0]]
    _, tracked_lm1 = tracker.update(bbox1, lm1)
    assert tracked_lm1 == lm1

    # Frame 2: Slightly shifted detection (micro-jitter)
    bbox2 = (102, 101, 80, 80)
    lm2 = [[112.0, 122.0], [152.0, 122.0], [132.0, 142.0], [117.0, 162.0], [147.0, 162.0]]
    _, tracked_lm2 = tracker.update(bbox2, lm2)
    # Due to smoothing factor 0.70, smoothed x = 0.70 * 112 + 0.30 * 110 = 111.4
    assert tracked_lm2[0][0] == 111.4

    # Frame 3: Missing detection (occlusion frame 1)
    _, tracked_lm3 = tracker.update(None, None)
    assert tracked_lm3 is not None
    assert tracked_lm3 == tracked_lm2

    # Frame 4: Missing detection (occlusion frame 2)
    _, tracked_lm4 = tracker.update(None, None)
    assert tracked_lm4 is not None

    # Frame 5: Missing detection (exceeded max_missed_frames)
    _, tracked_lm5 = tracker.update(None, None)
    assert tracked_lm5 is None


def test_frame_processor_end_to_end():
    """Verifies that FrameProcessor executes alignment, inference, color matching, and feathered blending."""
    onnx_file = SCRATCH_DIR / "test_swap_model.onnx"
    create_minimal_onnx_model(onnx_file)

    adapter = LicensedFaceSwapModelAdapter(
        model_path=onnx_file,
        provider="CPUExecutionProvider",
        input_size=128,
    )
    adapter.initialize()

    processor = FrameProcessor(
        model_adapter=adapter,
        face_aligner=FaceAligner(target_crop_size=256),
        color_matching=True,
        feather_edges=True,
    )

    frame = np.full((480, 640, 3), 80, dtype=np.uint8)
    target_face = np.full((256, 256, 3), 180, dtype=np.uint8)
    landmarks = [[200.0, 200.0], [300.0, 200.0], [250.0, 260.0], [220.0, 310.0], [280.0, 310.0]]
    bbox = (180, 170, 140, 160)

    out_frame, was_swapped = processor.process_frame(
        frame_bgr=frame,
        target_face_bgr=target_face,
        landmarks=landmarks,
        bounding_box=bbox,
    )

    assert was_swapped is True
    assert out_frame.shape == (480, 640, 3)
    # The swapped region should have modified pixel values
    assert not np.array_equal(out_frame, frame)


def test_pipeline_honest_unconfigured_transition():
    """Ensures that the VideoProcessingPipeline records an honest 'model_not_configured' status."""
    settings = get_settings()
    db = MockDatabaseService()
    storage = LocalStorageService(base_dir=SCRATCH_DIR)

    # Register project
    asyncio.run(
        db.get_collection("projects").insert_one({
            "project_id": "proj_p5b_honest",
            "detected_tracks": [{"track_id": "track_1", "boundingBox": [100, 100, 50, 50]}],
        })
    )
    # Affirm consent
    asyncio.run(
        db.get_collection("consent_records").insert_one({
            "project_id": "proj_p5b_honest",
            "consent_given": True,
        })
    )
    # Register dummy video upload
    v_path = SCRATCH_DIR / "source_video.mp4"
    create_synthetic_mp4_video(v_path, frame_count=10)
    asyncio.run(
        db.get_collection("uploads").insert_one({
            "upload_id": "vid_honest_1",
            "storage_path": str(v_path.relative_to(SCRATCH_DIR)),
        })
    )

    unconfigured_adapter = UnconfiguredFaceSwapModelAdapter()
    pipeline = VideoProcessingPipeline(
        settings=settings,
        db_service=db,
        storage_service=storage,
        model_adapter=unconfigured_adapter,
    )

    job = asyncio.run(
        pipeline.create_and_evaluate_job(
            project_id="proj_p5b_honest",
            source_video_id="vid_honest_1",
            replacement_face_id="face_honest_1",
            selected_actor_track_id="track_1",
        )
    )

    assert job.status == "model_not_configured"
    assert "unconfigured" in job.current_step.lower()


def test_pipeline_execution_with_licensed_model():
    """Verifies complete end-to-end video processing execution with real ONNX model inference and watermark."""
    settings = get_settings()
    db = MockDatabaseService()
    storage = LocalStorageService(base_dir=SCRATCH_DIR)

    # 1. Setup minimal ONNX model
    onnx_file = SCRATCH_DIR / "pipeline_swap.onnx"
    create_minimal_onnx_model(onnx_file)

    adapter = LicensedFaceSwapModelAdapter(
        model_path=onnx_file,
        provider="CPUExecutionProvider",
        input_size=128,
    )
    adapter.initialize()

    # 2. Setup video and face assets
    video_path = SCRATCH_DIR / "sample_scene.mp4"
    create_synthetic_mp4_video(video_path, frame_count=15, width=640, height=480)

    face_path = SCRATCH_DIR / "replacement_face.jpg"
    target_face_img = np.full((256, 256, 3), 160, dtype=np.uint8)
    cv2.imwrite(str(face_path), target_face_img)

    face_doc = {
        "upload_id": "face_upload_p5b",
        "storage_path": str(face_path.relative_to(SCRATCH_DIR)),
    }

    pipeline = VideoProcessingPipeline(
        settings=settings,
        db_service=db,
        storage_service=storage,
        model_adapter=adapter,
    )

    job_id = "swap_p5b_test_run"
    asyncio.run(
        db.get_collection("swap_jobs").insert_one({
            "job_id": job_id,
            "project_id": "proj_p5b",
            "selected_actor_track_id": "track_1",
            "source_video_id": "vid_sample_source",
            "replacement_face_id": "face_sample_target",
            "status": "queued",
            "progress": 0.0,
            "current_step": "Queued",
            "created_at": "2026-11-02T05:00:00Z",
        })
    )

    # Execute pipeline
    result_job = asyncio.run(
        pipeline.execute_pipeline(
            job_id=job_id,
            video_path=video_path,
            face_doc=face_doc,
            selected_actor_track_id="track_1",
            diagnostic_mode=False,
        )
    )

    assert result_job.status == "completed"
    assert result_job.progress == 1.0
    assert result_job.output_video_id is not None
    assert result_job.output_video_url is not None

    # Verify output video file on disk
    upload_doc = asyncio.run(db.get_collection("uploads").find_one({"upload_id": result_job.output_video_id}))
    assert upload_doc is not None
    output_path = storage.get_file_path(upload_doc["storage_path"])
    assert output_path.exists()
    assert output_path.stat().st_size > 1000

    # Verify container can be read by VideoReader
    reader = VideoReader()
    meta = reader.inspect(output_path)
    assert meta.frame_count >= 15
    assert meta.width == 640
    assert meta.height == 480
