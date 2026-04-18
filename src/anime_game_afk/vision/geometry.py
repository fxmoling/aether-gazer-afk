"""Image geometry utilities — crop, resize.

Pure functions. No state, no side effects.
"""
from __future__ import annotations

import cv2
import numpy as np

from anime_game_afk.core.types import Rect


def crop(image: np.ndarray, region: Rect) -> np.ndarray:
    """Crop image to the given region. Clamps coordinates to image bounds.

    Args:
        image: Source image (any channel count).
        region: Rectangle to crop.

    Returns:
        A copy of the cropped sub-image.
    """
    h, w = image.shape[:2]
    x1 = max(0, region.x)
    y1 = max(0, region.y)
    x2 = min(w, region.x2)
    y2 = min(h, region.y2)
    return image[y1:y2, x1:x2].copy()


def resize(image: np.ndarray, width: int, height: int) -> np.ndarray:
    """Resize image to target dimensions using area interpolation.

    Args:
        image: Source image.
        width: Target width in pixels.
        height: Target height in pixels.

    Returns:
        Resized image.
    """
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
