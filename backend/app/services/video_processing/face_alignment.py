import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple
import cv2
import numpy as np

logger = logging.getLogger("bollyswap.services.video_processing.alignment")

# Standard 5-point canonical template for 112x112 face alignment (ArcFace/InsightFace reference)
# Points: [right_eye, left_eye, nose_tip, right_mouth_corner, left_mouth_corner]
CANONICAL_TEMPLATE_112 = np.array(
    [
        [38.2946, 51.6963],  # Right eye
        [73.5318, 51.5014],  # Left eye
        [56.0252, 71.7366],  # Nose tip
        [41.5493, 92.3655],  # Right mouth corner
        [70.7299, 92.2041],  # Left mouth corner
    ],
    dtype=np.float32,
)


@dataclass
class AlignedFaceMetadata:
    """Metadata and transformation matrices for an aligned face crop."""
    crop_size: int
    affine_matrix: np.ndarray          # 2x3 forward transform matrix
    inverse_affine_matrix: np.ndarray  # 2x3 backward transform matrix
    source_landmarks: List[List[float]]
    source_bounding_box: Optional[Tuple[int, int, int, int]] = None


@dataclass
class AlignedFaceResult:
    """Cropped canonical aligned face image with transformation metadata."""
    aligned_face: np.ndarray
    metadata: AlignedFaceMetadata


class FaceAligner:
    """
    Extracts and normalizes facial crops using 5-point similarity transformation.
    Preserves forward and backward affine matrices to allow exact spatial re-projection.
    """

    def __init__(self, target_crop_size: int = 256):
        self.target_crop_size = target_crop_size
        scale = float(target_crop_size) / 112.0
        self.reference_landmarks = CANONICAL_TEMPLATE_112 * scale

    def compute_similarity_transform(
        self,
        landmarks: List[List[float]],
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes 2x3 forward similarity matrix M and inverse matrix M_inv
        mapping source landmarks to canonical reference points.
        """
        src_pts = np.array(landmarks, dtype=np.float32)
        if src_pts.shape != (5, 2):
            raise ValueError(f"Expected 5 landmark points [x, y], got shape: {src_pts.shape}")

        # Estimate partial 2D affine (similarity transform: translation, rotation, uniform scale)
        M, inliers = cv2.estimateAffinePartial2D(src_pts, self.reference_landmarks, method=cv2.LMEDS)
        if M is None:
            # Fallback to least squares
            M, inliers = cv2.estimateAffinePartial2D(src_pts, self.reference_landmarks)

        if M is None:
            raise RuntimeError("Failed to compute similarity transform from facial landmarks.")

        M_inv = cv2.invertAffineTransform(M)
        return M, M_inv

    def align_face(
        self,
        frame_bgr: np.ndarray,
        landmarks: List[List[float]],
        bounding_box: Optional[Tuple[int, int, int, int]] = None,
    ) -> AlignedFaceResult:
        """
        Warps the face region of the frame into standard canonical alignment.
        """
        M, M_inv = self.compute_similarity_transform(landmarks)

        aligned_crop = cv2.warpAffine(
            frame_bgr,
            M,
            (self.target_crop_size, self.target_crop_size),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT,
        )

        meta = AlignedFaceMetadata(
            crop_size=self.target_crop_size,
            affine_matrix=M,
            inverse_affine_matrix=M_inv,
            source_landmarks=landmarks,
            source_bounding_box=bounding_box,
        )

        return AlignedFaceResult(aligned_face=aligned_crop, metadata=meta)

    @staticmethod
    def create_feathered_mask(
        crop_size: int = 256,
        blur_kernel_size: int = 25,
        blur_sigma: float = 9.0,
    ) -> np.ndarray:
        """
        Creates an elliptical mask with smooth Gaussian gradient falloff at perimeter.
        Prevents harsh seams when re-projecting swapped faces onto video frames.
        """
        mask = np.zeros((crop_size, crop_size), dtype=np.uint8)
        center = (crop_size // 2, int(crop_size * 0.52))
        axes = (int(crop_size * 0.40), int(crop_size * 0.46))

        # Draw solid elliptical core
        cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)

        # Smooth edges via Gaussian blur
        k = blur_kernel_size if blur_kernel_size % 2 == 1 else blur_kernel_size + 1
        feathered = cv2.GaussianBlur(mask, (k, k), blur_sigma)
        return feathered

    def unalign_face(
        self,
        aligned_face: np.ndarray,
        M_inv: np.ndarray,
        target_shape: Tuple[int, int],  # (height, width)
        mask: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Projects an aligned face back into the source frame's coordinate system.
        Returns the warped face canvas and a feathered alignment mask.
        """
        target_h, target_w = target_shape

        if mask is None:
            # Default to full mask for legacy compatibility or create feathered mask
            mask = np.full(aligned_face.shape[:2], 255, dtype=np.uint8)

        warped_face = cv2.warpAffine(
            aligned_face,
            M_inv,
            (target_w, target_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )

        warped_mask = cv2.warpAffine(
            mask,
            M_inv,
            (target_w, target_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )

        return warped_face, warped_mask
