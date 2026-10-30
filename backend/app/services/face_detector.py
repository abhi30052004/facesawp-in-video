import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import cv2
import numpy as np

from app.services.video_service import SampledFrame

logger = logging.getLogger("bollyswap.services.detector")


class FaceDetectorError(Exception):
    """Raised when face detection model fails to load or execute."""
    def __init__(self, message: str, error_code: str = "FACE_DETECTOR_ERROR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


@dataclass
class DetectedFace:
    """Individual face detection instance on a single frame."""
    frame_index: int
    timestamp_seconds: float
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x, y, w, h) in original video resolution
    landmarks: List[List[float]]     # 5 points: [[re_x, re_y], [le_x, le_y], [nose_x, nose_y], [rm_x, rm_y], [lm_x, lm_y]]
    thumbnail_bytes: bytes           # High-quality cropped face thumbnail (JPEG)


class FaceDetectorYuNet:
    """
    Real AI face detector leveraging OpenCV's FaceDetectorYN (YuNet).
    Runs strictly on CPU, extracts 5 facial landmarks, calculates detection confidence,
    and crops bounded thumbnails without external cloud dependencies.
    """

    def __init__(
        self,
        model_path: Path,
        confidence_threshold: float = 0.6,
        nms_threshold: float = 0.3,
        top_k: int = 5000,
    ):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.top_k = top_k
        self._detector: Optional[cv2.FaceDetectorYN] = None
        self._load_model()

    def _load_model(self) -> None:
        """Loads and verifies the YuNet ONNX model."""
        if not self.model_path.exists():
            raise FaceDetectorError(
                f"YuNet ONNX model file not found at: {self.model_path}. "
                "Ensure face_detection_yunet_2023mar.onnx is present in backend/models.",
                error_code="MODEL_NOT_FOUND",
            )

        try:
            # Initialize with default 320x320 size; will be dynamically adjusted per frame
            self._detector = cv2.FaceDetectorYN.create(
                model=str(self.model_path),
                config="",
                input_size=(320, 320),
                score_threshold=self.confidence_threshold,
                nms_threshold=self.nms_threshold,
                top_k=self.top_k,
            )
            logger.info("OpenCV YuNet face detector initialized successfully from %s", self.model_path.name)
        except Exception as e:
            logger.exception("Failed to initialize OpenCV FaceDetectorYN")
            raise FaceDetectorError(
                f"Failed to create YuNet face detector: {type(e).__name__} - {str(e)}",
                error_code="MODEL_LOAD_FAILED",
            )

    @staticmethod
    def crop_face(
        frame: np.ndarray,
        x: int,
        y: int,
        w: int,
        h: int,
        padding_pct: float = 0.20,
    ) -> Optional[np.ndarray]:
        """
        Safely crops a face region with padding while preventing out-of-bounds indexing.
        """
        frame_h, frame_w = frame.shape[:2]

        pad_x = int(w * padding_pct)
        pad_y = int(h * padding_pct)

        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(frame_w, x + w + pad_x)
        y2 = min(frame_h, y + h + pad_y)

        if (x2 - x1) < 16 or (y2 - y1) < 16:
            return None

        return frame[y1:y2, x1:x2].copy()

    def detect_in_frame(
        self,
        frame_data: SampledFrame,
    ) -> List[DetectedFace]:
        """
        Runs YuNet detection on a single SampledFrame and maps coordinates
        back to the original video resolution.
        """
        if self._detector is None:
            self._load_model()

        img = frame_data.image
        h, w = img.shape[:2]

        # Dynamically set input size for the current frame
        self._detector.setInputSize((w, h))

        retval, raw_faces = self._detector.detect(img)
        if retval == 0 or raw_faces is None or len(raw_faces) == 0:
            return []

        scale = frame_data.scale_factor
        results: List[DetectedFace] = []

        for row in raw_faces:
            # YuNet output layout:
            # 0:4 -> bbox [x, y, w, h]
            # 4:14 -> 5 landmarks (right eye, left eye, nose, right mouth, left mouth)
            # 14 -> confidence score
            conf = float(row[14])
            if conf < self.confidence_threshold:
                continue

            bx, by, bw, bh = float(row[0]), float(row[1]), float(row[2]), float(row[3])

            # Safely crop thumbnail from the processed (unscaled) frame
            cropped = self.crop_face(img, int(bx), int(by), int(bw), int(bh))
            if cropped is None:
                continue

            # Encode thumbnail as JPEG
            encode_ret, jpeg_buf = cv2.imencode(".jpg", cropped, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            if not encode_ret:
                continue

            # Project coordinates back to original video dimensions
            orig_x = int(round(bx / scale))
            orig_y = int(round(by / scale))
            orig_w = int(round(bw / scale))
            orig_h = int(round(bh / scale))

            # Project 5 landmarks back to original video dimensions
            landmarks: List[List[float]] = []
            for i in range(5):
                lx = float(row[4 + i * 2]) / scale
                ly = float(row[5 + i * 2]) / scale
                landmarks.append([round(lx, 1), round(ly, 1)])

            results.append(
                DetectedFace(
                    frame_index=frame_data.frame_index,
                    timestamp_seconds=frame_data.timestamp_seconds,
                    confidence=round(conf, 4),
                    bbox=(orig_x, orig_y, orig_w, orig_h),
                    landmarks=landmarks,
                    thumbnail_bytes=bytes(jpeg_buf),
                )
            )

        return results

    def detect_in_video_frames(
        self,
        sampled_frames: List[SampledFrame],
    ) -> List[DetectedFace]:
        """Runs face detection sequentially across all sampled video frames."""
        all_detections: List[DetectedFace] = []
        for frame in sampled_frames:
            detections = self.detect_in_frame(frame)
            all_detections.extend(detections)

        logger.info(
            "YuNet detected %d faces across %d sampled frames",
            len(all_detections),
            len(sampled_frames),
        )
        return all_detections

