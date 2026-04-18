"""HSV color detection utilities.

Pure functions for identifying pixel ratios by HSV color range.
No state, no side effects.
"""
from __future__ import annotations

import cv2
import numpy as np

from anime_game_afk.core.types import Rect


def color_ratio(
    image: np.ndarray,
    hsv_low: tuple[int, int, int],
    hsv_high: tuple[int, int, int],
    region: Rect | None = None,
) -> float:
    """Calculate the fraction of pixels matching an HSV color range.

    Args:
        image: BGR source image.
        hsv_low: Lower HSV bound as (H, S, V).
        hsv_high: Upper HSV bound as (H, S, V).
        region: Optional sub-region to analyse. When provided, only pixels
                inside the rectangle are considered.

    Returns:
        Float in [0.0, 1.0] — ratio of matching pixels to total pixels.
        Returns 0.0 for an empty region.
    """
    if region is not None:
        from anime_game_afk.vision.geometry import crop  # local import avoids circular deps
        image = crop(image, region)

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(hsv_low, dtype=np.uint8), np.array(hsv_high, dtype=np.uint8))

    total = mask.size
    if total == 0:
        return 0.0
    return float(np.count_nonzero(mask)) / total
