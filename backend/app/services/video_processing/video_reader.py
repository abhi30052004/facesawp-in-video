import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import cv2
import numpy as np

logger = logging.getLogger("bollyswap.services.video_processing.reader")


class VideoReaderError(Exception):
    """Raised when video file is unreadable, corrupted, or unsupported."""
    def __init__(self, message: str, error_code: str = "INVALID_VIDEO"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


@dataclass
class VideoStreamMetadata:
    """Detailed structural metadata for a decoded video stream."""
    width: int
    height: int
    fps: float
    duration_seconds: float
    frame_count: int
    codec: str


class VideoReader:
    """
    Validates and inspects video stream headers and decodability.
    Enforces real container validation; never trusts file extensions alone.
    """

    @staticmethod
    def validate_media_signature(video_path: Path) -> bool:
        """Inspects binary container magic bytes to reject disguised scripts or corrupted files."""
        if not video_path.exists() or not video_path.is_file():
            return False

        size = video_path.stat().st_size
        if size < 16:
            return False

        with open(video_path, "rb") as f:
            header = f.read(64)

        # Standard MP4/MOV ftyp or atom box signatures
        if len(header) >= 8:
            box_type = header[4:8]
            if box_type in (b"ftyp", b"moov", b"mdat", b"wide", b"skip"):
                return True
            if b"ftyp" in header[:32]:
                return True

        # WebM signature
        if header.startswith(b"\x1aE\xdf\xa3"):
            return True

        return False

    def inspect(self, video_path: Path) -> VideoStreamMetadata:
        """
        Opens and inspects the video container using OpenCV VideoCapture.
        Guarantees resource release upon completion or error.
        """
        if not video_path.exists() or not video_path.is_file():
            raise VideoReaderError(f"Video file does not exist: {video_path.name}", error_code="FILE_NOT_FOUND")

        if not self.validate_media_signature(video_path):
            raise VideoReaderError(
                f"File '{video_path.name}' failed binary container validation. Not a valid MP4/MOV video.",
                error_code="INVALID_SIGNATURE",
            )

        cap = cv2.VideoCapture(str(video_path))
        try:
            if not cap.isOpened():
                raise VideoReaderError(
                    f"OpenCV failed to open video container for '{video_path.name}'.",
                    error_code="CONTAINER_OPEN_FAILED",
                )

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = float(cap.get(cv2.CAP_PROP_FPS))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            if width <= 0 or height <= 0 or frame_count <= 0:
                raise VideoReaderError(
                    f"Invalid stream dimensions ({width}x{height}) or zero frames ({frame_count}) in '{video_path.name}'.",
                    error_code="INVALID_DIMENSIONS",
                )

            if fps <= 0.0 or np.isnan(fps):
                fps = 30.0

            duration = round(frame_count / fps, 3)

            # FourCC codec representation
            fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
            codec = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)]).strip() or "mp4v"

            return VideoStreamMetadata(
                width=width,
                height=height,
                fps=round(fps, 2),
                duration_seconds=duration,
                frame_count=frame_count,
                codec=codec,
            )

        finally:
            cap.release()
