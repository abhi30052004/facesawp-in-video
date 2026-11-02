import asyncio
import os
import sys
import time
from pathlib import Path
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE_URL = "http://127.0.0.1:8001/api/v1"

async def run_single_swap_check():
    fixtures_dir = Path(__file__).resolve().parent / "fixtures"
    demo_video = fixtures_dir / "cinematic_authorized_demo.mp4"
    demo_face = fixtures_dir / "test_face.jpg"

    assert demo_video.exists(), f"Demo video missing: {demo_video}"
    assert demo_face.exists(), f"Demo face missing: {demo_face}"

    async with httpx.AsyncClient(base_url="http://127.0.0.1:8001", timeout=120.0) as client:
        print("\n--- 1. Upload Authorized Demo Assets ---")
        # Video upload
        with open(demo_video, "rb") as vf:
            res_v = await client.post(
                "/api/v1/videos/upload",
                files={"file": ("cinematic_authorized_demo.mp4", vf, "video/mp4")},
            )
        assert res_v.status_code == 200, f"Video upload failed: {res_v.text}"
        video_id = res_v.json()["data"]["fileId"]
        print(f"[OK] Uploaded video: {video_id}")

        # Face upload
        with open(demo_face, "rb") as ff:
            res_f = await client.post(
                "/api/v1/faces/upload",
                files={"file": ("test_face.jpg", ff, "image/jpeg")},
            )
        assert res_f.status_code == 200, f"Face upload failed: {res_f.text}"
        face_id = res_f.json()["data"]["faceId"]
        print(f"[OK] Uploaded face: {face_id}")

        print("\n--- 2. Create Project & Start FaceFusion CPU Job ---")
        res_proj = await client.post(
            "/api/v1/projects",
            json={
                "title": "Single Face Swap Verification Project",
                "originalVideoId": video_id,
                "replacementFaceId": face_id,
                "consentConfirmed": True,
            },
        )
        assert res_proj.status_code in (200, 201), f"Project creation failed: {res_proj.text}"
        project_id = res_proj.json()["data"]["projectId"]
        print(f"[OK] Created project: {project_id}")

        start_time = time.time()
        res_swap = await client.post(
            "/api/v1/swaps/create",
            json={
                "projectId": project_id,
                "sourceVideoId": video_id,
                "targetFaceId": face_id,
                "selectedActorTrackId": "track_1",
            },
        )
        assert res_swap.status_code == 200, f"Swap job creation failed: {res_swap.text}"
        job_data = res_swap.json()["data"]
        job_id = job_data["jobId"]
        print(f"[OK] Started FaceFusion swap job: {job_id}")

        print("\n--- 3. Polling Job Status Until Completion ---")
        terminal_statuses = ("completed", "failed", "cancelled")
        poll_interval = 1.0
        final_job = None

        while True:
            await asyncio.sleep(poll_interval)
            elapsed = time.time() - start_time
            res_poll = await client.get(f"/api/v1/swaps/{job_id}")
            if res_poll.status_code != 200:
                print(f"[!] Warning poll status: {res_poll.status_code}")
                continue

            current_job = res_poll.json().get("data", {})
            st = current_job.get("status")
            pct = current_job.get("progress", 0.0)
            step = current_job.get("currentStep", "")
            print(f"[{elapsed:5.1f}s] Status: {st:<12} | Progress: {pct*100:5.1f}% | Stage: {step}")

            if st in terminal_statuses:
                final_job = current_job
                break

            if elapsed > 180:
                raise TimeoutError("Face swap job timed out after 180s")

        total_duration = time.time() - start_time
        print(f"\n--- 4. Verify Final Status ---")
        assert final_job["status"] == "completed", f"Job failed with status: {final_job}"
        print(f"[OK] Final Status: {final_job['status'].upper()} in {total_duration:.2f} seconds")

        print("\n--- 5. Verify Output Video Download Endpoint ---")
        # Check download endpoint: /api/jobs/{job_id}/download or /api/v1/jobs/{job_id}/download
        res_download = await client.get(f"/api/v1/jobs/{job_id}/download")
        if res_download.status_code != 200:
            res_download = await client.get(f"/api/jobs/{job_id}/download")
        assert res_download.status_code == 200, f"Download failed with status {res_download.status_code}: {res_download.text}"
        video_bytes = res_download.content
        assert len(video_bytes) > 1000, f"Output video payload too small: {len(video_bytes)} bytes"

        output_path = Path("backend/storage/videos") / f"verified_single_swap_{job_id}.mp4"
        output_path.write_bytes(video_bytes)
        print(f"[OK] Download endpoint returned valid MP4: {len(video_bytes):,} bytes saved to {output_path}")

        print("\n--- 6. Confirm Output MP4 is Playable with FFprobe ---")
        from app.services.facefusion_engine import get_facefusion_engine
        engine = get_facefusion_engine()
        meta = engine.inspect_video_metadata(str(output_path.resolve()))
        print(f"[OK] Output Video Metadata:")
        print(f"    - Resolution : {meta.get('resolution')}")
        print(f"    - Duration   : {meta.get('duration')}s")
        print(f"    - Video Codec: {meta.get('video_codec')}")
        print(f"    - Audio Codec: {meta.get('audio_codec')} (Audio preserved: {meta.get('has_audio')})")
        print(f"    - Size       : {meta.get('size_bytes'):,} bytes")

        assert meta.get("width", 0) > 0, "Invalid video resolution"
        assert meta.get("duration", 0) > 0.5, "Duration too short"
        assert meta.get("video_codec") in ("h264", "hevc", "av1"), f"Unexpected codec {meta.get('video_codec')}"
        assert meta.get("has_audio") is True, "Audio was not preserved"

        print("\n=======================================================")
        print("REAL FACE SWAP COMPLETION VERIFICATION: 100% SUCCESSFUL")
        print("=======================================================")

if __name__ == "__main__":
    asyncio.run(run_single_swap_check())
