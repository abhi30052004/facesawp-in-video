"""
Face Color Transfer and Seamless Feathered Mask Blending.
Harmonizes skin tone, ambient scene lighting, and color temperature using
Reinhard LAB color transfer, and projects the swapped face back to the native
frame coordinates with smooth Gaussian boundary falloff.
"""

import logging
from typing import Optional, Tuple
import cv2
import numpy as np

logger = logging.getLogger("bollyswap.services.face_swap.blender")


class FaceBlender:
    """
    Handles color matching and seamless compositing of swapped faces onto video frames.
    """

    def __init__(
        self,
        blur_kernel_size: int = 19,
        blur_sigma: float = 7.0,
    ):
        self.blur_kernel_size = (
            blur_kernel_size if blur_kernel_size % 2 == 1 else blur_kernel_size + 1
        )
        self.blur_sigma = blur_sigma
        self._cached_mask_128: Optional[np.ndarray] = None

    def get_feathered_mask_128(self) -> np.ndarray:
        """
        Creates or returns cached feathered elliptical mask for 128x128 resolution.
        """
        if self._cached_mask_128 is not None:
            return self._cached_mask_128

        mask = np.zeros((128, 128), dtype=np.uint8)
        # Ellipse covering facial features while leaving hairline and jaw edges smooth
        center = (64, 68)
        axes = (48, 56)
        cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)

        # Apply Gaussian blur for soft transition
        feathered = cv2.GaussianBlur(mask, (self.blur_kernel_size, self.blur_kernel_size), self.blur_sigma)
        self._cached_mask_128 = feathered
        return self._cached_mask_128

    @staticmethod
    def match_color_reinhard(source_bgr: np.ndarray, target_bgr: np.ndarray) -> np.ndarray:
        """
        Transfers color distribution from target_bgr (original actor face)
        to source_bgr (swapped face) in CIELAB color space.
        Preserves natural ambient lighting, contrast, and skin tone.
        """
        if source_bgr is None or target_bgr is None:
            return source_bgr

        src_lab = cv2.cvtColor(source_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
        tgt_lab = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)

        src_mean = np.mean(src_lab, axis=(0, 1))
        src_std = np.std(src_lab, axis=(0, 1))
        tgt_mean = np.mean(tgt_lab, axis=(0, 1))
        tgt_std = np.std(tgt_lab, axis=(0, 1))

        # Guard against zero-variance channels
        src_std = np.maximum(src_std, 1e-4)

        # Scale and shift distribution
        matched_lab = (src_lab - src_mean) * (tgt_std / src_std) + tgt_mean
        matched_lab = np.clip(matched_lab, 0, 255).astype(np.uint8)

        return cv2.cvtColor(matched_lab, cv2.COLOR_LAB2BGR)

    def blend(
        self,
        frame_bgr: np.ndarray,
        swapped_128_bgr: np.ndarray,
        original_target_128_bgr: np.ndarray,
        M_inv: np.ndarray,
        apply_color_match: bool = True,
    ) -> np.ndarray:
        """
        Applies color harmonization, unaligns swapped face to native frame coordinates,
        and composites using the feathered alpha mask.
        """
        # 1. Color transfer to harmonize lighting
        if apply_color_match and original_target_128_bgr is not None:
            harmonized_128 = self.match_color_reinhard(
                source_bgr=swapped_128_bgr,
                target_bgr=original_target_128_bgr,
            )
        else:
            harmonized_128 = swapped_128_bgr

        # 2. Get feathered 128x128 mask
        mask_128 = self.get_feathered_mask_128()

        # 3. Project swapped face and mask back to frame coordinates
        frame_h, frame_w = frame_bgr.shape[:2]

        warped_face = cv2.warpAffine(
            harmonized_128,
            M_inv,
            (frame_w, frame_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )

        warped_mask = cv2.warpAffine(
            mask_128,
            M_inv,
            (frame_w, frame_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )

        # 4. Continuous alpha composition
        alpha = warped_mask.astype(np.float32) / 255.0
        if alpha.ndim == 2:
            alpha = alpha[:, :, None]

        composite = (alpha * warped_face.astype(np.float32)) + ((1.0 - alpha) * frame_bgr.astype(np.float32))
        return np.clip(composite, 0, 255).astype(np.uint8)

