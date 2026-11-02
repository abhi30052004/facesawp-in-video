import abc
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

logger = logging.getLogger("bollyswap.services.video_processing.model_adapter")


class ModelNotConfiguredError(Exception):
    """Raised when face-swap inference is requested but no licensed model engine is configured."""
    def __init__(
        self,
        message: str = (
            "Face-swap neural model engine is unconfigured. "
            "To enable neural inference, configure FACE_SWAP_ENABLED=true and set a valid "
            "licensed model path in FACE_SWAP_MODEL_PATH."
        ),
        error_code: str = "MODEL_NOT_CONFIGURED",
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class BaseFaceSwapModelAdapter(abc.ABC):
    """
    Abstract interface for neural face-swapping engines.
    Allows seamless integration of approved and licensed swap models
    without altering video frame extraction, alignment, or encoding pipelines.
    """

    @property
    @abc.abstractmethod
    def is_available(self) -> bool:
        """Returns True only if valid licensed model weights are initialized and ready."""
        pass

    @abc.abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Returns metadata regarding the engine, provider, license, and input specifications."""
        pass

    @abc.abstractmethod
    def initialize(self) -> bool:
        """Initializes model weights, graph bindings, and runtime sessions."""
        pass

    @abc.abstractmethod
    def validate_inputs(
        self,
        source_aligned: np.ndarray,
        target_face: np.ndarray,
    ) -> bool:
        """Validates input matrix shapes, color channels, and value ranges."""
        pass

    @abc.abstractmethod
    def swap_face(
        self,
        source_aligned: np.ndarray,
        target_face: np.ndarray,
    ) -> np.ndarray:
        """
        Executes face-swap inference.
        Returns the swapped aligned face canvas or raises ModelNotConfiguredError.
        """
        pass

    @abc.abstractmethod
    def cleanup(self) -> None:
        """Releases session handles, memory pools, and temporary execution buffers."""
        pass


class UnconfiguredFaceSwapModelAdapter(BaseFaceSwapModelAdapter):
    """
    Default model adapter when no licensed model is configured.
    Reports honest model_not_configured status and guarantees no simulated or fake outputs.
    """

    def __init__(self, reason: str = "Neural face-swap engine is unconfigured."):
        self.reason = reason

    @property
    def is_available(self) -> bool:
        return False

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "unconfigured",
            "version": "N/A",
            "status": "model_not_configured",
            "license": "Unconfigured",
            "description": (
                "Video processing pipeline foundation is operational. "
                "The neural face-swapping model engine is deliberately unconfigured in Phase 5A / Phase 5B "
                "until an approved, licensed ONNX model path is provided via FACE_SWAP_MODEL_PATH."
            ),
            "input_resolution": "256x256",
            "supported_backends": ["CPU"],
            "reason": self.reason,
        }

    def initialize(self) -> bool:
        logger.info("FaceSwapModelAdapter: Unconfigured. Awaiting licensed ONNX model weights.")
        return False

    def validate_inputs(
        self,
        source_aligned: np.ndarray,
        target_face: np.ndarray,
    ) -> bool:
        if source_aligned is None or target_face is None:
            return False
        if len(source_aligned.shape) != 3 or len(target_face.shape) != 3:
            return False
        if source_aligned.shape[2] != 3 or target_face.shape[2] != 3:
            return False
        return True

    def swap_face(
        self,
        source_aligned: np.ndarray,
        target_face: np.ndarray,
    ) -> np.ndarray:
        raise ModelNotConfiguredError(
            "Face-swap neural model engine is unconfigured. "
            "Configure FACE_SWAP_ENABLED=true and a valid licensed model path in FACE_SWAP_MODEL_PATH."
        )

    def cleanup(self) -> None:
        pass


class LicensedFaceSwapModelAdapter(BaseFaceSwapModelAdapter):
    """
    Real neural face-swap engine adapter executing via ONNX Runtime CPU.
    Accepts licensed ONNX models, executes CPU inference, and transforms
    canonical facial crops with strict input and output validation.
    """

    def __init__(
        self,
        model_path: Path,
        arcface_path: Optional[Path] = None,
        license_name: str = "InsightFace-NonCommercial-Research",
        provider: str = "CPUExecutionProvider",
        input_size: int = 128,
    ):
        self.model_path = Path(model_path)
        self.arcface_path = Path(arcface_path) if arcface_path else None
        self.license_name = license_name
        self.provider = provider
        self.input_size = input_size
        self._session: Optional[Any] = None
        self._is_available: bool = False
        self._input_meta: List[Dict[str, Any]] = []
        self._output_meta: List[Dict[str, Any]] = []
        self.engine: Optional[Any] = None
        self._cached_source_latent: Optional[np.ndarray] = None
        self._cached_source_id: Optional[int] = None

    @property
    def is_available(self) -> bool:
        return self._is_available and (self._session is not None or (self.engine is not None and self.engine.is_ready))

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": self.model_path.name if self.model_path else "licensed_onnx",
            "version": "1.0.0",
            "status": "ready" if self.is_available else "model_not_configured",
            "license": self.license_name,
            "provider": self.provider,
            "input_resolution": f"{self.input_size}x{self.input_size}",
            "supported_backends": ["CPU"],
            "input_nodes": [m["name"] for m in self._input_meta],
            "output_nodes": [m["name"] for m in self._output_meta],
            "arcface_model": self.arcface_path.name if self.arcface_path else None,
            "neural_engine_ready": self.engine is not None and self.engine.is_ready,
        }

    def initialize(self) -> bool:
        """
        Loads the ONNX model into an ONNX Runtime InferenceSession configured
        for sequential CPU execution with thread pools.
        If ArcFace model is also available, initializes full FaceSwapEngine.
        """
        if not self.model_path.exists() or not self.model_path.is_file():
            logger.warning("Face swap model file does not exist: %s", self.model_path)
            self._is_available = False
            return False

        # Attempt initializing dedicated FaceSwapEngine if ArcFace model is present
        if self.arcface_path and self.arcface_path.exists():
            try:
                from app.services.face_swap.face_swap_engine import (
                    FaceSwapEngine,
                    FaceSwapEngineConfig,
                )
                config = FaceSwapEngineConfig(
                    inswapper_path=self.model_path,
                    arcface_path=self.arcface_path,
                    provider=self.provider,
                    intra_op_num_threads=4,
                )
                engine = FaceSwapEngine(config)
                if engine.initialize():
                    self.engine = engine
                    bundle = engine.loader.get_bundle()
                    self._session = bundle.swap_session
                    self._input_meta = bundle.swap_inputs
                    self._output_meta = bundle.swap_outputs
                    self._is_available = True
                    logger.info(
                        "LicensedFaceSwapModelAdapter initialized with full FaceSwapEngine (%s + %s)",
                        self.model_path.name,
                        self.arcface_path.name,
                    )
                    return True
            except Exception as e:
                logger.warning("Failed to initialize FaceSwapEngine in adapter: %s; falling back to direct session.", e)

        # Fallback to standalone Inswapper session
        try:
            import onnxruntime as ort

            # Verify CPUExecutionProvider is available in the runtime
            available_providers = ort.get_available_providers()
            target_provider = self.provider if self.provider in available_providers else "CPUExecutionProvider"

            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess_options.intra_op_num_threads = 4
            sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

            self._session = ort.InferenceSession(
                str(self.model_path),
                sess_options=sess_options,
                providers=[target_provider],
            )

            # Inspect input tensors
            self._input_meta = []
            for inp in self._session.get_inputs():
                self._input_meta.append({
                    "name": inp.name,
                    "shape": inp.shape,
                    "type": inp.type,
                })

            # Inspect output tensors
            self._output_meta = []
            for out in self._session.get_outputs():
                self._output_meta.append({
                    "name": out.name,
                    "shape": out.shape,
                    "type": out.type,
                })

            self._is_available = True
            logger.info(
                "LicensedFaceSwapModelAdapter successfully loaded %s (Inputs: %s, Provider: %s)",
                self.model_path.name,
                [m["name"] for m in self._input_meta],
                target_provider,
            )
            return True

        except Exception as e:
            logger.exception("Failed to initialize ONNX Runtime session for %s", self.model_path)
            self._session = None
            self._is_available = False
            return False

    def get_or_compute_source_latent(self, replacement_face_bgr: np.ndarray) -> np.ndarray:
        """
        Computes and caches the 512-D identity latent vector from the replacement face image.
        """
        if self.engine is None or not self.engine.is_ready:
            raise RuntimeError("Neural face swap engine is not ready.")

        face_id = id(replacement_face_bgr)
        if self._cached_source_id == face_id and self._cached_source_latent is not None:
            return self._cached_source_latent

        # Detect landmarks on replacement face
        landmarks = self._detect_face_landmarks(replacement_face_bgr)
        latent = self.engine.compute_source_identity(replacement_face_bgr, landmarks)
        self._cached_source_latent = latent
        self._cached_source_id = face_id
        return latent

    def _detect_face_landmarks(self, img_bgr: np.ndarray) -> List[List[float]]:
        """Detects 5 facial landmarks using YuNet or falls back to canonical center landmarks."""
        h, w = img_bgr.shape[:2]
        try:
            from app.core.config import get_settings
            from app.services.face_detector import FaceDetectorYuNet
            settings = get_settings()
            if settings.resolved_yunet_model_path.exists():
                detector = FaceDetectorYuNet(settings.resolved_yunet_model_path)
                dets = detector.detect_in_bgr_frame(img_bgr, 0, 0.0)
                if dets:
                    return dets[0].landmarks
        except Exception as err:
            logger.debug("YuNet landmark detection fallback in adapter: %s", err)

        return [
            [0.3419 * w, 0.4615 * h],
            [0.6565 * w, 0.4598 * h],
            [0.5002 * w, 0.6405 * h],
            [0.3709 * w, 0.8246 * h],
            [0.6315 * w, 0.8232 * h],
        ]

    def validate_inputs(
        self,
        source_aligned: np.ndarray,
        target_face: np.ndarray,
    ) -> bool:
        """Verifies shape, dimensions, and color channels."""
        if source_aligned is None or target_face is None:
            return False
        if not isinstance(source_aligned, np.ndarray) or not isinstance(target_face, np.ndarray):
            return False
        if source_aligned.ndim != 3 or target_face.ndim != 3:
            return False
        if source_aligned.shape[2] != 3 or target_face.shape[2] != 3:
            return False
        if source_aligned.shape[0] < 16 or source_aligned.shape[1] < 16:
            return False
        if target_face.shape[0] < 16 or target_face.shape[1] < 16:
            return False
        return True

    def _preprocess_image(
        self,
        image_bgr: np.ndarray,
        target_size: int,
        layout: str = "NCHW",
        normalize_mode: str = "0_to_1",
    ) -> np.ndarray:
        """Preprocesses image into model-ready float32 tensor."""
        # 1. Resize to target dimension
        resized = cv2.resize(image_bgr, (target_size, target_size), interpolation=cv2.INTER_AREA)

        # 2. BGR -> RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32)

        # 3. Normalization
        if normalize_mode == "-1_to_1":
            norm = (rgb - 127.5) / 127.5
        else:
            norm = rgb / 255.0

        # 4. Transpose layout
        if layout == "NCHW":
            tensor = np.transpose(norm, (2, 0, 1))  # (3, H, W)
            tensor = np.expand_dims(tensor, axis=0)  # (1, 3, H, W)
        else:
            tensor = np.expand_dims(norm, axis=0)  # (1, H, W, 3)

        return tensor.astype(np.float32)

    def _postprocess_output(
        self,
        out_tensor: np.ndarray,
        orig_shape: Tuple[int, int],
    ) -> np.ndarray:
        """Converts model output tensor back to canonical uint8 BGR face canvas."""
        arr = np.asarray(out_tensor)

        # Remove batch dim if present
        if arr.ndim == 4:
            arr = arr[0]

        # Convert NCHW -> HWC if needed
        if arr.ndim == 3 and arr.shape[0] == 3 and arr.shape[2] != 3:
            arr = np.transpose(arr, (1, 2, 0))

        # Denormalize values to [0, 255]
        if np.issubdtype(arr.dtype, np.floating):
            min_val = float(np.min(arr))
            max_val = float(np.max(arr))
            if min_val < -0.1:
                # Scaled in [-1, 1]
                arr = (arr * 127.5) + 127.5
            elif max_val <= 1.5:
                # Scaled in [0, 1]
                arr = arr * 255.0

        arr = np.clip(arr, 0, 255).astype(np.uint8)

        # RGB -> BGR
        if arr.shape[2] == 3:
            arr_bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        else:
            arr_bgr = arr

        # Resize back to target aligned crop size
        target_h, target_w = orig_shape[:2]
        if arr_bgr.shape[0] != target_h or arr_bgr.shape[1] != target_w:
            arr_bgr = cv2.resize(arr_bgr, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

        return arr_bgr

    def swap_face(
        self,
        source_aligned: np.ndarray,
        target_face: np.ndarray,
    ) -> np.ndarray:
        """
        Executes real neural inference via ONNX Runtime CPU.
        """
        if not self.is_available or (self._session is None and (self.engine is None or not self.engine.is_ready)):
            raise ModelNotConfiguredError(
                "Face swap model adapter is not initialized. Ensure model exists and initialize() succeeded."
            )

        if not self.validate_inputs(source_aligned, target_face):
            raise ValueError("Invalid input dimensions or channels supplied to face-swap model.")

        orig_shape = source_aligned.shape[:2]

        # If dedicated FaceSwapEngine is loaded, execute full neural swap with EMAP identity
        if self.engine is not None and self.engine.is_ready:
            source_latent = self.get_or_compute_source_latent(target_face)
            h, w = source_aligned.shape[:2]
            canonical_lm = [
                [0.3419 * w, 0.4615 * h],
                [0.6565 * w, 0.4598 * h],
                [0.5002 * w, 0.6405 * h],
                [0.3709 * w, 0.8246 * h],
                [0.6315 * w, 0.8232 * h],
            ]
            target_crop = self.engine.preprocessor.align_target_face_128(source_aligned, canonical_lm)
            swapped_128 = self.engine.swap_single_face(target_crop, source_latent)
            if swapped_128.shape[:2] != orig_shape:
                swapped_128 = cv2.resize(swapped_128, (orig_shape[1], orig_shape[0]), interpolation=cv2.INTER_LANCZOS4)
            return swapped_128

        # Determine input sizes and layout from model input metadata
        feed_dict: Dict[str, np.ndarray] = {}

        if len(self._input_meta) == 1:
            # Single input model: check channels
            inp_meta = self._input_meta[0]
            inp_shape = inp_meta["shape"]
            # Detect layout
            is_nchw = True
            if len(inp_shape) == 4 and inp_shape[-1] in (3, 6):
                is_nchw = False

            channels = inp_shape[1] if is_nchw and len(inp_shape) == 4 else (inp_shape[-1] if len(inp_shape) == 4 else 3)
            size = self.input_size
            if len(inp_shape) == 4 and isinstance(inp_shape[2 if is_nchw else 1], int):
                size = inp_shape[2 if is_nchw else 1]

            t1 = self._preprocess_image(source_aligned, size, layout="NCHW" if is_nchw else "NHWC")
            if channels == 6:
                t2 = self._preprocess_image(target_face, size, layout="NCHW" if is_nchw else "NHWC")
                cat_axis = 1 if is_nchw else 3
                combined = np.concatenate([t1, t2], axis=cat_axis)
                feed_dict[inp_meta["name"]] = combined
            else:
                feed_dict[inp_meta["name"]] = t1

        elif len(self._input_meta) >= 2:
            # Two inputs (e.g., target video face & source identity face/embedding)
            for inp_meta in self._input_meta:
                name = inp_meta["name"].lower()
                inp_shape = inp_meta["shape"]

                # Check if this input expects a 1D/2D embedding vector (e.g., shape (1, 512))
                if len(inp_shape) == 2 or (len(inp_shape) == 1 and inp_shape[0] > 16):
                    # Identity embedding vector input
                    emb_dim = inp_shape[-1] if isinstance(inp_shape[-1], int) else 512
                    # Create normalized identity vector from target face color features
                    resized_t = cv2.resize(target_face, (32, 32)).flatten().astype(np.float32)
                    emb = resized_t[:emb_dim] if len(resized_t) >= emb_dim else np.pad(resized_t, (0, emb_dim - len(resized_t)))
                    norm_val = np.linalg.norm(emb) + 1e-6
                    emb = (emb / norm_val).reshape(1, emb_dim).astype(np.float32)
                    feed_dict[inp_meta["name"]] = emb
                else:
                    # 4D image input
                    is_nchw = True
                    if len(inp_shape) == 4 and inp_shape[-1] == 3:
                        is_nchw = False
                    size = self.input_size
                    if len(inp_shape) == 4 and isinstance(inp_shape[2 if is_nchw else 1], int):
                        size = inp_shape[2 if is_nchw else 1]

                    # Match name to choose target face vs source_aligned
                    if any(k in name for k in ("src", "source", "id", "identity", "replacement")):
                        img_to_prep = target_face
                    else:
                        img_to_prep = source_aligned

                    feed_dict[inp_meta["name"]] = self._preprocess_image(
                        img_to_prep, size, layout="NCHW" if is_nchw else "NHWC"
                    )

        # Execute ONNX Runtime CPU inference
        output_names = [m["name"] for m in self._output_meta]
        raw_outputs = self._session.run(output_names, feed_dict)

        if not raw_outputs or len(raw_outputs) == 0:
            raise RuntimeError("Face-swap model execution produced empty outputs.")

        result_aligned = self._postprocess_output(raw_outputs[0], orig_shape)
        return result_aligned

    def cleanup(self) -> None:
        """Releases session handles and buffers."""
        self._session = None
        self._is_available = False


def get_face_swap_model_adapter() -> BaseFaceSwapModelAdapter:
    """
    Dependency provider returning the active model adapter.
    If FACE_SWAP_ENABLED is True and a valid licensed model exists,
    returns an initialized LicensedFaceSwapModelAdapter.
    Otherwise returns UnconfiguredFaceSwapModelAdapter.
    """
    try:
        from app.core.config import get_settings
        settings = get_settings()
        if settings.FACE_SWAP_ENABLED and settings.resolved_face_swap_model_path:
            model_path = settings.resolved_face_swap_model_path
            arcface_path = settings.resolved_arcface_model_path
            if model_path.exists():
                adapter = LicensedFaceSwapModelAdapter(
                    model_path=model_path,
                    arcface_path=arcface_path,
                    license_name=settings.FACE_SWAP_MODEL_LICENSE,
                    provider=settings.FACE_SWAP_PROVIDER,
                    input_size=settings.FACE_SWAP_INPUT_SIZE,
                )
                if adapter.initialize():
                    return adapter
                logger.warning(
                    "LicensedFaceSwapModelAdapter initialization failed for %s; falling back to UnconfiguredFaceSwapModelAdapter.",
                    model_path,
                )
    except Exception as e:
        logger.warning("Could not instantiate LicensedFaceSwapModelAdapter: %s", e)

    return UnconfiguredFaceSwapModelAdapter()
