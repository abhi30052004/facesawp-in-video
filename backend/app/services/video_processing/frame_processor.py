import logging
from typing import List, Optional, Tuple
import cv2
import numpy as np

from app.services.video_processing.face_alignment import FaceAligner
from app.services.video_processing.model_adapter import (
    BaseFaceSwapModelAdapter,
    ModelNotConfiguredError,
    UnconfiguredFaceSwapModelAdapter,
)

logger = logging.getLogger("bollyswap.services.video_processing.frame_processor")


def match_color_stats(source_bgr: np.ndarray, target_bgr: np.ndarray) -> np.ndarray:
    """
    Applies Reinhard color transfer from target_bgr (original face in video)
    to source_bgr (swapped face) in LAB color space to match skin tone,
    lighting temperature, and scene ambient color.
    """
    if source_bgr is None or target_bgr is None:
        return source_bgr

    # Convert to CIELAB space
    src_lab = cv2.cvtColor(source_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    tgt_lab = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)

    # Compute channel-wise mean and standard deviation
    src_mean = np.mean(src_lab, axis=(0, 1))
    src_std = np.std(src_lab, axis=(0, 1))
    tgt_mean = np.mean(tgt_lab, axis=(0, 1))
    tgt_std = np.std(tgt_lab, axis=(0, 1))

    # Guard against division by zero
    src_std = np.maximum(src_std, 1e-4)

    # Scale source distribution to match target distribution
    matched_lab = (src_lab - src_mean) * (tgt_std / src_std) + tgt_mean
    matched_lab = np.clip(matched_lab, 0, 255).astype(np.uint8)

    return cv2.cvtColor(matched_lab, cv2.COLOR_LAB2BGR)


def blend_face_composite(
    original_frame: np.ndarray,
    warped_face: np.ndarray,
    warped_mask: np.ndarray,
) -> np.ndarray:
    """
    Blends the warped swapped face onto the original frame using
    a feathered continuous alpha mask to avoid harsh seam boundaries.
    """
    if warped_mask is None:
        return original_frame

    # warped_mask is uint8 in range [0, 255]
    alpha = (warped_mask.astype(np.float32) / 255.0)
    if alpha.ndim == 2:
        alpha = alpha[:, :, None]

    # Linear interpolation composite
    comp = (alpha * warped_face.astype(np.float32)) + ((1.0 - alpha) * original_frame.astype(np.float32))
    return np.clip(comp, 0, 255).astype(np.uint8)


class TemporalFaceTracker:
    """
    Smooths facial landmarks and bounding boxes across consecutive video frames
    to eliminate micro-jitter and handle momentary 1-2 frame occlusions.
    """

    def __init__(self, smoothing_factor: float = 0.75, max_missed_frames: int = 2):
        self.smoothing_factor = smoothing_factor
        self.max_missed_frames = max_missed_frames
        self.last_bbox: Optional[Tuple[int, int, int, int]] = None
        self.last_landmarks: Optional[List[List[float]]] = None
        self.missed_counter: int = 0

    def update(
        self,
        detected_bbox: Optional[Tuple[int, int, int, int]],
        detected_landmarks: Optional[List[List[float]]],
    ) -> Tuple[Optional[Tuple[int, int, int, int]], Optional[List[List[float]]]]:
        """
        Updates tracking state with current detection or interpolates from history.
        """
        if detected_landmarks is not None and len(detected_landmarks) == 5:
            if self.last_landmarks is not None:
                # Apply exponential moving average smoothing
                alpha = self.smoothing_factor
                smoothed_lm: List[List[float]] = []
                for curr, prev in zip(detected_landmarks, self.last_landmarks):
                    sx = round(alpha * curr[0] + (1.0 - alpha) * prev[0], 2)
                    sy = round(alpha * curr[1] + (1.0 - alpha) * prev[1], 2)
                    smoothed_lm.append([sx, sy])
                self.last_landmarks = smoothed_lm
            else:
                self.last_landmarks = detected_landmarks

            self.last_bbox = detected_bbox
            self.missed_counter = 0
            return self.last_bbox, self.last_landmarks

        # If detection was missed in this frame, attempt interpolation
        if self.missed_counter < self.max_missed_frames and self.last_landmarks is not None:
            self.missed_counter += 1
            return self.last_bbox, self.last_landmarks

        # Lost tracking
        self.missed_counter += 1
        return None, None

    def reset(self) -> None:
        """Resets tracker state."""
        self.last_bbox = None
        self.last_landmarks = None
        self.missed_counter = 0


class FrameProcessor:
    """
    Coordinates per-frame facial landmark alignment, target face synthesis,
    color harmonization, and feathered coordinate re-projection.
    Enforces honest status reporting: never claims an unswapped diagnostic frame is swapped.
    """

    def __init__(
        self,
        model_adapter: Optional[BaseFaceSwapModelAdapter] = None,
        face_aligner: Optional[FaceAligner] = None,
        tracker: Optional[TemporalFaceTracker] = None,
        color_matching: bool = True,
        feather_edges: bool = True,
    ):
        self.model_adapter = model_adapter or UnconfiguredFaceSwapModelAdapter()
        self.face_aligner = face_aligner or FaceAligner(target_crop_size=256)
        self.tracker = tracker or TemporalFaceTracker()
        self.color_matching = color_matching
        self.feather_edges = feather_edges

    def process_frame(
        self,
        frame_bgr: np.ndarray,
        target_face_bgr: np.ndarray,
        landmarks: Optional[List[List[float]]] = None,
        bounding_box: Optional[Tuple[int, int, int, int]] = None,
        diagnostic_mode: bool = False,
    ) -> Tuple[np.ndarray, bool]:
        """
        Executes facial alignment, model inference, color matching, and feathered blending.

        Returns:
            Tuple[np.ndarray, bool]: (resulting_frame_bgr, was_swapped)
            was_swapped is strictly False if model is unavailable.
        """
        # 1. Update temporal tracker and smooth landmarks
        _, smoothed_landmarks = self.tracker.update(bounding_box, landmarks)

        if smoothed_landmarks is None or len(smoothed_landmarks) != 5:
            # No face detected or tracked in this frame, pass through untouched
            return frame_bgr.copy(), False

        # 2. Align face using canonical 5-point similarity transformation
        aligned_res = self.face_aligner.align_face(frame_bgr, smoothed_landmarks, bounding_box)

        # 3. Check model adapter availability
        if not self.model_adapter.is_available:
            if not diagnostic_mode:
                raise ModelNotConfiguredError(
                    "Face-swap neural model engine is unconfigured. "
                    "Configure FACE_SWAP_ENABLED=true and set FACE_SWAP_MODEL_PATH in .env."
                )
            # In explicit diagnostic pipeline test mode, return original frame untouched
            return frame_bgr.copy(), False

        # 4. Fast neural path if dedicated FaceSwapEngine is active
        if (
            hasattr(self.model_adapter, "engine")
            and self.model_adapter.engine is not None
            and self.model_adapter.engine.is_ready
        ):
            source_latent = self.model_adapter.get_or_compute_source_latent(target_face_bgr)
            composite, was_swapped = self.model_adapter.engine.process_frame(
                frame_bgr=frame_bgr,
                target_landmarks=smoothed_landmarks,
                source_latent=source_latent,
            )
            return composite, was_swapped

        # 5. Standard model inference via adapter canvas
        swapped_aligned = self.model_adapter.swap_face(
            source_aligned=aligned_res.aligned_face,
            target_face=target_face_bgr,
        )

        # 5. Natural color matching (harmonize lighting, ambient tone, and skin color)
        if self.color_matching:
            swapped_aligned = match_color_stats(
                source_bgr=swapped_aligned,
                target_bgr=aligned_res.aligned_face,
            )

        # 6. Generate feathered mask to eliminate sharp seams
        if self.feather_edges:
            feathered_mask = self.face_aligner.create_feathered_mask(self.face_aligner.target_crop_size)
        else:
            feathered_mask = np.full(
                (self.face_aligner.target_crop_size, self.face_aligner.target_crop_size),
                255,
                dtype=np.uint8,
            )

        # 7. Project swapped face and mask back to original frame coordinates
        warped_face, warped_mask = self.face_aligner.unalign_face(
            aligned_face=swapped_aligned,
            M_inv=aligned_res.metadata.inverse_affine_matrix,
            target_shape=frame_bgr.shape[:2],
            mask=feathered_mask,
        )

        # 8. Composite warped face with feathered alpha blending
        composite = blend_face_composite(frame_bgr, warped_face, warped_mask)

        return composite, True
