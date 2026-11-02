"""
Model Adapter for FaceFusion Engine (Replaces legacy experimental InsightFace adapters).
Provides compatibility interfaces for existing schemas and status queries.
"""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("bollyswap.model_adapter")


class ModelNotConfiguredError(Exception):
    def __init__(self, message: str = "FaceFusion model is not configured", error_code: str = "MODEL_NOT_CONFIGURED"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class BaseFaceSwapModelAdapter:
    """FaceFusion engine adapter interface."""

    def __init__(self):
        self.name = "FaceFusion 3.9.2 (Ghost 256)"
        self.model_type = "ghost_1_256"
        self.license = "Apache-2.0"
        self.execution_provider = "CPUExecutionProvider"

    @property
    def is_available(self) -> bool:
        from app.services.facefusion_engine import get_facefusion_engine
        return get_facefusion_engine().get_status()["ready"]

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "engine": "FaceFusion",
            "version": "3.9.2",
            "model_type": self.model_type,
            "license": self.license,
            "execution_provider": self.execution_provider,
            "is_available": self.is_available,
        }


class UnconfiguredFaceSwapModelAdapter(BaseFaceSwapModelAdapter):
    """Fallback when FaceFusion engine is missing."""
    pass


_adapter_instance: Optional[BaseFaceSwapModelAdapter] = None


def get_face_swap_model_adapter() -> BaseFaceSwapModelAdapter:
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = BaseFaceSwapModelAdapter()
    return _adapter_instance


def reset_face_swap_model_adapter() -> None:
    global _adapter_instance
    _adapter_instance = None
