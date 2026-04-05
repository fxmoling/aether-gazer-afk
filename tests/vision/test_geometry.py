"""Tests for vision.geometry — crop, resize, find_contours.

All tests use synthetically generated NumPy arrays; no real game assets needed.
"""
from __future__ import annotations

import numpy as np
import pytest

from anime_game_afk.core.types import Rect
from anime_game_afk.vision.geometry import crop, find_contours, resize

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_IMG_W = 100
_IMG_H = 80


def _solid(value: int, h: int = _IMG_H, w: int = _IMG_W) -> np.ndarray:
    """Return a solid-colour greyscale image."""
    return np.full((h, w), value, dtype=np.uint8)


# ---------------------------------------------------------------------------
# crop
# ---------------------------------------------------------------------------


def test_crop_within_bounds_returns_correct_shape() -> None:
    """Cropping a region fully inside the image returns the exact region size."""
    img = _solid(128)
    region = Rect(x=10, y=5, w=30, h=20)
    result = crop(img, region)
    assert result.shape == (20, 30)


def test_crop_within_bounds_returns_correct_pixels() -> None:
    """Cropped pixels match the source at the same coordinates."""
    img = np.arange(_IMG_H * _IMG_W, dtype=np.uint8).reshape(_IMG_H, _IMG_W)
    region = Rect(x=5, y=3, w=10, h=7)
    result = crop(img, region)
    expected = img[3:10, 5:15]
    np.testing.assert_array_equal(result, expected)


def test_crop_returns_copy_not_view() -> None:
    """Modifying the cropped result must not affect the original image."""
    img = _solid(50)
    region = Rect(x=0, y=0, w=10, h=10)
    cropped = crop(img, region)
    cropped[:] = 255
    assert img[0, 0] == 50  # original unchanged


def test_crop_clamped_when_region_extends_past_right_edge() -> None:
    """Region extending beyond the right edge is clamped to image width."""
    img = _solid(64)
    region = Rect(x=90, y=0, w=50, h=10)  # x2 = 140 > 100
    result = crop(img, region)
    assert result.shape[1] == 10  # clamped width: 100 - 90


def test_crop_clamped_when_region_extends_past_bottom_edge() -> None:
    """Region extending below the image is clamped to image height."""
    img = _solid(64)
    region = Rect(x=0, y=70, w=20, h=50)  # y2 = 120 > 80
    result = crop(img, region)
    assert result.shape[0] == 10  # clamped height: 80 - 70


def test_crop_negative_origin_clamped_to_zero() -> None:
    """Negative x/y is clamped to 0 so no out-of-bounds indexing occurs."""
    img = _solid(32)
    region = Rect(x=-10, y=-5, w=40, h=30)
    result = crop(img, region)
    # After clamping: x1=0, y1=0, x2=30, y2=25
    assert result.shape == (25, 30)


def test_crop_full_image_returns_equal_array() -> None:
    """Cropping with a region equal to the whole image returns an identical array."""
    img = np.random.default_rng(0).integers(0, 256, (_IMG_H, _IMG_W), dtype=np.uint8)
    region = Rect(x=0, y=0, w=_IMG_W, h=_IMG_H)
    result = crop(img, region)
    np.testing.assert_array_equal(result, img)


def test_crop_works_on_three_channel_image() -> None:
    """crop handles BGR images (3-channel) correctly."""
    img = np.zeros((_IMG_H, _IMG_W, 3), dtype=np.uint8)
    img[10:20, 10:20] = (0, 0, 255)  # red square
    region = Rect(x=5, y=5, w=20, h=20)
    result = crop(img, region)
    assert result.shape == (20, 20, 3)


# ---------------------------------------------------------------------------
# resize
# ---------------------------------------------------------------------------


def test_resize_up_returns_correct_shape() -> None:
    """resize to a larger size returns the requested dimensions."""
    img = _solid(128, h=10, w=10)
    result = resize(img, width=50, height=40)
    assert result.shape == (40, 50)


def test_resize_down_returns_correct_shape() -> None:
    """resize to a smaller size returns the requested dimensions."""
    img = _solid(200)
    result = resize(img, width=20, height=16)
    assert result.shape == (16, 20)


def test_resize_to_same_size_preserves_shape() -> None:
    img = _solid(100)
    result = resize(img, width=_IMG_W, height=_IMG_H)
    assert result.shape == (_IMG_H, _IMG_W)


def test_resize_three_channel_image() -> None:
    """resize handles BGR images."""
    img = np.zeros((_IMG_H, _IMG_W, 3), dtype=np.uint8)
    result = resize(img, width=50, height=40)
    assert result.shape == (40, 50, 3)


# ---------------------------------------------------------------------------
# find_contours
# ---------------------------------------------------------------------------


def _image_with_white_rect(
    x: int, y: int, w: int, h: int, img_h: int = 200, img_w: int = 200
) -> np.ndarray:
    """Return a black greyscale image with a white filled rectangle."""
    img = np.zeros((img_h, img_w), dtype=np.uint8)
    img[y : y + h, x : x + w] = 255
    return img


def test_find_contours_single_rect() -> None:
    """A single white rectangle on a black background yields one Rect."""
    img = _image_with_white_rect(x=10, y=20, w=30, h=40)
    results = find_contours(img, min_area=1)
    assert len(results) == 1
    r = results[0]
    assert r.x == 10
    assert r.y == 20
    assert r.w == 30
    assert r.h == 40


def test_find_contours_two_separate_rects() -> None:
    """Two non-overlapping rectangles yield two separate Rect objects."""
    img = np.zeros((200, 200), dtype=np.uint8)
    img[10:30, 10:40] = 255   # rect A: w=30, h=20
    img[100:140, 100:160] = 255  # rect B: w=60, h=40
    results = find_contours(img, min_area=1)
    assert len(results) == 2


def test_find_contours_min_area_filters_small_rects() -> None:
    """Rectangles whose bounding-box area is below min_area are excluded."""
    img = np.zeros((200, 200), dtype=np.uint8)
    img[5:10, 5:10] = 255    # 5×5 = area 25 — below threshold
    img[50:80, 50:90] = 255  # 40×30 = area 1200 — above threshold
    results = find_contours(img, min_area=100)
    assert len(results) == 1
    r = results[0]
    assert r.w * r.h >= 100


def test_find_contours_empty_image_returns_empty_list() -> None:
    """All-black image has no contours."""
    img = np.zeros((100, 100), dtype=np.uint8)
    results = find_contours(img, min_area=1)
    assert results == []


def test_find_contours_bgr_image_converted_to_grey() -> None:
    """find_contours accepts a 3-channel BGR image."""
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    img[20:50, 20:60] = (255, 255, 255)  # white rectangle
    results = find_contours(img, min_area=1)
    assert len(results) == 1
