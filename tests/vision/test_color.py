"""Tests for vision.color — HSV color region detection and color ratio.

All tests use synthetically generated NumPy arrays; no real game assets needed.
A saturated red square is embedded in a white background so the HSV bounds
are predictable and stable.
"""
from __future__ import annotations

import numpy as np
import pytest

from anime_game_afk.core.types import Rect
from anime_game_afk.vision.color import color_ratio, find_color_regions

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
# find_color_regions
# ---------------------------------------------------------------------------


def test_find_color_regions_single_red_square() -> None:
    """A single red rectangle on white returns exactly one bounding rect."""
    img = _make_red_on_white(rect_x=20, rect_y=30, rect_w=40, rect_h=50)
    results = find_color_regions(img, _RED_HSV_LOW, _RED_HSV_HIGH, min_area=1)
    assert len(results) == 1
    r = results[0]
    assert r.x == 20
    assert r.y == 30
    assert r.w == 40
    assert r.h == 50


def test_find_color_regions_two_separate_red_rects() -> None:
    """Two non-overlapping red rectangles yield two separate results."""
    img = np.full((_IMG_H, _IMG_W, 3), _WHITE_BGR, dtype=np.uint8)
    img[10:30, 10:40] = _RED_BGR   # rect A
    img[100:120, 100:140] = _RED_BGR  # rect B
    results = find_color_regions(img, _RED_HSV_LOW, _RED_HSV_HIGH, min_area=1)
    assert len(results) == 2


def test_find_color_regions_no_matching_color_returns_empty() -> None:
    """All-white image has no red pixels; result should be empty."""
    img = np.full((_IMG_H, _IMG_W, 3), _WHITE_BGR, dtype=np.uint8)
    results = find_color_regions(img, _RED_HSV_LOW, _RED_HSV_HIGH, min_area=1)
    assert results == []


def test_find_color_regions_min_area_filters_tiny_regions() -> None:
    """Regions whose area is below min_area are excluded."""
    img = np.full((_IMG_H, _IMG_W, 3), _WHITE_BGR, dtype=np.uint8)
    img[5:8, 5:8] = _RED_BGR       # 3×3 = area 9 — tiny
    img[50:90, 50:100] = _RED_BGR  # 50×40 = area 2000 — large
    results = find_color_regions(img, _RED_HSV_LOW, _RED_HSV_HIGH, min_area=100)
    assert len(results) == 1
    assert results[0].w * results[0].h >= 100


def test_find_color_regions_returns_rect_objects() -> None:
    """Each element in the result list is a Rect."""
    img = _make_red_on_white(rect_x=10, rect_y=10, rect_w=20, rect_h=20)
    results = find_color_regions(img, _RED_HSV_LOW, _RED_HSV_HIGH, min_area=1)
    assert len(results) >= 1
    for r in results:
        assert isinstance(r, Rect)


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
