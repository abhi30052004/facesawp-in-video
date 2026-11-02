import io
import shutil
from pathlib import Path
from unittest.mock import MagicMock
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.services.database import DatabaseService, get_database_service
from app.services.storage_service import LocalStorageService, get_storage_service
from app.services.video_processing.audio_handler import AudioHandler
from app.services.video_processing.model_adapter import (
    get_face_swap_model_adapter,
    reset_face_swap_model_adapter,
)
from app.services.face_detector import get_shared_yunet_detector
from app.services.face_swap.face_swap_engine import FaceSwapEngine, FaceSwapEngineConfig
from app.services.face_swap.model_loader import FaceSwapModelLoader


FIXTURES_DIR = Path(__file__).parent / "fixtures"
SCRATCH_DIR = Path("backend/storage/test_scratch_phase8")


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

    async def update_one(self, query, update, upsert=False, **kwargs):
        for doc in self.docs:
            match = all(doc.get(k) == v for k, v in query.items())
            if match:
                if "$set" in update:
                    doc.update(update["$set"])
                res = MagicMock()
                res.modified_count = 1
                return res
        if upsert:
            new_doc = dict(query)
            if "$setOnInsert" in update:
                new_doc.update(update["$setOnInsert"])
            if "$set" in update:
                new_doc.update(update["$set"])
            new_doc["_id"] = f"mock_{len(self.docs)}"
            self.docs.append(new_doc)
            res = MagicMock()
            res.upserted_id = new_doc["_id"]
            return res
        res = MagicMock()
        res.modified_count = 0
        return res

    async def find_one(self, query, sort=None):
        docs_to_search = list(reversed(self.docs)) if sort else self.docs
        for doc in docs_to_search:
            match = all(doc.get(k) == v for k, v in query.items())
            if match:
                return dict(doc)
        return None

    def find(self, query=None):
        class AsyncCursor:
            def __init__(self, docs):
                self.docs = docs

            def sort(self, *args, **kwargs):
                return self

            def skip(self, *args, **kwargs):
                return self

            def limit(self, *args, **kwargs):
                return self

            def __aiter__(self):
                self._iter = iter(self.docs)
                return self

            async def __anext__(self):
                try:
                    return next(self._iter)
                except StopIteration:
                    raise StopAsyncIteration

        return AsyncCursor(self.docs)


class MockDatabaseService(DatabaseService):
    def __init__(self):
        super().__init__()
        self._connected = True
        self._collections = {}

    @property
    def is_connected(self) -> bool:
        return True

    @property
    def status(self) -> str:
        return "connected"

    def get_collection(self, name: str):
        if name not in self._collections:
            self._collections[name] = InMemoryAsyncCollection()
        return self._collections[name]


@pytest.fixture
def mock_env():
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    db = MockDatabaseService()
    storage = LocalStorageService(base_dir=SCRATCH_DIR)

    from app.services.project_service import ProjectService, get_project_service
    from app.services.detection_service import DetectionService, get_detection_service
    from app.services.video_processing.processing_pipeline import VideoProcessingPipeline, get_video_processing_pipeline

    app = create_app()
    app.dependency_overrides[get_database_service] = lambda: db
    app.dependency_overrides[get_storage_service] = lambda: storage
    app.dependency_overrides[get_project_service] = lambda: ProjectService(db_service=db)
    app.dependency_overrides[get_detection_service] = lambda: DetectionService(
        settings=get_settings(), db_service=db, storage_service=storage
    )
    app.dependency_overrides[get_video_processing_pipeline] = lambda: VideoProcessingPipeline(
        settings=get_settings(), db_service=db, storage_service=storage
    )

    client = TestClient(app)
    yield client, db, storage
    app.dependency_overrides.clear()
    shutil.rmtree(SCRATCH_DIR, ignore_errors=True)


def test_e2e_full_client_workflow(mock_env):
    """
    Executes the entire BollySwap AI client workflow:
    1. Health check & model license confirmation
    2. Video upload (authorized test footage with audio)
    3. Replacement face photo upload (consenting user portrait)
    4. Likeness consent registration
    5. OpenCV YuNet face detection & track hypothesis generation
    6. Actor track selection (confirming HTTP 200 without HTTP 400)
    7. Swap job creation
    8. Real neural inference execution (Inswapper 128 + ArcFace 512-D)
    9. Output container validation (MP4 playable, audio preserved, watermark visible, identity verified)
    """
    client, db, storage = mock_env
    settings = get_settings()

    # -------------------------------------------------------------
    # Step 1: Health Check & Model Verification
    # -------------------------------------------------------------
    health_resp = client.get("/api/v1/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()["data"]
    assert health_data["status"] == "online"
    assert health_data["faceSwapStatus"] == "ready"
    assert health_data["faceSwapLicense"] == "InsightFace-NonCommercial-Research"
    assert health_data["activeModel"] is not None

    # Verify model weights exist on local disk
    assert settings.resolved_face_swap_model_path.exists(), "inswapper_128.onnx must exist"
    assert settings.resolved_arcface_model_path.exists(), "w600k_r50.onnx must exist"
    assert settings.resolved_yunet_model_path.exists(), "YuNet model must exist"

    # -------------------------------------------------------------
    # Step 2: Media Uploads (Video + Replacement Face)
    # -------------------------------------------------------------
    video_source_path = FIXTURES_DIR / "cinematic_authorized_demo.mp4"
    if not video_source_path.exists():
        video_source_path = FIXTURES_DIR / "face_video.mp4"

    face_source_path = FIXTURES_DIR / "test_face.jpg"

    # Upload video
    with open(video_source_path, "rb") as vf:
        video_resp = client.post(
            "/api/v1/videos/upload",
            files={"file": ("cinematic_authorized_demo.mp4", vf, "video/mp4")},
        )
    assert video_resp.status_code == 200
    video_data = video_resp.json()["data"]
    video_id = video_data.get("fileId") or video_data.get("videoId")
    assert video_id.startswith("vid_")

    # Upload replacement face
    with open(face_source_path, "rb") as ff:
        face_resp = client.post(
            "/api/v1/faces/upload",
            files={"file": ("consenting_actor.jpg", ff, "image/jpeg")},
        )
    assert face_resp.status_code == 200
    face_data = face_resp.json()["data"]
    face_id = face_data["faceId"]
    assert face_id.startswith("face_")

    project_id = f"proj_client_demo_{int(cv2.getTickCount())}"

    # -------------------------------------------------------------
    # Step 3: Likeness Consent Registration
    # -------------------------------------------------------------
    consent_resp = client.post(
        "/api/v1/consent",
        json={
            "projectId": project_id,
            "consentGiven": True,
            "consentTextVersion": "v1.0",
            "affirmation": "I affirm that I own the rights or have authorized likeness consent to synthesize this persona.",
        },
    )
    assert consent_resp.status_code == 200
    assert consent_resp.json()["data"]["consentGiven"] is True

    # -------------------------------------------------------------
    # Step 4: Real YuNet Face Detection
    # -------------------------------------------------------------
    detect_resp = client.post(
        "/api/v1/faces/detect",
        json={"projectId": project_id, "videoId": video_id},
    )
    assert detect_resp.status_code == 200
    detect_data = detect_resp.json()["data"]
    assert detect_data["detectionStatus"] == "completed"
    assert len(detect_data["tracks"]) >= 1

    selected_track = detect_data["tracks"][0]["trackId"]
    assert selected_track == "track_1"

    # -------------------------------------------------------------
    # Step 5: Actor Track Selection (Confirm NO HTTP 400!)
    # -------------------------------------------------------------
    select_resp = client.post(
        f"/api/v1/projects/{project_id}/faces/select",
        json={"selectedTrackId": selected_track},
    )
    assert select_resp.status_code == 200, f"Expected 200 OK but got {select_resp.status_code}: {select_resp.text}"
    select_data = select_resp.json()["data"]
    assert select_data["selectedTrackId"] == selected_track

    # -------------------------------------------------------------
    # Step 6: Create Project with explicit ID
    # -------------------------------------------------------------
    create_proj_resp = client.post(
        "/api/v1/projects",
        json={
            "projectId": project_id,
            "title": "BollySwap Client Demo Project",
            "originalVideoId": video_id,
            "replacementFaceId": face_id,
            "consentConfirmed": True,
        },
    )
    assert create_proj_resp.status_code == 201
    proj_doc_data = create_proj_resp.json()["data"]
    assert proj_doc_data["projectId"] == project_id

    # -------------------------------------------------------------
    # Step 7: Create Face Swap Job
    # -------------------------------------------------------------
    create_job_resp = client.post(
        "/api/v1/swaps/create",
        json={
            "projectId": project_id,
            "sourceVideoId": video_id,
            "replacementFaceId": face_id,
            "selectedActorTrackId": selected_track,
        },
    )
    assert create_job_resp.status_code == 200
    swap_job = create_job_resp.json()["data"]
    job_id = swap_job["jobId"]
    assert job_id.startswith("swap_")

    # -------------------------------------------------------------
    # Step 8: Execute Neural Face Swap Pipeline
    # -------------------------------------------------------------
    adapter = get_face_swap_model_adapter()
    assert adapter.is_available is True
    assert adapter.provider == "CPUExecutionProvider"

    # Retrieve physical paths for video and target face
    stored_video_path = storage.get_file_path(f"videos/{video_id}.mp4")
    face_meta = client.get(f"/api/v1/files/{face_id}")
    assert face_meta.status_code == 200

    from app.services.video_processing.processing_pipeline import VideoProcessingPipeline
    pipeline = VideoProcessingPipeline(
        settings=settings,
        db_service=db,
        storage_service=storage,
        model_adapter=adapter,
    )

    uploads_col = db.get_collection("uploads")
    face_upload_doc = {
        "upload_id": face_id,
        "storage_path": f"faces/{face_id}.jpg",
    }

    # Execute real neural pipeline
    import asyncio
    result = asyncio.run(
        pipeline.execute_pipeline(
            job_id=job_id,
            video_path=stored_video_path,
            face_doc=face_upload_doc,
            selected_actor_track_id=selected_track,
            diagnostic_mode=False,
        )
    )

    assert result.status == "completed"
    assert result.output_video_id is not None
    assert result.output_video_url is not None

    # -------------------------------------------------------------
    # Step 9: Verify Output Artifacts (Playability, Audio, Watermark, Identity)
    # -------------------------------------------------------------
    output_mp4_path = storage.get_file_path(f"videos/{result.output_video_id}.mp4")
    assert output_mp4_path.exists(), f"Output MP4 must exist at {output_mp4_path}"
    assert output_mp4_path.stat().st_size > 1000, "Output MP4 size must be valid"

    # 1. Inspect container with OpenCV
    cap = cv2.VideoCapture(str(output_mp4_path))
    assert cap.isOpened(), "Output MP4 container must be readable by OpenCV VideoCapture"
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    assert fps > 0, "FPS must be positive"
    assert frame_count > 0, "Frame count must be greater than zero"
    assert width > 0 and height > 0, "Frame dimensions must be non-zero"

    # Read frames and verify content
    frames_read = 0
    sampled_frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frames_read in (0, frame_count // 2, frame_count - 1):
            sampled_frames.append(frame)
        frames_read += 1
    cap.release()

    assert frames_read == frame_count
    assert len(sampled_frames) >= 2, "Must sample at least 2 frames"

    # Persist artifacts to main storage for client demo inspection
    demo_export_dir = Path("backend/storage/videos")
    demo_export_dir.mkdir(parents=True, exist_ok=True)
    demo_mp4_export = demo_export_dir / "client_demo_swapped.mp4"
    shutil.copy2(output_mp4_path, demo_mp4_export)

    # Save visual verification audit frames
    cv2.imwrite("backend/storage/demo_audit_swapped.jpg", sampled_frames[0])
    cap_orig = cv2.VideoCapture(str(video_source_path))
    ret_orig, frame_orig = cap_orig.read()
    cap_orig.release()
    if ret_orig:
        cv2.imwrite("backend/storage/demo_audit_orig.jpg", frame_orig)

    # 2. Verify AI Watermark
    # Check bottom region where watermark text 'BollySwap AI • Synthetic Media' is drawn
    sample_frame = sampled_frames[0]
    h, w = sample_frame.shape[:2]
    # Watermark is positioned bottom-right with margin 30
    watermark_roi = sample_frame[h - 60 : h - 10, w - 400 : w - 20]
    assert watermark_roi.size > 0
    # Confirm variance/non-uniformity indicating text glyphs overlaid
    std_dev = np.std(watermark_roi)
    assert std_dev > 1.0, "Watermark region must contain rendered text pixels"

    # 3. Verify Audio Preservation
    audio_handler = AudioHandler(ffmpeg_path=settings.resolved_ffmpeg_path)
    has_audio = audio_handler.has_audio(output_mp4_path)
    # If the original video had audio, output must have audio preserved
    orig_has_audio = audio_handler.has_audio(stored_video_path)
    assert has_audio == orig_has_audio, "Audio presence in output must match input footage"
    assert has_audio is True, "Output must have preserved active audio stream"

    # 4. Neural Face Swap Verification via ArcFace Cosine Similarity
    target_face_bgr = cv2.imread(str(face_source_path))
    assert target_face_bgr is not None
    engine = adapter.engine
    assert engine is not None and engine.is_ready

    # Detect face in consenting target photo
    detector = get_shared_yunet_detector()
    target_dets = detector.detect_in_bgr_frame(target_face_bgr, frame_index=0, timestamp_seconds=0.0)
    assert len(target_dets) >= 1, "Must detect face in target face photo"
    target_landmarks = target_dets[0].landmarks

    # Detect face in the swapped output frame
    out_detections = detector.detect_in_bgr_frame(sample_frame, frame_index=0, timestamp_seconds=0.0)
    assert len(out_detections) >= 1, "YuNet must detect the swapped face in the rendered MP4"

    swapped_det = out_detections[0]
    assert swapped_det.confidence >= 0.60
    assert len(swapped_det.landmarks) == 5

    # Align both faces to 112x112 canonical ArcFace template
    aligned_swapped = engine.preprocessor.align_source_face_112(sample_frame, swapped_det.landmarks)
    aligned_target = engine.preprocessor.align_source_face_112(target_face_bgr, target_landmarks)

    arc_blob_swapped = engine.preprocessor.prepare_arcface_input(aligned_swapped)
    arc_blob_target = engine.preprocessor.prepare_arcface_input(aligned_target)

    rec_session = engine.loader.get_bundle().recognition_session
    rec_inp_name = engine.loader.get_bundle().rec_inputs[0]["name"]
    rec_out_name = engine.loader.get_bundle().rec_outputs[0]["name"]

    emb_swapped = rec_session.run([rec_out_name], {rec_inp_name: arc_blob_swapped})[0].flatten()
    emb_target = rec_session.run([rec_out_name], {rec_inp_name: arc_blob_target})[0].flatten()

    emb_swapped /= (np.linalg.norm(emb_swapped) + 1e-6)
    emb_target /= (np.linalg.norm(emb_target) + 1e-6)

    cosine_sim = float(np.dot(emb_swapped, emb_target))
    print(f"\n[PHASE 8 AUDIT] ArcFace Cosine Similarity between swapped face and target identity: {cosine_sim:.4f}")
    assert cosine_sim > 0.40, (
        f"Face swap identity verification failed: Cosine similarity {cosine_sim:.4f} is too low. "
        "Genuine face replacement must match consenting target persona."
    )
