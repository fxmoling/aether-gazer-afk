"""Tests for vision.color — HSV color region detection and color ratio.

All tests use synthetically generated NumPy arrays; no real game assets needed.
A saturated red square is embedded in a white background so the HSV bounds
are predictable and stable.
"""
from __future__ import annotations

import numpy as np
import pytest

from anime_game_afk.core.types import Rect
from anime_game_afk.vision.color import color_ratio

# ---------------------------------------------------------------------------
# Colour constants
# ---------------------------------------------------------------------------

# Pure red in BGR (B=0, G=0, R=255).
# In OpenCV HSV: H≈0, S=255, V=255.
_RED_BGR = (0, 0, 255)
_WHITE_BGR = (255, 255, 255)

# HSV range that captures pure red (hue 0 ± a small margin).
_RED_HSV_LOW = (0, 200, 200)
_RED_HSV_HIGH = (5, 255, 255)

_IMG_W = 200
_IMG_H = 200


def _make_red_on_white(
    rect_x: int,
    rect_y: int,
    rect_w: int,
    rect_h: int,
    img_h: int = _IMG_H,
    img_w: int = _IMG_W,
) -> np.ndarray:
    """Return a BGR image with a red rectangle on a white background."""
    img = np.full((img_h, img_w, 3), _WHITE_BGR, dtype=np.uint8)
    img[rect_y : rect_y + rect_h, rect_x : rect_x + rect_w] = _RED_BGR
    return img


# ---------------------------------------------------------------------------
# color_ratio
# ---------------------------------------------------------------------------


def test_color_ratio_all_red_image_returns_one() -> None:
    """Solid red image returns ratio ≈ 1.0."""
    img = np.full((_IMG_H, _IMG_W, 3), _RED_BGR, dtype=np.uint8)
    ratio = color_ratio(img, _RED_HSV_LOW, _RED_HSV_HIGH)
    assert ratio == pytest.approx(1.0, abs=0.01)


def test_color_ratio_all_white_image_returns_zero() -> None:
    """Solid white image contains no red pixels → ratio = 0.0."""
    img = np.full((_IMG_H, _IMG_W, 3), _WHITE_BGR, dtype=np.uint8)
    ratio = color_ratio(img, _RED_HSV_LOW, _RED_HSV_HIGH)
    assert ratio == pytest.approx(0.0, abs=0.01)


def test_color_ratio_known_fraction() -> None:
    """A red square occupying half the image returns ratio ≈ 0.5."""
    img = np.full((_IMG_H, _IMG_W, 3), _WHITE_BGR, dtype=np.uint8)
    # Paint exactly the left half red.
    half = _IMG_W // 2
    img[:, :half] = _RED_BGR
    ratio = color_ratio(img, _RED_HSV_LOW, _RED_HSV_HIGH)
    assert ratio == pytest.approx(0.5, abs=0.02)


def test_color_ratio_with_region_isolates_sub_area() -> None:
    """color_ratio with region only counts pixels inside the region."""
    img = np.full((_IMG_H, _IMG_W, 3), _WHITE_BGR, dtype=np.uint8)
    # Red square at (50, 50, 40×40).
    img[50:90, 50:90] = _RED_BGR
    # Region that exactly covers the red square.
    region = Rect(x=50, y=50, w=40, h=40)
    ratio = color_ratio(img, _RED_HSV_LOW, _RED_HSV_HIGH, region=region)
    assert ratio == pytest.approx(1.0, abs=0.01)


def test_color_ratio_with_region_outside_colored_area_returns_zero() -> None:
    """A region that does not overlap the red area returns 0."""
    img = _make_red_on_white(rect_x=100, rect_y=100, rect_w=50, rect_h=50)
    region = Rect(x=0, y=0, w=50, h=50)  # top-left, no red here
    ratio = color_ratio(img, _RED_HSV_LOW, _RED_HSV_HIGH, region=region)
    assert ratio == pytest.approx(0.0, abs=0.01)


def test_color_ratio_returns_float() -> None:
    img = _make_red_on_white(rect_x=10, rect_y=10, rect_w=20, rect_h=20)
    ratio = color_ratio(img, _RED_HSV_LOW, _RED_HSV_HIGH)
    assert isinstance(ratio, float)


def test_color_ratio_value_in_range() -> None:
    """color_ratio always returns a value in [0.0, 1.0]."""
    img = _make_red_on_white(rect_x=50, rect_y=50, rect_w=50, rect_h=50)
    ratio = color_ratio(img, _RED_HSV_LOW, _RED_HSV_HIGH)
    assert 0.0 <= ratio <= 1.0
