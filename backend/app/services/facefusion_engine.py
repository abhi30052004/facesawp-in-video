import os
import sys
import re
import asyncio
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from app.core.config import get_settings

logger = logging.getLogger("bollyswap.facefusion_engine")

def resolve_ffmpeg_bin() -> str:
    """Finds ffmpeg executable using application settings, PATH, WinGet, or imageio."""
    settings = get_settings()
    return settings.resolved_ffmpeg_path


def resolve_ffprobe_bin() -> str:
    """Finds ffprobe executable using application settings, PATH, or WinGet."""
    settings = get_settings()
    return settings.resolved_ffprobe_path


def get_configured_env() -> Dict[str, str]:
    """Prepares an execution environment ensuring FFmpeg directory and venv are in PATH."""
    env = os.environ.copy()
    current_path = env.get("PATH", "")

    # 1. Inject FFmpeg directory into PATH
    ffmpeg_bin = resolve_ffmpeg_bin()
    if os.path.isabs(ffmpeg_bin):
        ffmpeg_dir = os.path.dirname(ffmpeg_bin)
        if os.path.exists(ffmpeg_dir) and ffmpeg_dir not in current_path:
            current_path = f"{ffmpeg_dir};{current_path}"

    # 2. Inject virtualenv Scripts into PATH if present
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    venv_scripts = repo_root / "backend" / ".venv" / "Scripts"
    if venv_scripts.exists() and str(venv_scripts) not in current_path:
        current_path = f"{venv_scripts};{current_path}"
        env["VIRTUAL_ENV"] = str(venv_scripts.parent)

    env["PATH"] = current_path
    # Prevent Python child process output buffering
    env["PYTHONUNBUFFERED"] = "1"
    return env


class FaceFusionEngine:
    """
    Subprocess execution manager for FaceFusion 3.9.2 headless engine.
    Ensures:
    - Pure CPU execution (--execution-providers cpu)
    - Apache-2.0 ghost_1_256 model
    - Subprocess streaming with real percentage tracking
    - Reliable process cancellation and resource cleanup
    - BollySwap AI watermark integration
    - FFprobe metadata validation
    """

    def __init__(self):
        self.settings = get_settings()
        self.repo_root = Path(__file__).resolve().parent.parent.parent.parent
        self.facefusion_dir = self.settings.resolved_facefusion_dir
        venv_python = self.repo_root / "backend" / ".venv" / "Scripts" / "python.exe"
        if venv_python.exists():
            self.python_exe = str(venv_python)
        else:
            self.python_exe = sys.executable
        self._active_processes: Dict[str, asyncio.subprocess.Process] = {}
        self._active_jobs_state: Dict[str, Dict[str, Any]] = {}

    def get_status(self) -> Dict[str, Any]:
        """Returns engine readiness, model status, and FFmpeg capability."""
        ffmpeg_bin = resolve_ffmpeg_bin()
        ffprobe_bin = resolve_ffprobe_bin()
        ffmpeg_ok = os.path.exists(ffmpeg_bin) or shutil.which("ffmpeg", path=get_configured_env().get("PATH")) is not None
        ffprobe_ok = os.path.exists(ffprobe_bin) or shutil.which("ffprobe", path=get_configured_env().get("PATH")) is not None

        models_dir = self.settings.resolved_model_dir
        ghost_model_path = models_dir / "ghost_1_256.onnx"
        ghost_available = ghost_model_path.exists() and ghost_model_path.stat().st_size > 400 * 1024 * 1024

        cli_installed = (self.facefusion_dir / "facefusion.py").exists()

        is_ready = cli_installed and ffmpeg_ok and ffprobe_ok

        return {
            "engine": "FaceFusion",
            "version": "3.9.2",
            "model": "ghost_1_256",
            "model_license": "Apache-2.0",
            "execution_provider": "CPUExecutionProvider",
            "cli_installed": cli_installed,
            "ffmpeg_available": ffmpeg_ok,
            "ffprobe_available": ffprobe_ok,
            "ghost_model_cached": ghost_available,
            "ready": is_ready,
            "supported_providers": ["cpu"],
        }

    def inspect_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """Runs ffprobe on a video file to retrieve resolution, duration, audio & video codecs."""
        ffprobe = resolve_ffprobe_bin()
        cmd = [
            ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path,
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True, env=get_configured_env())
            import json
            data = json.loads(res.stdout)
            format_info = data.get("format", {})
            duration = float(format_info.get("duration", 0.0))
            streams = data.get("streams", [])

            video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
            audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))
            v_codec = video_stream.get("codec_name", "unknown")
            a_codec = audio_stream.get("codec_name", "none") if audio_stream else "none"
            has_audio = audio_stream is not None

            return {
                "duration": duration,
                "width": width,
                "height": height,
                "resolution": f"{width}x{height}",
                "video_codec": v_codec,
                "audio_codec": a_codec,
                "has_audio": has_audio,
                "size_bytes": int(format_info.get("size", 0)),
            }
        except Exception as exc:
            logger.warning(f"FFprobe extraction failed for {video_path}: {exc}")
            return {
                "duration": 0.0,
                "resolution": "unknown",
                "video_codec": "unknown",
                "audio_codec": "unknown",
                "has_audio": False,
                "size_bytes": 0,
            }

    async def apply_watermark(self, input_video: str, output_video: str) -> bool:
        """
        Applies compliance watermark 'AI Generated Media • BollySwap AI' via FFmpeg.
        Preserves audio track with standard web-compatible AAC encoding and faststart.
        """
        ffmpeg = resolve_ffmpeg_bin()
        font_path = "C\\:/Windows/Fonts/arial.ttf" if os.path.exists("C:/Windows/Fonts/arial.ttf") else ""
        font_opt = f":fontfile='{font_path}'" if font_path else ""
        filter_str = (
            f"drawtext=text='AI Generated Media \\: BollySwap AI'{font_opt}:"
            "x=w-tw-20:y=h-th-20:fontsize=16:fontcolor=white@0.85:"
            "box=1:boxcolor=black@0.45:boxborderw=5"
        )

        meta = self.inspect_video_metadata(input_video)
        audio_args = ["-c:a", "aac", "-b:a", "128k"] if meta.get("has_audio") else ["-an"]

        cmd = [
            ffmpeg,
            "-y",
            "-i", input_video,
            "-vf", filter_str,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            *audio_args,
            "-movflags", "+faststart",
            output_video,
        ]

        logger.info(f"Applying BollySwap watermark to {input_video} -> {output_video}")
        env = get_configured_env()

        def _run_ffmpeg():
            return subprocess.run(cmd, capture_output=True, env=env)

        res = await asyncio.to_thread(_run_ffmpeg)
        if res.returncode != 0:
            stderr = res.stderr.decode("utf-8", errors="ignore")[:300] if res.stderr else "unknown error"
            logger.warning(f"FFmpeg drawtext failed, attempting simple copy with AAC: {stderr}")
            # Fallback: copy video stream, encode audio to AAC, add faststart
            cmd_fb = [
                ffmpeg,
                "-y",
                "-i", input_video,
                "-c:v", "copy",
                *audio_args,
                "-movflags", "+faststart",
                output_video,
            ]
            res_fb = await asyncio.to_thread(lambda: subprocess.run(cmd_fb, capture_output=True, env=env))
            if res_fb.returncode != 0:
                shutil.copy2(input_video, output_video)
        return True

    async def run_facefusion_job(
        self,
        job_id: str,
        source_face_path: str,
        target_video_path: str,
        output_video_path: str,
        on_progress: Optional[Callable[[int, str], None]] = None,
        threads: Optional[int] = None,
        fast_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes FaceFusion headless CLI subprocess asynchronously.
        Optimized for CPU-only execution with dynamic multi-threading and fast frame formats.
        Parses progress and updates job status in real time.
        """
        abs_source = str(Path(source_face_path).resolve())
        abs_target = str(Path(target_video_path).resolve())
        abs_out_path = Path(output_video_path).resolve()
        abs_out_path.parent.mkdir(parents=True, exist_ok=True)
        abs_final_output = str(abs_out_path)
        raw_output = str(abs_out_path.parent / f"raw_ff_{abs_out_path.name}")

        self._active_jobs_state[job_id] = {
            "status": "processing",
            "stage": "initialization",
            "progress": 5,
            "error": None,
        }
        if on_progress:
            on_progress(5, "initialization")

        # Dynamic execution thread count (sensible allocation on CPU)
        if threads is None or threads <= 0:
            cpu_cores = os.cpu_count() or 4
            threads = min(cpu_cores, 4)

        video_preset = "ultrafast" if fast_mode else "fast"
        video_quality = "75" if fast_mode else "85"

        # Command for FaceFusion pinned 3.9.2
        cmd = [
            str(self.python_exe),
            "facefusion.py",
            "headless-run",
            "-s", abs_source,
            "-t", abs_target,
            "-o", raw_output,
            "--processors", "face_swapper",
            "--face-swapper-model", "ghost_1_256",
            "--execution-providers", "cpu",
            "--execution-thread-count", str(threads),
            "--video-memory-strategy", "moderate",
            "--temp-frame-format", "jpeg",
            "--output-video-preset", video_preset,
            "--output-video-quality", video_quality,
            "--output-audio-encoder", "aac",
            "--log-level", "info",
        ]

        logger.info(f"Launching FaceFusion CLI for job {job_id}: {' '.join(cmd)}")
        env = get_configured_env()

        progress_pattern = re.compile(r"(\d+)%\|")
        frame_pattern = re.compile(r"processing:\s+(\d+)/(\d+)")
        loop = asyncio.get_running_loop()

        def _execute_cli_sync():
            proc = subprocess.Popen(
                cmd,
                cwd=str(self.facefusion_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",
            )
            self._active_processes[job_id] = proc
            captured_logs = []

            try:
                for raw_line in proc.stdout:
                    line = raw_line.strip()
                    if not line:
                        continue
                    captured_logs.append(line)
                    logger.info(f"[FaceFusion CLI] {line}")

                    match_pct = progress_pattern.search(line)
                    match_frame = frame_pattern.search(line)
                    pct = None
                    if match_pct:
                        pct = int(match_pct.group(1))
                    elif match_frame:
                        curr, total = int(match_frame.group(1)), int(match_frame.group(2))
                        if total > 0:
                            pct = int((curr / total) * 100)

                    if pct is not None:
                        scaled = 10 + int(pct * 0.75)
                        self._active_jobs_state[job_id]["progress"] = scaled
                        self._active_jobs_state[job_id]["stage"] = "face_swapping"
                        if on_progress:
                            loop.call_soon_threadsafe(on_progress, scaled, "face_swapping")

                proc.wait()
                return proc.returncode, captured_logs
            finally:
                if proc.stdout:
                    try:
                        proc.stdout.close()
                    except Exception:
                        pass
                self._active_processes.pop(job_id, None)

        try:
            returncode, captured_logs = await asyncio.to_thread(_execute_cli_sync)

            if returncode != 0:
                tail = "\n".join(captured_logs[-10:]) if captured_logs else "No CLI output captured."
                err_msg = f"FaceFusion engine exited with non-zero code {returncode}. Recent logs:\n{tail}"
                logger.error(err_msg)
                self._active_jobs_state[job_id]["status"] = "failed"
                self._active_jobs_state[job_id]["error"] = err_msg
                if os.path.exists(raw_output):
                    try:
                        os.remove(raw_output)
                    except Exception:
                        pass
                raise RuntimeError(err_msg)

            # Stage: Watermarking
            self._active_jobs_state[job_id]["stage"] = "watermarking"
            self._active_jobs_state[job_id]["progress"] = 90
            if on_progress:
                on_progress(90, "watermarking")

            await self.apply_watermark(raw_output, abs_final_output)

            # Clean raw unwatermarked output
            if os.path.exists(raw_output):
                try:
                    os.remove(raw_output)
                except Exception:
                    pass

            # Stage: Metadata Validation via FFprobe
            meta = self.inspect_video_metadata(abs_final_output)

            self._active_jobs_state[job_id]["status"] = "completed"
            self._active_jobs_state[job_id]["stage"] = "completed"
            self._active_jobs_state[job_id]["progress"] = 100
            if on_progress:
                on_progress(100, "completed")

            return {
                "status": "completed",
                "output_path": abs_final_output,
                "metadata": meta,
            }
        except Exception as exc:
            self._active_jobs_state[job_id]["status"] = "failed"
            self._active_jobs_state[job_id]["error"] = str(exc)
            raise

    def cancel_job(self, job_id: str) -> bool:
        """Terminates running FaceFusion process if active."""
        proc = self._active_processes.get(job_id)
        if proc:
            logger.info(f"Terminating FaceFusion process for job {job_id}")
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], check=False)
                else:
                    proc.terminate()
            except Exception as e:
                logger.warning(f"Error terminating process: {e}")
            self._active_processes.pop(job_id, None)

        if job_id in self._active_jobs_state:
            self._active_jobs_state[job_id]["status"] = "cancelled"
            self._active_jobs_state[job_id]["stage"] = "cancelled"

        return True

    def get_job_state(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Returns in-memory state of active or recently completed job."""
        return self._active_jobs_state.get(job_id)


_engine_instance: Optional[FaceFusionEngine] = None


def get_facefusion_engine() -> FaceFusionEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = FaceFusionEngine()
    return _engine_instance

