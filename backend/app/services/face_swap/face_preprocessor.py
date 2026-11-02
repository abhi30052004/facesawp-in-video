"""
Facial Alignment and Preprocessing for Real Neural Face Swapping.
Handles:
1. 112x112 similarity alignment for ArcFace identity embedding extraction.
2. 128x128 similarity alignment for Inswapper target face processing.
3. Accurate affine forward and inverse transformation matrices.
4. Tensor normalization and projection via EMAP.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple
import cv2
import numpy as np

logger = logging.getLogger("bollyswap.services.face_swap.preprocessor")

# 5-point canonical template for 112x112 ArcFace recognition
# Order: [right_eye, left_eye, nose_tip, right_mouth_corner, left_mouth_corner]
ARCFACE_112_TEMPLATE = np.array(
    [
        [38.2946, 51.6963],  # Right eye
        [73.5318, 51.5014],  # Left eye
        [56.0252, 71.7366],  # Nose tip
        [41.5493, 92.3655],  # Right mouth corner
        [70.7299, 92.2041],  # Left mouth corner
    ],
    dtype=np.float32,
)

# 5-point canonical template for 128x128 Inswapper face generator
# Centers the 112x112 facial region horizontally with +8px offset on left and right
INSWAPPER_128_TEMPLATE = ARCFACE_112_TEMPLATE + np.array([8.0, 0.0], dtype=np.float32)


@dataclass
class TargetFaceCrop:
    """Cropped target face ready for Inswapper with spatial matrix transforms."""
    aligned_bgr: np.ndarray          # (128, 128, 3) uint8 BGR
    target_blob: np.ndarray          # (1, 3, 128, 128) float32 RGB in [0, 1]
    M: np.ndarray                    # 2x3 forward transform matrix
    M_inv: np.ndarray                # 2x3 inverse transform matrix


class FacePreprocessor:
    """
    Coordinates geometric normalization and tensor preparation for face swapping.
    """

    @staticmethod
    def estimate_similarity_transform(
        landmarks: List[List[float]],
        template: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes forward similarity matrix M and inverse matrix M_inv
        mapping source landmarks to the canonical facial template.
        """
        src_pts = np.asarray(landmarks, dtype=np.float32)
        if src_pts.shape != (5, 2):
            raise ValueError(f"Expected 5 2D landmarks, got shape: {src_pts.shape}")

        M, _ = cv2.estimateAffinePartial2D(src_pts, template, method=cv2.LMEDS)
        if M is None:
            M, _ = cv2.estimateAffinePartial2D(src_pts, template)

        if M is None:
            raise RuntimeError("Failed to compute affine similarity transform.")

        M_inv = cv2.invertAffineTransform(M)
        return M, M_inv

    def align_source_face_112(
        self,
        source_img_bgr: np.ndarray,
        landmarks: List[List[float]],
    ) -> np.ndarray:
        """
        Aligns source image to 112x112 canonical resolution for ArcFace recognition.
        """
        M, _ = self.estimate_similarity_transform(landmarks, ARCFACE_112_TEMPLATE)
        aligned = cv2.warpAffine(
            source_img_bgr,
            M,
            (112, 112),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT,
        )
        return aligned

    def prepare_arcface_input(self, aligned_112_bgr: np.ndarray) -> np.ndarray:
        """
        Converts 112x112 BGR image into ArcFace normalized input tensor:
        Shape: (1, 3, 112, 112) float32, range [-1.0, 1.0], RGB channel order.
        """
        blob = cv2.dnn.blobFromImage(
            aligned_112_bgr,
            scalefactor=1.0 / 127.5,
            size=(112, 112),
            mean=(127.5, 127.5, 127.5),
            swapRB=True,
        )
        return blob.astype(np.float32)

    def project_identity_embedding(
        self,
        raw_embedding: np.ndarray,
        emap: np.ndarray,
    ) -> np.ndarray:
        """
        L2-normalizes the raw ArcFace 512-D embedding and projects it
        into the Inswapper latent space via the model's EMAP matrix.
        Returns:
            latent: (1, 512) float32 normalized latent identity vector.
        """
        emb = raw_embedding.flatten().astype(np.float32)
        norm = np.linalg.norm(emb)
        if norm > 1e-6:
            emb = emb / norm

        # Project via EMAP
        latent = np.dot(emb.reshape(1, 512), emap)
        latent_norm = np.linalg.norm(latent)
        if latent_norm > 1e-6:
            latent = latent / latent_norm

        return latent.astype(np.float32)

    def align_target_face_128(
        self,
        frame_bgr: np.ndarray,
        landmarks: List[List[float]],
    ) -> TargetFaceCrop:
        """
        Aligns target face in a video frame to 128x128 canonical resolution for Inswapper.
        Returns cropped BGR canvas, normalized float32 RGB tensor blob, and transform matrices.
        """
        M, M_inv = self.estimate_similarity_transform(landmarks, INSWAPPER_128_TEMPLATE)
        aligned_bgr = cv2.warpAffine(
            frame_bgr,
            M,
            (128, 128),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT,
        )

        # Normalize to [0, 1] RGB tensor (1, 3, 128, 128)
        target_blob = cv2.dnn.blobFromImage(
            aligned_bgr,
            scalefactor=1.0 / 255.0,
            size=(128, 128),
            mean=(0.0, 0.0, 0.0),
            swapRB=True,
        ).astype(np.float32)

        return TargetFaceCrop(
            aligned_bgr=aligned_bgr,
            target_blob=target_blob,
            M=M,
            M_inv=M_inv,
        )
