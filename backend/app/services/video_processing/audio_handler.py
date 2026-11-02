import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger("bollyswap.services.video_processing.audio")


class AudioProcessingError(Exception):
    """Raised when audio extraction or remuxing fails."""
    def __init__(self, message: str, error_code: str = "AUDIO_PROCESSING_ERROR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class AudioHandler:
    """
    Extracts and remuxes original audio tracks using FFmpeg.
    Preserves audio synchronization and stream codecs without re-encoding where possible.
    Safely handles audio-less clips and corrupted containers.
    """

    def __init__(self, ffmpeg_path: Optional[str] = None):
        if ffmpeg_path:
            self.ffmpeg_path = ffmpeg_path
        else:
            settings = get_settings()
            self.ffmpeg_path = settings.resolved_ffmpeg_path

    def has_audio(self, video_path: Path) -> bool:
        """Probes the video container to detect presence of an audio stream."""
        if not video_path.exists() or not video_path.is_file():
            return False

        cmd = [self.ffmpeg_path, "-i", str(video_path)]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
            # FFmpeg reports streams to stderr
            output = res.stderr or ""
            return "Audio:" in output
        except Exception as e:
            logger.warning("Failed to probe audio streams for %s: %s", video_path.name, e)
            return False

    def extract_audio(self, video_path: Path, output_audio_path: Path) -> bool:
        """
        Extracts original audio stream into a standalone file without re-encoding.
        Returns True if audio was extracted, False if no audio stream exists.
        """
        if not self.has_audio(video_path):
            logger.info("Video %s contains no audio streams. Skipping audio extraction.", video_path.name)
            return False

        output_audio_path.parent.mkdir(parents=True, exist_ok=True)

        # Attempt 1: Direct stream copy (lossless, zero re-encoding)
        cmd_copy = [
            self.ffmpeg_path,
            "-y",
            "-i", str(video_path),
            "-vn",
            "-c:a", "copy",
            str(output_audio_path),
        ]

        try:
            res = subprocess.run(cmd_copy, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
            if res.returncode == 0 and output_audio_path.exists() and output_audio_path.stat().st_size > 0:
                logger.info("Extracted original audio (lossless stream copy) from %s", video_path.name)
                return True
        except Exception as e:
            logger.warning("Stream copy failed, attempting AAC fallback: %s", e)

        # Attempt 2: AAC fallback if stream copy failed
        cmd_aac = [
            self.ffmpeg_path,
            "-y",
            "-i", str(video_path),
            "-vn",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_audio_path),
        ]

        try:
            res = subprocess.run(cmd_aac, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
            if res.returncode == 0 and output_audio_path.exists() and output_audio_path.stat().st_size > 0:
                logger.info("Extracted audio (AAC fallback) from %s", video_path.name)
                return True
            raise AudioProcessingError(f"FFmpeg audio extraction failed: {res.stderr}")
        except Exception as e:
            logger.exception("Failed to extract audio from %s", video_path.name)
            raise AudioProcessingError(f"Audio extraction error: {str(e)}")

    def combine_audio_video(
        self,
        video_path: Path,
        audio_path: Optional[Path],
        output_path: Path,
    ) -> bool:
        """
        Remuxes audio stream with processed video container.
        Preserves video stream and synchronization with '-shortest'.
        """
        if not video_path.exists():
            raise AudioProcessingError(f"Processed video not found: {video_path.name}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # If no audio file is provided or audio does not exist, copy video directly
        if audio_path is None or not audio_path.exists() or audio_path.stat().st_size == 0:
            logger.info("No audio track provided; output will be video-only: %s", output_path.name)
            cmd_silent = [
                self.ffmpeg_path,
                "-y",
                "-i", str(video_path),
                "-c:v", "copy",
                "-an",
                str(output_path),
            ]
            subprocess.run(cmd_silent, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=30)
            return True

        # Remux video and audio streams
        cmd_remux = [
            self.ffmpeg_path,
            "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "copy",
            "-shortest",
            str(output_path),
        ]

        try:
            res = subprocess.run(cmd_remux, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=45)
            if res.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
                logger.info("Remuxed video and audio into %s", output_path.name)
                return True
        except Exception as e:
            logger.warning("Stream copy remux failed, attempting aac audio fallback: %s", e)

        # Fallback with AAC re-encoding
        cmd_remux_fallback = [
            self.ffmpeg_path,
            "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(output_path),
        ]

        res = subprocess.run(cmd_remux_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=45)
        if res.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
            logger.info("Remuxed video and audio (fallback) into %s", output_path.name)
            return True

        raise AudioProcessingError(f"Failed to remux audio and video: {res.stderr}")

