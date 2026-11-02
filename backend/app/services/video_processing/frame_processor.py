"""
Deprecated FrameProcessor placeholder.
Face replacement is now handled natively and multithreaded by FaceFusion 3.9.2.
"""
from typing import Tuple, Optional, Any
import numpy as np


class FrameProcessor:
    def __init__(self, *args, **kwargs):
        pass

    def process_frame(
        self,
        frame_bgr: np.ndarray,
        target_face_bgr: np.ndarray,
        landmarks: Optional[Any] = None,
        bounding_box: Optional[Tuple[int, int, int, int]] = None,
        diagnostic_mode: bool = False,
    ) -> Tuple[np.ndarray, bool]:
        # Legacy pass-through
        return frame_bgr, False
