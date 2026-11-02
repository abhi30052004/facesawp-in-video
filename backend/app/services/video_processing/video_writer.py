import logging
from pathlib import Path
from typing import List, Optional, Tuple
import cv2
import numpy as np

logger = logging.getLogger("bollyswap.services.video_processing.writer")


class VideoWriterError(Exception):
    """Raised when writing video container or applying watermarks fails."""
    def __init__(self, message: str, error_code: str = "VIDEO_WRITER_ERROR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class VideoWriter:
    """
    Encodes video frames to temporary MP4 files using OpenCV VideoWriter.
    Enforces ethical AI transparency by applying visible, anti-aliased synthetic media watermarks.
    Validates generated containers and safely handles artifact cleanup.
    """

    def __init__(self, watermark_text: str = "BollySwap AI • Synthetic Media"):
        self.watermark_text = watermark_text
        self._writer: Optional[cv2.VideoWriter] = None
        self._output_path: Optional[Path] = None

    @classmethod
    def apply_watermark(
        cls,
        frame_bgr: np.ndarray,
        text: str = "BollySwap AI • Synthetic Media",
    ) -> np.ndarray:
        """
        Overlays a cinematic, semi-transparent identification pill in the bottom-right corner.
        """
        h, w = frame_bgr.shape[:2]
        if w < 160 or h < 120:
            return frame_bgr

        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = max(0.4, min(0.65, w / 1600.0))
        thickness = 1
        (t_w, t_h), baseline = cv2.getTextSize(text, font, scale, thickness)

        margin = max(10, int(w * 0.02))
        pad_x = 8
        pad_y = 6

        x2 = w - margin
        y2 = h - margin
        x1 = x2 - t_w - (pad_x * 2)
        y1 = y2 - t_h - (pad_y * 2)

        if x1 < 0 or y1 < 0:
            return frame_bgr

        # Alpha blend dark backing pill for legibility across varied backgrounds
        out = frame_bgr.copy()
        sub_region = out[y1:y2, x1:x2]
        dark_rect = np.full(sub_region.shape, (15, 15, 22), dtype=np.uint8)
        blended = cv2.addWeighted(dark_rect, 0.75, sub_region, 0.25, 0)
        out[y1:y2, x1:x2] = blended

        # Subtle border
        cv2.rectangle(out, (x1, y1), (x2, y2), (60, 60, 80), 1, cv2.LINE_AA)

        # Muted gold text (#D6AD65 -> BGR: (101, 173, 214))
        text_origin = (x1 + pad_x, y2 - pad_y - int(baseline / 2))
        cv2.putText(out, text, text_origin, font, scale, (101, 173, 214), thickness, cv2.LINE_AA)

        return out

    def open(
        self,
        output_path: Path,
        fps: float,
        width: int,
        height: int,
        fourcc: str = "mp4v",
    ) -> None:
        """Initializes OpenCV VideoWriter for encoding."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._output_path = output_path
        fourcc_code = cv2.VideoWriter_fourcc(*fourcc)

        self._writer = cv2.VideoWriter(
            str(output_path),
            fourcc_code,
            fps,
            (width, height),
        )

        if not self._writer.isOpened():
            raise VideoWriterError(
                f"Failed to open VideoWriter for destination: {output_path.name}",
                error_code="WRITER_OPEN_FAILED",
            )

    def write_frame(self, frame_bgr: np.ndarray, watermark: bool = True) -> None:
        """Applies watermark and writes a single frame."""
        if self._writer is None:
            raise VideoWriterError("VideoWriter is not open. Call open() first.")

        if watermark:
            frame_to_write = self.apply_watermark(frame_bgr, self.watermark_text)
        else:
            frame_to_write = frame_bgr

        self._writer.write(frame_to_write)

    def close(self) -> None:
        """Releases the VideoWriter resource."""
        if self._writer is not None:
            self._writer.release()
            self._writer = None

    @staticmethod
    def validate_output(video_path: Path) -> bool:
        """Verifies that the generated video file exists and can be decoded."""
        if not video_path.exists() or video_path.stat().st_size == 0:
            return False

        cap = cv2.VideoCapture(str(video_path))
        try:
            if not cap.isOpened():
                return False
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return frames > 0 and w > 0 and h > 0
        finally:
            cap.release()

    @staticmethod
    def cleanup_files(paths: List[Optional[Path]]) -> None:
        """Safely removes temporary files."""
        for p in paths:
            if p is not None and p.exists() and p.is_file():
                try:
                    p.unlink()
                    logger.debug("Cleaned up temporary file: %s", p.name)
                except Exception as e:
                    logger.warning("Failed to remove temporary file %s: %s", p.name, e)

