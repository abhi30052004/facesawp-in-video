import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, List, Optional, Tuple
import cv2
import numpy as np

logger = logging.getLogger("bollyswap.services.video")


class VideoProcessingError(Exception):
    """Raised when a video file is unreadable, corrupted, or unsupported."""
    def __init__(self, message: str, error_code: str = "VIDEO_PROCESSING_ERROR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


@dataclass
class VideoMetadata:
    """Metadata extracted from the video stream."""
    width: int
    height: int
    fps: float
    duration_seconds: float
    frame_count: int


@dataclass
class SampledFrame:
    """A sampled video frame with exact timestamp and scaling metadata."""
    frame_index: int
    timestamp_seconds: float
    image: np.ndarray
    original_width: int
    original_height: int
    scale_factor: float


class VideoService:
    """
    Handles robust video frame extraction and container inspection using OpenCV.
    Protects CPU and memory by enforcing sampling intervals, max frame counts,
    and aspect-ratio preserving frame resizing.
    """

    def __init__(
        self,
        sample_interval_seconds: float = 1.5,
        max_sampled_frames: int = 30,
        max_frame_dimension: int = 1280,
    ):
        self.sample_interval_seconds = sample_interval_seconds
        self.max_sampled_frames = max_sampled_frames
        self.max_frame_dimension = max_frame_dimension

    def inspect_video(self, video_path: Path) -> VideoMetadata:
        """
        Extracts structural video properties (dimensions, FPS, frame count, duration).
        Raises VideoProcessingError if the container cannot be parsed.
        """
        if not video_path.exists() or not video_path.is_file():
            raise VideoProcessingError(f"Video file does not exist: {video_path.name}")

        cap = cv2.VideoCapture(str(video_path))
        try:
            if not cap.isOpened():
                raise VideoProcessingError(f"Failed to open video container: {video_path.name}")

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = float(cap.get(cv2.CAP_PROP_FPS))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            if width <= 0 or height <= 0:
                raise VideoProcessingError(f"Invalid video dimensions ({width}x{height}) in {video_path.name}")

            # Safe fallback for variable frame rate or missing fps header
            if fps <= 0.0 or np.isnan(fps):
                fps = 30.0

            duration = (frame_count / fps) if frame_count > 0 else 0.0

            return VideoMetadata(
                width=width,
                height=height,
                fps=round(fps, 2),
                duration_seconds=round(duration, 2),
                frame_count=frame_count,
            )
        finally:
            cap.release()

    def sample_frames(
        self,
        video_path: Path,
        sample_interval: Optional[float] = None,
        max_frames: Optional[int] = None,
    ) -> List[SampledFrame]:
        """
        Samples video frames at regular temporal intervals.
        Enforces memory safety limits and frame downscaling.
        """
        interval = sample_interval or self.sample_interval_seconds
        limit = max_frames or self.max_sampled_frames

        if not video_path.exists() or not video_path.is_file():
            raise VideoProcessingError(f"Video file does not exist: {video_path.name}")

        cap = cv2.VideoCapture(str(video_path))
        try:
            if not cap.isOpened():
                raise VideoProcessingError(f"Failed to open video container: {video_path.name}")

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = float(cap.get(cv2.CAP_PROP_FPS))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            if width <= 0 or height <= 0 or frame_count <= 0:
                raise VideoProcessingError("Video contains no readable frames or has corrupted headers.")

            if fps <= 0.0 or np.isnan(fps):
                fps = 30.0

            frame_step = max(1, int(round(fps * interval)))
            target_indices = list(range(0, frame_count, frame_step))[:limit]

            sampled: List[SampledFrame] = []

            for frame_idx in target_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret or frame is None:
                    logger.debug("Could not read frame at index %d", frame_idx)
                    continue

                timestamp = round(frame_idx / fps, 3)

                # Resize if exceeding max_frame_dimension
                scale_factor = 1.0
                max_dim = max(frame.shape[0], frame.shape[1])
                processed_frame = frame
                if max_dim > self.max_frame_dimension:
                    scale_factor = self.max_frame_dimension / float(max_dim)
                    new_w = int(round(frame.shape[1] * scale_factor))
                    new_h = int(round(frame.shape[0] * scale_factor))
                    processed_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

                sampled.append(
                    SampledFrame(
                        frame_index=frame_idx,
                        timestamp_seconds=timestamp,
                        image=processed_frame,
                        original_width=width,
                        original_height=height,
                        scale_factor=scale_factor,
                    )
                )

            if not sampled:
                raise VideoProcessingError("No frames could be successfully decoded from the video.")

            logger.info("Sampled %d frames from video %s", len(sampled), video_path.name)
            return sampled

        finally:
            cap.release()

