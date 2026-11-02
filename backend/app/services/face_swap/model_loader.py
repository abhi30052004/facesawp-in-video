"""
Model Loader for Neural Face Swap Engine.
Initializes ONNX Runtime sessions for:
1. inswapper_128.onnx (InsightFace Inswapper)
2. w600k_r50.onnx (ArcFace ResNet-50 512-D identity extractor)
Extracts the EMAP embedding projection matrix and enforces CPUExecutionProvider.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger("bollyswap.services.face_swap.loader")


@dataclass
class ModelSessionBundle:
    """Holds active ONNX Runtime sessions and metadata."""
    swap_session: Any
    recognition_session: Any
    emap: np.ndarray
    swap_inputs: List[Dict[str, Any]]
    swap_outputs: List[Dict[str, Any]]
    rec_inputs: List[Dict[str, Any]]
    rec_outputs: List[Dict[str, Any]]


class FaceSwapModelLoader:
    """
    Manages loading, validation, and session lifecycle for ONNX face swapping models.
    Guarantees pure CPU execution without requiring GPU or CUDA dependencies.
    """

    def __init__(
        self,
        inswapper_path: Path,
        arcface_path: Path,
        provider: str = "CPUExecutionProvider",
        intra_op_num_threads: int = 4,
    ):
        self.inswapper_path = Path(inswapper_path)
        self.arcface_path = Path(arcface_path)
        self.provider = provider
        self.intra_op_num_threads = intra_op_num_threads
        self._bundle: Optional[ModelSessionBundle] = None

    @property
    def is_loaded(self) -> bool:
        return self._bundle is not None

    def get_bundle(self) -> ModelSessionBundle:
        if self._bundle is None:
            raise RuntimeError("Face swap models are not loaded. Call load() first.")
        return self._bundle

    def load(self) -> ModelSessionBundle:
        """
        Loads both inswapper and ArcFace models, extracts emap, and builds session bundle.
        """
        if self._bundle is not None:
            return self._bundle

        if not self.inswapper_path.exists() or not self.inswapper_path.is_file():
            raise FileNotFoundError(f"Inswapper ONNX model not found at: {self.inswapper_path}")

        if not self.arcface_path.exists() or not self.arcface_path.is_file():
            raise FileNotFoundError(f"ArcFace ONNX model not found at: {self.arcface_path}")

        import onnx
        from onnx import numpy_helper
        import onnxruntime as ort

        # Ensure CPUExecutionProvider is available
        available_providers = ort.get_available_providers()
        target_provider = (
            self.provider if self.provider in available_providers else "CPUExecutionProvider"
        )
        logger.info("Initializing FaceSwapModelLoader with provider: %s", target_provider)

        # 1. Extract EMAP projection matrix from inswapper ONNX initializers
        onnx_model = onnx.load(str(self.inswapper_path))
        emap: Optional[np.ndarray] = None

        # Look for 512x512 matrix in graph initializers
        for init in onnx_model.graph.initializer:
            arr = numpy_helper.to_array(init)
            if arr.ndim == 2 and arr.shape == (512, 512):
                emap = arr
                logger.debug("Found EMAP initializer by shape (512, 512): %s", init.name)
                break

        # Fallback to last initializer as standard in InsightFace inswapper
        if emap is None and len(onnx_model.graph.initializer) > 0:
            last_init = onnx_model.graph.initializer[-1]
            arr = numpy_helper.to_array(last_init)
            if arr.ndim == 2 and arr.shape == (512, 512):
                emap = arr
                logger.debug("Found EMAP as last initializer: %s", last_init.name)

        if emap is None:
            logger.warning(
                "Could not find 512x512 EMAP in inswapper initializers. Using identity projection."
            )
            emap = np.eye(512, dtype=np.float32)

        # Session optimization configuration
        sess_opts = ort.SessionOptions()
        sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_opts.intra_op_num_threads = self.intra_op_num_threads
        sess_opts.inter_op_num_threads = 1
        sess_opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

        # 2. Inswapper Session
        logger.info("Creating ONNX Runtime session for Inswapper: %s", self.inswapper_path.name)
        swap_sess = ort.InferenceSession(
            str(self.inswapper_path),
            sess_options=sess_opts,
            providers=[target_provider],
        )
        swap_inputs = [
            {"name": inp.name, "shape": inp.shape, "type": inp.type}
            for inp in swap_sess.get_inputs()
        ]
        swap_outputs = [
            {"name": out.name, "shape": out.shape, "type": out.type}
            for out in swap_sess.get_outputs()
        ]

        # 3. ArcFace Recognition Session
        logger.info("Creating ONNX Runtime session for ArcFace: %s", self.arcface_path.name)
        rec_sess = ort.InferenceSession(
            str(self.arcface_path),
            sess_options=sess_opts,
            providers=[target_provider],
        )
        rec_inputs = [
            {"name": inp.name, "shape": inp.shape, "type": inp.type}
            for inp in rec_sess.get_inputs()
        ]
        rec_outputs = [
            {"name": out.name, "shape": out.shape, "type": out.type}
            for out in rec_sess.get_outputs()
        ]

        self._bundle = ModelSessionBundle(
            swap_session=swap_sess,
            recognition_session=rec_sess,
            emap=emap.astype(np.float32),
            swap_inputs=swap_inputs,
            swap_outputs=swap_outputs,
            rec_inputs=rec_inputs,
            rec_outputs=rec_outputs,
        )

        logger.info(
            "FaceSwapModelLoader loaded successfully: Inswapper (%s -> %s), ArcFace (%s -> %s)",
            [i["name"] for i in swap_inputs],
            [o["name"] for o in swap_outputs],
            [i["name"] for i in rec_inputs],
            [o["name"] for o in rec_outputs],
        )
        return self._bundle

    def unload(self) -> None:
        """Releases session references and memory."""
        self._bundle = None

