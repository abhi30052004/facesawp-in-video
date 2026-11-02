import asyncio
import os
import sys
import time
import json
import logging
from pathlib import Path
import httpx

try:
    import psutil
except ImportError:
    psutil = None

# Add backend directory to path
backend_dir = Path(r"c:\Users\abhijitbhunia\OneDrive - virtualemployee P Ltd\Desktop\FaceSwappingDemo\backend").resolve()
sys.path.insert(0, str(backend_dir))

from app.services.facefusion_engine import get_facefusion_engine

engine = get_facefusion_engine()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bollyswap.e2e_verifier")

BASE_URL = "http://127.0.0.1:8000"
FIXTURES_DIR = backend_dir / "tests" / "fixtures"
VIDEO_PATH = FIXTURES_DIR / "cinematic_authorized_demo.mp4"
FACE_PATH = FIXTURES_DIR / "test_face.jpg"
SCRATCH_DIR = Path(r"C:\Users\abhijitbhunia\.gemini\antigravity\brain\bf7edc0f-177f-4e28-bde4-3e59c019247b\scratch")
RESULTS_OUTPUT_PATH = SCRATCH_DIR / "final_swapped_client_demo.mp4"
REPORT_OUTPUT_PATH = SCRATCH_DIR / "e2e_verification_metrics.json"


async def main():
    metrics = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "base_url": BASE_URL,
        "video_input": str(VIDEO_PATH),
        "face_input": str(FACE_PATH),
        "tests": {},
        "timings": {},
        "system_utilization": {},
    }

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0) as client:
        # 1. Health check
        logger.info("=== STEP 1: Health & Engine Status Check ===")
        t0 = time.time()
        res = await client.get("/health")
        assert res.status_code == 200, f"Health returned {res.status_code}: {res.text}"
        health_data = res.json().get("data", {})
        swap_status = health_data.get("face_swap_status") or health_data.get("faceSwapStatus")
        swap_license = health_data.get("face_swap_license") or health_data.get("faceSwapLicense")
        assert swap_status == "ready", f"Unexpected swap status: {swap_status}"
        assert swap_license == "Apache-2.0", f"Unexpected swap license: {swap_license}"
        logger.info("Root /health OK: status=%s, model=%s", health_data.get("status"), swap_license)

        # Engine status
        res_engine = await client.get("/api/engine/status")
        assert res_engine.status_code == 200, f"Engine status returned {res_engine.status_code}"
        engine_status = res_engine.json().get("data", {})
        assert engine_status.get("engine") in ("FaceFusion", "facefusion")
        assert engine_status.get("version") == "3.9.2"
        assert engine_status.get("ghost_model_cached") is True
        assert "cpu" in engine_status.get("execution_provider", "").lower()
        logger.info("Engine status OK: FaceFusion 3.9.2, Ghost model cached, CPU provider verified.")
        metrics["tests"]["health_and_engine_status"] = "PASSED"
        metrics["engine_info"] = engine_status

        # 2. Inspect Source Video Metadata with FFprobe
        logger.info("=== STEP 2: Source Asset Inspection ===")
        source_meta = engine.inspect_video_metadata(str(VIDEO_PATH))
        assert source_meta.get("width", 0) > 0, "Source video has no valid video track"
        assert source_meta.get("has_audio") is True, "Source video has no audio stream"
        source_duration = source_meta.get("duration", 0.0)
        source_resolution = f"{source_meta.get('width')}x{source_meta.get('height')}"
        logger.info("Source Video: %s | Duration: %.2fs | Audio Codec: %s", source_resolution, source_duration, source_meta.get("audio_codec"))
        metrics["source_video_metadata"] = source_meta

        # 3. Create Project
        logger.info("=== STEP 3: Project Creation ===")
        t_proj = time.time()
        proj_payload = {
            "name": "BollySwap AI Official Client Demo",
            "description": "Authorized Bollywood scene with real FaceFusion 3.9.2 face replacement",
            "consent_confirmed": True,
        }
        res_proj = await client.post("/api/projects", json=proj_payload)
        assert res_proj.status_code in (200, 201), f"Create project failed: {res_proj.text}"
        project_data = res_proj.json().get("data", {})
        project_id = project_data.get("project_id") or project_data.get("projectId")
        assert project_id, f"Missing project_id in {project_data}"
        logger.info("Project created successfully: project_id=%s", project_id)
        metrics["tests"]["project_creation"] = "PASSED"
        metrics["project_id"] = project_id

        # 4. Upload Video
        logger.info("=== STEP 4: Video Upload ===")
        with open(VIDEO_PATH, "rb") as vf:
            video_files = {"file": ("cinematic_authorized_demo.mp4", vf, "video/mp4")}
            res_vupload = await client.post(
                f"/api/projects/{project_id}/upload?file_kind=video",
                files=video_files,
            )
        assert res_vupload.status_code == 200, f"Video upload failed: {res_vupload.text}"
        v_data = res_vupload.json().get("data", {})
        source_video_id = v_data.get("upload_id") or v_data.get("file_id") or v_data.get("fileId")
        assert source_video_id, f"Missing source_video_id in {v_data}"
        logger.info("Video uploaded: file_id=%s", source_video_id)
        metrics["tests"]["video_upload"] = "PASSED"

        # 5. Upload Replacement Face
        logger.info("=== STEP 5: Replacement Face Upload ===")
        with open(FACE_PATH, "rb") as ff:
            face_files = {"file": ("test_face.jpg", ff, "image/jpeg")}
            res_fupload = await client.post(
                f"/api/projects/{project_id}/upload?file_kind=face",
                files=face_files,
            )
        assert res_fupload.status_code == 200, f"Face upload failed: {res_fupload.text}"
        f_data = res_fupload.json().get("data", {})
        replacement_face_id = f_data.get("upload_id") or f_data.get("file_id") or f_data.get("fileId")
        assert replacement_face_id, f"Missing replacement_face_id in {f_data}"
        logger.info("Face uploaded: file_id=%s", replacement_face_id)
        metrics["tests"]["face_upload"] = "PASSED"

        # 6. Dispatch Swap Job via POST /api/projects/{project_id}/process
        logger.info("=== STEP 6: Starting Real FaceFusion Neural Inference ===")
        swap_start_time = time.time()
        res_swap = await client.post(
            f"/api/projects/{project_id}/process",
            json={
                "source_video_id": source_video_id,
                "replacement_face_id": replacement_face_id,
            },
        )
        assert res_swap.status_code == 200, f"Swap initiation failed: {res_swap.text}"
        job_info = res_swap.json().get("data", {})
        job_id = job_info.get("job_id") or job_info.get("jobId")
        assert job_id, "Missing job_id"
        logger.info("Swap job started: job_id=%s, initial_status=%s", job_id, job_info.get("status"))

        # 7. Monitor Inference and Progress
        logger.info("=== STEP 7: Monitoring Inference Progress & CPU/RAM Usage ===")
        poll_interval = 1.0
        max_wait = 180.0
        elapsed = 0.0
        final_job_data = None
        progress_history = []
        cpu_samples = []
        ram_samples = []

        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed = time.time() - swap_start_time

            # Sample system utilization
            if psutil:
                cpu_pct = psutil.cpu_percent(interval=None)
                ram_pct = psutil.virtual_memory().percent
                cpu_samples.append(cpu_pct)
                ram_samples.append(ram_pct)
            else:
                cpu_pct = 0.0
                ram_pct = 0.0

            res_job = await client.get(f"/api/jobs/{job_id}")
            if res_job.status_code != 200:
                logger.warning("Job status check returned %s", res_job.status_code)
                continue

            job_state = res_job.json().get("data", {})
            status = job_state.get("status")
            progress = job_state.get("progress", 0)
            stage = job_state.get("currentStage") or job_state.get("current_stage") or job_state.get("stage") or job_state.get("current_step")
            progress_history.append({"time_sec": round(elapsed, 1), "progress": progress, "stage": stage})

            logger.info(
                "Job %s | Status: %s | Progress: %s | Stage: %s | CPU: %.1f%% | RAM: %.1f%%",
                job_id, status, progress, stage, cpu_pct, ram_pct
            )

            if status in ("completed", "failed", "cancelled"):
                final_job_data = job_state
                break

        assert final_job_data, f"Job timed out after {max_wait}s"
        err_msg = final_job_data.get("errorMessage") or final_job_data.get("error_message") or final_job_data.get("error")
        assert final_job_data.get("status") == "completed", f"Job ended in status '{final_job_data.get('status')}': {err_msg}"
        total_swap_duration = time.time() - swap_start_time
        logger.info("Neural face swap completed successfully in %.2fs!", total_swap_duration)
        metrics["timings"]["neural_swap_duration_sec"] = round(total_swap_duration, 2)
        metrics["system_utilization"] = {
            "avg_cpu_percent": round(sum(cpu_samples) / max(len(cpu_samples), 1), 1),
            "max_cpu_percent": round(max(cpu_samples) if cpu_samples else 0.0, 1),
            "avg_ram_percent": round(sum(ram_samples) / max(len(ram_samples), 1), 1),
            "max_ram_percent": round(max(ram_samples) if ram_samples else 0.0, 1),
        }
        metrics["progress_history"] = progress_history
        metrics["tests"]["real_cpu_inference"] = "PASSED"

        # 8. Download Result Video
        logger.info("=== STEP 8: Inspecting Result API & Downloading Output MP4 Artifact ===")
        res_meta = await client.get(f"/api/jobs/{job_id}/result")
        assert res_meta.status_code == 200, f"Result endpoint failed: {res_meta.status_code}"
        logger.info("Result metadata endpoint OK: isSwapped=%s, model=%s", res_meta.json().get("data", {}).get("isSwapped"), res_meta.json().get("data", {}).get("modelIdentifier"))

        res_download = await client.get(f"/api/jobs/{job_id}/download")
        assert res_download.status_code == 200, f"Download failed: {res_download.status_code}"
        with open(RESULTS_OUTPUT_PATH, "wb") as out_f:
            out_f.write(res_download.content)
        out_file_size = os.path.getsize(RESULTS_OUTPUT_PATH)
        assert out_file_size > 50000, f"Output file too small: {out_file_size} bytes"
        logger.info("Output MP4 saved: %s (Size: %d bytes / %.2f MB)", RESULTS_OUTPUT_PATH, out_file_size, out_file_size / (1024*1024))
        metrics["tests"]["result_download"] = "PASSED"
        metrics["output_file"] = {
            "path": str(RESULTS_OUTPUT_PATH),
            "size_bytes": out_file_size,
            "size_mb": round(out_file_size / (1024 * 1024), 2),
        }

        # 9. Verify Swapped MP4 Metadata with FFprobe (Audio, Codec, Duration)
        logger.info("=== STEP 9: Verifying Swapped Output Media Integrity ===")
        out_meta = engine.inspect_video_metadata(str(RESULTS_OUTPUT_PATH))
        assert out_meta.get("width", 0) > 0, "Output has no valid video track"
        assert out_meta.get("has_audio") is True, "CRITICAL: Output missing original audio track!"
        assert out_meta["video_codec"] in ("h264", "hevc", "mpeg4"), f"Unexpected codec: {out_meta['video_codec']}"
        assert abs(out_meta["duration"] - source_duration) < 1.0, f"Duration mismatch: {out_meta['duration']} vs {source_duration}"
        logger.info("Output Verification PASSED:")
        logger.info(" - Video Codec: %s", out_meta.get("video_codec"))
        logger.info(" - Audio Codec: %s (Audio Preserved!)", out_meta.get("audio_codec"))
        logger.info(" - Resolution: %dx%d", out_meta.get("width"), out_meta.get("height"))
        logger.info(" - Duration: %.2fs (Matches source %.2fs)", out_meta.get("duration"), source_duration)
        metrics["output_metadata"] = out_meta
        metrics["tests"]["audio_preservation"] = "PASSED"
        metrics["tests"]["video_playback_integrity"] = "PASSED"

        # 10. Negative & Resilience Scenarios (Section C)
        logger.info("=== STEP 10: Negative & Resilience Scenarios ===")
        
        # Test 10a: Invalid File Format Upload -> 400
        fake_bad_file = {"file": ("malicious.exe", b"MZNotAValidVideoContent", "application/x-dosexec")}
        res_bad_upload = await client.post(
            f"/api/projects/{project_id}/upload?file_kind=video",
            files=fake_bad_file,
        )
        assert res_bad_upload.status_code == 400, f"Expected 400 for bad extension, got {res_bad_upload.status_code}"
        logger.info("Negative Test 10a (Invalid File Upload 400): PASSED")
        metrics["tests"]["invalid_upload_rejection"] = "PASSED"

        # Test 10b: Non-existent Project / Job -> 404
        res_missing_proj = await client.get("/api/projects/non-existent-proj-id-xyz")
        assert res_missing_proj.status_code == 404, f"Expected 404 for missing project, got {res_missing_proj.status_code}"
        res_missing_job = await client.get("/api/jobs/non-existent-job-id-xyz")
        assert res_missing_job.status_code == 404, f"Expected 404 for missing job, got {res_missing_job.status_code}"
        logger.info("Negative Test 10b (Non-existent Resources 404): PASSED")
        metrics["tests"]["not_found_handling"] = "PASSED"

        # Test 10c: Job Cancellation Endpoint -> DELETE /api/jobs/{id}
        # Create a new project for cancellation test
        res_cancel_proj = await client.post("/api/projects", json={"name": "Cancel Test Project"})
        assert res_cancel_proj.status_code in (200, 201), f"Create cancel test project failed: {res_cancel_proj.text}"
        cancel_proj_id = res_cancel_proj.json().get("data", {}).get("project_id") or res_cancel_proj.json().get("data", {}).get("projectId")
        with open(VIDEO_PATH, "rb") as vf:
            res_cv = await client.post(f"/api/projects/{cancel_proj_id}/upload?file_kind=video", files={"file": ("v.mp4", vf, "video/mp4")})
        with open(FACE_PATH, "rb") as ff:
            res_cf = await client.post(f"/api/projects/{cancel_proj_id}/upload?file_kind=face", files={"file": ("f.jpg", ff, "image/jpeg")})

        cvid = res_cv.json().get("data", {}).get("upload_id")
        cfid = res_cf.json().get("data", {}).get("upload_id")

        # Start swap
        res_cstart = await client.post(
            f"/api/projects/{cancel_proj_id}/process",
            json={"source_video_id": cvid, "replacement_face_id": cfid},
        )
        cjob_id = res_cstart.json().get("data", {}).get("job_id") or res_cstart.json().get("data", {}).get("jobId")
        # Immediately cancel
        await asyncio.sleep(0.5)
        res_del = await client.delete(f"/api/jobs/{cjob_id}")
        assert res_del.status_code == 200, f"Cancel returned {res_del.status_code}"
        res_cstatus = await client.get(f"/api/jobs/{cjob_id}")
        assert res_cstatus.json().get("data", {}).get("status") in ("cancelled", "failed", "completed")
        logger.info("Negative Test 10c (Job Cancellation): PASSED")
        metrics["tests"]["job_cancellation"] = "PASSED"

        # Write final verification report
        with open(REPORT_OUTPUT_PATH, "w") as rf:
            json.dump(metrics, rf, indent=2)
        logger.info("E2E Verification Report saved to: %s", REPORT_OUTPUT_PATH)
        logger.info("=== ALL 10 E2E DEMO VERIFICATION STEPS PASSED SUCCESSFULLY! ===")


if __name__ == "__main__":
    asyncio.run(main())
