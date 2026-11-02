"""
Neural Face Swap Engine for BollySwap AI.
Coordinates real deep learning face replacement using:
- ArcFace ResNet-50 for source biometric identity extraction.
- Inswapper 128x128 for latent facial expression and pose conditioning.
- Seamless feathered edge compositing and LAB color harmonization.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

from app.services.face_swap.face_blender import FaceBlender
from app.services.face_swap.face_preprocessor import FacePreprocessor, TargetFaceCrop
from app.services.face_swap.model_loader import FaceSwapModelLoader, ModelSessionBundle

logger = logging.getLogger("bollyswap.services.face_swap.engine")


@dataclass
class FaceSwapEngineConfig:
    """Configuration parameters for the neural face swap engine."""
    inswapper_path: Path
    arcface_path: Path
    provider: str = "CPUExecutionProvider"
    intra_op_num_threads: int = 4
    color_matching: bool = True
    feather_edges: bool = True


class FaceSwapEngine:
    """
    Production face replacement engine.
    Executes real neural inference via ONNX Runtime CPU.
    """

    def __init__(self, config: FaceSwapEngineConfig):
        self.config = config
        self.loader = FaceSwapModelLoader(
            inswapper_path=config.inswapper_path,
            arcface_path=config.arcface_path,
            provider=config.provider,
            intra_op_num_threads=config.intra_op_num_threads,
        )
        self.preprocessor = FacePreprocessor()
        self.blender = FaceBlender()
        self._bundle: Optional[ModelSessionBundle] = None

    @property
    def is_ready(self) -> bool:
        return self._bundle is not None and self.loader.is_loaded

    def initialize(self) -> bool:
        """Loads sessions into memory and extracts EMAP matrix."""
        try:
            self._bundle = self.loader.load()
            logger.info("FaceSwapEngine initialized and ready for neural inference.")
            return True
        except Exception as e:
            logger.exception("Failed to initialize FaceSwapEngine: %s", e)
            self._bundle = None
            return False

    def compute_source_identity(
        self,
        source_bgr: np.ndarray,
        source_landmarks: List[List[float]],
    ) -> np.ndarray:
        """
        Extracts 512-D identity embedding from replacement face portrait,
        projects through Inswapper EMAP, and normalizes into unit sphere.
        This operation is executed once per video processing job.
        Returns:
            latent: (1, 512) float32 normalized vector.
        """
        if not self.is_ready or self._bundle is None:
            raise RuntimeError("FaceSwapEngine is not initialized.")

        # 1. 112x112 similarity alignment
        aligned_112 = self.preprocessor.align_source_face_112(source_bgr, source_landmarks)

        # 2. Prepare normalized ArcFace input blob
        arc_blob = self.preprocessor.prepare_arcface_input(aligned_112)

        # 3. Run ArcFace recognition model
        rec_sess = self._bundle.recognition_session
        input_name = self._bundle.rec_inputs[0]["name"]
        output_name = self._bundle.rec_outputs[0]["name"]

        raw_feat = rec_sess.run([output_name], {input_name: arc_blob})[0]

        # 4. Project via EMAP and normalize
        latent = self.preprocessor.project_identity_embedding(raw_feat, self._bundle.emap)
        logger.debug("Computed source identity latent vector with shape: %s", latent.shape)
        return latent

    def swap_single_face(
        self,
        target_crop: TargetFaceCrop,
        source_latent: np.ndarray,
    ) -> np.ndarray:
        """
        Runs Inswapper neural inference to transfer source identity onto target aligned crop.
        Returns 128x128 uint8 BGR face image.
        """
        if not self.is_ready or self._bundle is None:
            raise RuntimeError("FaceSwapEngine is not initialized.")

        swap_sess = self._bundle.swap_session
        inp_meta = self._bundle.swap_inputs

        # Identify input node names
        target_node = inp_meta[0]["name"]
        source_node = inp_meta[1]["name"]
        for m in inp_meta:
            name_l = m["name"].lower()
            if any(k in name_l for k in ("source", "src", "id", "latent")):
                source_node = m["name"]
            elif any(k in name_l for k in ("target", "dst", "img", "image")):
                target_node = m["name"]

        output_name = self._bundle.swap_outputs[0]["name"]

        feed_dict = {
            target_node: target_crop.target_blob,
            source_node: source_latent,
        }

        # Run ONNX Runtime inference
        pred = swap_sess.run([output_name], feed_dict)[0]

        # pred has shape (1, 3, 128, 128) float32 in range [0, 1] (or [0, 255])
        out_arr = pred[0]
        out_rgb = np.transpose(out_arr, (1, 2, 0))

        # Check normalization scale
        max_val = float(np.max(out_rgb))
        if max_val <= 1.5:
            out_rgb = out_rgb * 255.0

        out_rgb = np.clip(out_rgb, 0, 255).astype(np.uint8)
        swapped_bgr = cv2.cvtColor(out_rgb, cv2.COLOR_RGB2BGR)

        return swapped_bgr

    def process_frame(
        self,
        frame_bgr: np.ndarray,
        target_landmarks: List[List[float]],
        source_latent: np.ndarray,
    ) -> Tuple[np.ndarray, bool]:
        """
        Performs full end-to-end face swap on a single video frame:
        1. 128x128 alignment
        2. Inswapper neural generation
        3. Color transfer and feathered boundary alpha blending
        """
        if not self.is_ready:
            return frame_bgr.copy(), False

        # 1. Align target face in frame to 128x128
        target_crop = self.preprocessor.align_target_face_128(frame_bgr, target_landmarks)

        # 2. Execute neural face swap
        swapped_128_bgr = self.swap_single_face(target_crop, source_latent)

        # 3. Blend swapped face into original frame
        composite = self.blender.blend(
            frame_bgr=frame_bgr,
            swapped_128_bgr=swapped_128_bgr,
            original_target_128_bgr=target_crop.aligned_bgr,
            M_inv=target_crop.M_inv,
            apply_color_match=self.config.color_matching,
        )

        return composite, True

    def cleanup(self) -> None:
        """Unloads sessions from memory."""
        self.loader.unload()
        self._bundle = None
