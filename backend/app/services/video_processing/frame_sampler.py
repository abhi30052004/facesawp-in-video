import logging
from pathlib import Path
from typing import Generator, Optional, Tuple
import cv2
import numpy as np

from app.services.video_processing.video_reader import VideoReader, VideoReaderError

logger = logging.getLogger("bollyswap.services.video_processing.sampler")


class FrameSampler:
    """
    Sequentially streams video frames one at a time using OpenCV VideoCapture.
    Guarantees constant memory consumption by yielding frames as an iterator
    rather than buffering the complete video into RAM.
    """

    def __init__(self, reader: Optional[VideoReader] = None):
        self.reader = reader or VideoReader()

    def stream_frames(
        self,
        video_path: Path,
        max_frames: Optional[int] = None,
        stride: int = 1,
    ) -> Generator[Tuple[int, float, np.ndarray], None, None]:
        """
        Yields (frame_index, timestamp_seconds, frame_bgr) sequentially.
        """
        meta = self.reader.inspect(video_path)
        cap = cv2.VideoCapture(str(video_path))

        try:
            if not cap.isOpened():
                raise VideoReaderError(f"Failed to open video stream: {video_path.name}")

            fps = meta.fps if meta.fps > 0 else 30.0
            frame_idx = 0
            yielded_count = 0
            stride = max(1, stride)

            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                if frame_idx % stride == 0:
                    timestamp = round(frame_idx / fps, 3)
                    yield frame_idx, timestamp, frame
                    yielded_count += 1

                    if max_frames is not None and yielded_count >= max_frames:
                        logger.info("Reached maximum frame limit (%d frames) for %s", max_frames, video_path.name)
                        break

                frame_idx += 1

        finally:
            cap.release()
