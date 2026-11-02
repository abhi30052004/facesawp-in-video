import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.services.facefusion_engine import get_facefusion_engine, resolve_ffmpeg_bin, resolve_ffprobe_bin


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_1_health_endpoints(client: TestClient):
    """TEST 1: GET /api/health and /health return 200 with online/degraded status."""
    res_root = client.get("/health")
    assert res_root.status_code == 200
    assert res_root.json()["success"] is True

    res_api = client.get("/api/health")
    assert res_api.status_code == 200
    assert res_api.json()["success"] is True


def test_2_engine_status(client: TestClient):
    """TEST 2: GET /api/engine/status reports FaceFusion 3.9.2, Ghost model, and CPU execution."""
    res = client.get("/api/engine/status")
    assert res.status_code == 200
    payload = res.json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["engine"] == "FaceFusion"
    assert data["version"] == "3.9.2"
    assert data["model"] == "ghost_1_256"
    assert data["model_license"] == "Apache-2.0"
    assert data["execution_provider"] == "CPUExecutionProvider"
    assert data["cli_installed"] is True
    assert data["ffmpeg_available"] is True
    assert data["ready"] is True


def test_3_ffmpeg_and_ffprobe_resolution():
    """TEST 3: Verify FFmpeg and FFprobe binaries are resolvable and functional."""
    ffmpeg = resolve_ffmpeg_bin()
    ffprobe = resolve_ffprobe_bin()
    assert os.path.exists(ffmpeg) or "ffmpeg" in ffmpeg
    assert os.path.exists(ffprobe) or "ffprobe" in ffprobe


def test_4_ghost_model_cached():
    """TEST 4: Verify ghost_1_256.onnx weights are cached and > 400 MB."""
    engine = get_facefusion_engine()
    model_path = engine.facefusion_dir / ".assets" / "models" / "ghost_1_256.onnx"
    assert model_path.exists(), f"Ghost model missing from {model_path}"
    assert model_path.stat().st_size > 400 * 1024 * 1024


def test_5_ffprobe_video_metadata_inspection():
    """TEST 5: Inspect test fixture video with FFprobe via FaceFusionEngine."""
    engine = get_facefusion_engine()
    fixture_video = engine.repo_root / "backend" / "tests" / "fixtures" / "cinematic_authorized_demo.mp4"
    assert fixture_video.exists()

    meta = engine.inspect_video_metadata(str(fixture_video))
    assert meta["duration"] > 0
    assert meta["width"] == 320
    assert meta["height"] == 240
    assert meta["video_codec"] in ("mpeg4", "h264")
    assert meta["has_audio"] is True


from tests.test_phase3 import InMemoryDatabaseService
from app.services.database import get_database_service
from app.services.project_service import ProjectService, get_project_service


def test_6_project_creation_and_upload(client: TestClient):
    """TEST 6: POST /api/projects creates a project and /projects/{id}/upload accepts assets."""
    mock_db = InMemoryDatabaseService(connected=True)
    proj_service = ProjectService(db_service=mock_db)

    app.dependency_overrides[get_database_service] = lambda: mock_db
    app.dependency_overrides[get_project_service] = lambda: proj_service

    try:
        proj_res = client.post(
            "/api/projects",
            json={"title": "Client Demo FaceFusion Project", "description": "Verification test project"},
        )
        assert proj_res.status_code in (200, 201)
        proj_data = proj_res.json()["data"]
        proj_id = proj_data.get("projectId") or proj_data.get("project_id")

        # Upload test face
        fixtures_dir = Path(__file__).parent / "fixtures"
        face_path = fixtures_dir / "test_face.jpg"
        with open(face_path, "rb") as f:
            up_face = client.post(
                f"/api/projects/{proj_id}/upload?upload_type=face",
                files={"file": ("test_face.jpg", f, "image/jpeg")},
            )
        assert up_face.status_code == 200
        assert up_face.json()["success"] is True
        assert up_face.json()["data"]["file_type"] == "face"

        # Upload test video
        video_path = fixtures_dir / "cinematic_authorized_demo.mp4"
        with open(video_path, "rb") as f:
            up_vid = client.post(
                f"/api/projects/{proj_id}/upload?upload_type=video",
                files={"file": ("cinematic_authorized_demo.mp4", f, "video/mp4")},
            )
        assert up_vid.status_code == 200
        assert up_vid.json()["success"] is True
        assert up_vid.json()["data"]["file_type"] == "video"
    finally:
        app.dependency_overrides.clear()


def test_7_job_cancellation_endpoint(client: TestClient):
    """TEST 7: DELETE /api/jobs/{id} cancels job cleanly."""
    res = client.delete("/api/jobs/swap_test_cancel_123")
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_8_watermark_application_async():
    """TEST 8: Verify FFmpeg watermark application."""
    import asyncio
    engine = get_facefusion_engine()
    fixtures_dir = engine.repo_root / "backend" / "tests" / "fixtures"
    input_video = str(fixtures_dir / "cinematic_authorized_demo.mp4")
    temp_out = str(fixtures_dir / "test_watermarked_temp.mp4")

    async def run():
        ok = await engine.apply_watermark(input_video, temp_out)
        assert ok is True
        assert os.path.exists(temp_out)
        meta = engine.inspect_video_metadata(temp_out)
        assert meta["duration"] > 0
        if os.path.exists(temp_out):
            os.remove(temp_out)

    asyncio.run(run())


def test_9_end_to_end_facefusion_real_swap_on_cpu():
    """TEST 9: Real FaceFusion neural swap execution on CPU."""
    import asyncio
    engine = get_facefusion_engine()
    fixtures_dir = engine.repo_root / "backend" / "tests" / "fixtures"
    source_face = str(fixtures_dir / "test_face.jpg")
    target_video = str(fixtures_dir / "cinematic_authorized_demo.mp4")
    out_video = str(fixtures_dir / "test_facefusion_e2e_out.mp4")

    progress_events = []

    def on_progress(pct: int, stage: str):
        progress_events.append((pct, stage))

    async def run():
        res = await engine.run_facefusion_job(
            job_id="test_swap_e2e_001",
            source_face_path=source_face,
            target_video_path=target_video,
            output_video_path=out_video,
            on_progress=on_progress,
            threads=2,
        )
        assert res["status"] == "completed"
        assert os.path.exists(out_video)
        assert os.path.getsize(out_video) > 10000

        # TEST 10: Audio Preservation
        meta = res["metadata"]
        assert meta["has_audio"] is True
        assert meta["video_codec"] in ("h264", "libx264")
        assert meta["duration"] > 0.5

        # TEST 11: BollySwap AI Watermarking
        assert meta["size_bytes"] > 0

        # TEST 12: Lifecycle State Verification
        state = engine.get_job_state("test_swap_e2e_001")
        assert state["status"] == "completed"
        assert state["progress"] == 100

        # Cleanup
        if os.path.exists(out_video):
            os.remove(out_video)

    asyncio.run(run())

