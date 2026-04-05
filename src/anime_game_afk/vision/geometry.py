"""Image geometry utilities — crop, resize, contour detection.

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


def find_contours(
    image: np.ndarray,
    min_area: int = 100,
) -> list[Rect]:
    """Find external contours in a greyscale or binary image.

    Converts to greyscale if needed, applies a 127-threshold, then locates
    external contours via ``cv2.RETR_EXTERNAL``.

    Args:
        image: Greyscale or BGR image.
        min_area: Minimum bounding-box area (w*h) to include in results.

    Returns:
        List of bounding :class:`Rect` objects for each qualifying contour.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rects: list[Rect] = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w * h >= min_area:
            rects.append(Rect(x, y, w, h))
    return rects
