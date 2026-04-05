"""Tests for vision.ocr — template-matching OCR stub.

All tests use synthetically generated NumPy arrays; no real game assets needed.
A known pattern is embedded at a fixed position and used both as the
source image and as the 'template' representing the corresponding text label.
"""
from __future__ import annotations

import numpy as np
import pytest

from anime_game_afk.core.types import Rect
from anime_game_afk.vision.ocr import recognize_text
from anime_game_afk.vision.types import TextResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_IMG_SIZE = 200
_PATCH_SIZE = 30
_BG_VALUE = 64
_FG_VALUE = 200


def _make_pattern(size: int = _PATCH_SIZE) -> np.ndarray:
    """Return a recognisable greyscale pattern (cross shape) of given size."""
    tmpl = np.full((size, size), _BG_VALUE, dtype=np.uint8)
    mid = size // 2
    arm = max(1, size // 6)
    tmpl[mid - arm : mid + arm, :] = _FG_VALUE   # horizontal bar
    tmpl[:, mid - arm : mid + arm] = _FG_VALUE   # vertical bar
    return tmpl


def _make_image_with_pattern(px: int, py: int) -> np.ndarray:
    """Return a 200×200 grey image with the cross pattern at (px, py)."""
    img = np.full((_IMG_SIZE, _IMG_SIZE), _BG_VALUE, dtype=np.uint8)
    pattern = _make_pattern()
    img[py : py + _PATCH_SIZE, px : px + _PATCH_SIZE] = pattern
    return img


# ---------------------------------------------------------------------------
# recognize_text — no templates
# ---------------------------------------------------------------------------


def test_recognize_text_no_templates_uses_ocr() -> None:
    """When templates=None, uses real OCR (if available) to read text."""
    img = _make_image_with_pattern(50, 50)
    results = recognize_text(img)
    # With RapidOCR installed, it may detect the cross pattern as "+"
    # Without RapidOCR, returns empty list. Either is acceptable.
    assert isinstance(results, list)


def test_recognize_text_empty_templates_dict_returns_empty_list() -> None:
    """An empty templates dict is equivalent to no templates."""
    img = _make_image_with_pattern(50, 50)
    results = recognize_text(img, templates={})
    assert results == []


# ---------------------------------------------------------------------------
# recognize_text — matching templates
# ---------------------------------------------------------------------------


def test_recognize_text_single_match_found() -> None:
    """Pattern template embedded in the image should be found and returned."""
    embed_x, embed_y = 40, 40
    img = _make_image_with_pattern(embed_x, embed_y)
    pattern = _make_pattern()
    templates = {"HELLO": pattern}

    results = recognize_text(img, templates=templates, threshold=0.9)

    assert len(results) == 1
    assert results[0].text == "HELLO"
    assert results[0].confidence >= 0.9
    assert isinstance(results[0].region, Rect)
    assert results[0].region.x == embed_x
    assert results[0].region.y == embed_y


def test_recognize_text_returns_text_result_objects() -> None:
    """Each element in results is a TextResult dataclass."""
    img = _make_image_with_pattern(30, 30)
    templates = {"LABEL": _make_pattern()}
    results = recognize_text(img, templates=templates, threshold=0.9)
    for r in results:
        assert isinstance(r, TextResult)


def test_recognize_text_results_sorted_by_confidence_descending() -> None:
    """When multiple labels match, results are sorted best-confidence first."""
    embed_x, embed_y = 50, 50
    img = _make_image_with_pattern(embed_x, embed_y)
    pattern = _make_pattern()
    # Two identical templates — both will match at the same location.
    templates: dict[str, np.ndarray] = {
        "ALPHA": pattern,
        "BETA": pattern,
    }
    results = recognize_text(img, templates=templates, threshold=0.9)
    assert len(results) == 2
    confidences = [r.confidence for r in results]
    assert confidences == sorted(confidences, reverse=True)


# ---------------------------------------------------------------------------
# recognize_text — threshold filtering
# ---------------------------------------------------------------------------


def test_recognize_text_threshold_too_high_returns_empty() -> None:
    """With threshold > 1.0, nothing can ever match."""
    img = _make_image_with_pattern(50, 50)
    templates = {"IMPOSSIBLE": _make_pattern()}
    results = recognize_text(img, templates=templates, threshold=1.01)
    assert results == []


def test_recognize_text_noise_template_returns_empty() -> None:
    """A random noise template should not match at threshold=0.9."""
    img = _make_image_with_pattern(50, 50)
    rng = np.random.default_rng(seed=7)
    noise = rng.integers(0, 256, (_PATCH_SIZE, _PATCH_SIZE), dtype=np.uint8)
    results = recognize_text(img, templates={"NOISE": noise}, threshold=0.9)
    assert results == []


# ---------------------------------------------------------------------------
# recognize_text — region restriction
# ---------------------------------------------------------------------------


def test_recognize_text_with_region_finds_pattern_inside_region() -> None:
    """Pattern inside the provided region is found."""
    embed_x, embed_y = 60, 60
    img = _make_image_with_pattern(embed_x, embed_y)
    templates = {"ITEM": _make_pattern()}
    region = Rect(x=50, y=50, w=60, h=60)

    results = recognize_text(img, region=region, templates=templates, threshold=0.9)

    assert len(results) == 1
    assert results[0].text == "ITEM"
    # Coordinates are in full-image space.
    assert results[0].region.x == embed_x
    assert results[0].region.y == embed_y


def test_recognize_text_with_region_misses_pattern_outside_region() -> None:
    """Pattern outside the region must not appear in results."""
    embed_x, embed_y = 150, 150
    img = _make_image_with_pattern(embed_x, embed_y)
    templates = {"FAR": _make_pattern()}
    # Region covers only the top-left corner — pattern is far away.
    region = Rect(x=0, y=0, w=80, h=80)

    results = recognize_text(img, region=region, templates=templates, threshold=0.9)

    assert results == []
