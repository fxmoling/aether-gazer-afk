"""Tests for vision.matcher — template matching utilities.

All tests use synthetically generated NumPy arrays, so no real game assets
are required.  A cross-shaped template is embedded at known positions in a
uniform-grey background; cv2.TM_CCOEFF_NORMED reliably finds it.
"""
from __future__ import annotations

import numpy as np
import pytest

from anime_game_afk.core.types import Rect
from anime_game_afk.vision.matcher import match_all, match_best, match_template
from anime_game_afk.vision.types import MatchResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BG_VALUE = 64      # uniform grey background pixel value
_FG_VALUE = 200     # cross-arm pixel value
_TMPL_SIZE = 20     # template is TMPL_SIZE × TMPL_SIZE
_IMG_SIZE = 200     # square image side length


def _make_template() -> np.ndarray:
    """Return a 20×20 greyscale cross pattern on a dark background."""
    tmpl = np.full((_TMPL_SIZE, _TMPL_SIZE), _BG_VALUE, dtype=np.uint8)
    # Horizontal bar (rows 8–11, all cols)
    tmpl[8:12, :] = _FG_VALUE
    # Vertical bar (rows all, cols 8–11)
    tmpl[:, 8:12] = _FG_VALUE
    return tmpl


def _make_image(*positions: tuple[int, int]) -> np.ndarray:
    """Return a 200×200 greyscale image with the cross embedded at each (x, y)."""
    img = np.full((_IMG_SIZE, _IMG_SIZE), _BG_VALUE, dtype=np.uint8)
    tmpl = _make_template()
    for px, py in positions:
        img[py : py + _TMPL_SIZE, px : px + _TMPL_SIZE] = tmpl
    return img


# ---------------------------------------------------------------------------
# match_template — basic detection
# ---------------------------------------------------------------------------


def test_match_template_finds_cross_at_known_position() -> None:
    """match_template should locate the cross at the exact embedding position."""
    embed_x, embed_y = 30, 40
    img = _make_image((embed_x, embed_y))
    tmpl = _make_template()

    result = match_template(img, tmpl, threshold=0.9)

    assert result.matched is True
    assert result.score >= 0.9
    assert result.x == embed_x
    assert result.y == embed_y
    assert result.w == _TMPL_SIZE
    assert result.h == _TMPL_SIZE


def test_match_template_returns_match_result_type() -> None:
    img = _make_image((50, 50))
    tmpl = _make_template()
    result = match_template(img, tmpl)
    assert isinstance(result, MatchResult)


def test_match_template_no_match_below_threshold() -> None:
    """A blank image should yield a low score and matched=False."""
    img = np.full((_IMG_SIZE, _IMG_SIZE), _BG_VALUE, dtype=np.uint8)
    tmpl = _make_template()

    result = match_template(img, tmpl, threshold=0.9)

    assert result.matched is False
    assert result.score < 0.9


def test_match_template_with_region_finds_cross_inside() -> None:
    """Region search should find the cross when it lies fully inside the region."""
    embed_x, embed_y = 50, 50
    img = _make_image((embed_x, embed_y))
    tmpl = _make_template()
    region = Rect(x=30, y=30, w=80, h=80)

    result = match_template(img, tmpl, region=region, threshold=0.9)

    assert result.matched is True
    # Coordinates must be in full-image space.
    assert result.x == embed_x
    assert result.y == embed_y


def test_match_template_with_region_misses_cross_outside() -> None:
    """Region search should not find the cross when it lies outside the region."""
    embed_x, embed_y = 150, 150
    img = _make_image((embed_x, embed_y))
    tmpl = _make_template()
    # Region covers only top-left 100×100 — cross is at (150,150).
    region = Rect(x=0, y=0, w=100, h=100)

    result = match_template(img, tmpl, region=region, threshold=0.9)

    assert result.matched is False


def test_match_template_template_larger_than_image_returns_no_match() -> None:
    """When the template is bigger than the image, return a no-match sentinel."""
    small_img = np.zeros((10, 10), dtype=np.uint8)
    large_tmpl = np.ones((20, 20), dtype=np.uint8)

    result = match_template(small_img, large_tmpl)

    assert result.matched is False
    assert result.score == 0.0


def test_match_template_template_larger_than_region_returns_no_match() -> None:
    img = _make_image((10, 10))
    tmpl = _make_template()
    # Region is 10×10, template is 20×20.
    tiny_region = Rect(x=0, y=0, w=10, h=10)

    result = match_template(img, tmpl, region=tiny_region)

    assert result.matched is False


def test_match_template_score_is_high_for_perfect_match() -> None:
    """Embedding the template verbatim should yield a near-perfect score."""
    tmpl = _make_template()
    # Image that is exactly the template, so score == 1.0.
    img = tmpl.copy()

    result = match_template(img, tmpl)

    assert result.score > 0.99


# ---------------------------------------------------------------------------
# match_best — multiple templates
# ---------------------------------------------------------------------------


def test_match_best_selects_highest_scoring_template() -> None:
    """match_best should prefer the template that actually matches."""
    embed_x, embed_y = 60, 60
    img = _make_image((embed_x, embed_y))
    good_tmpl = _make_template()
    # Noise template — random, unlikely to match well.
    rng = np.random.default_rng(seed=42)
    noise_tmpl = rng.integers(0, 256, (_TMPL_SIZE, _TMPL_SIZE), dtype=np.uint8)

    result = match_best(img, [noise_tmpl, good_tmpl], threshold=0.9)

    assert result.matched is True
    assert result.score >= 0.9


def test_match_best_empty_template_list() -> None:
    img = _make_image((30, 30))
    result = match_best(img, [])
    assert result.matched is False
    assert result.score == 0.0


def test_match_best_single_template_same_as_match_template() -> None:
    embed_x, embed_y = 40, 40
    img = _make_image((embed_x, embed_y))
    tmpl = _make_template()

    single = match_template(img, tmpl, threshold=0.9)
    best = match_best(img, [tmpl], threshold=0.9)

    assert best.x == single.x
    assert best.y == single.y
    assert abs(best.score - single.score) < 1e-6


def test_match_best_with_region() -> None:
    embed_x, embed_y = 50, 50
    img = _make_image((embed_x, embed_y))
    tmpl = _make_template()
    region = Rect(x=40, y=40, w=60, h=60)

    result = match_best(img, [tmpl], region=region, threshold=0.9)

    assert result.matched is True
    assert result.x == embed_x
    assert result.y == embed_y


# ---------------------------------------------------------------------------
# match_all — multiple occurrences + NMS
# ---------------------------------------------------------------------------


def test_match_all_finds_single_cross() -> None:
    embed_x, embed_y = 50, 50
    img = _make_image((embed_x, embed_y))
    tmpl = _make_template()

    results = match_all(img, tmpl, threshold=0.9)

    assert len(results) == 1
    assert results[0].x == embed_x
    assert results[0].y == embed_y


def test_match_all_finds_two_non_overlapping_crosses() -> None:
    """Two well-separated crosses should both be found."""
    pos_a = (10, 10)
    pos_b = (130, 130)
    img = _make_image(pos_a, pos_b)
    tmpl = _make_template()

    results = match_all(img, tmpl, threshold=0.9)

    assert len(results) == 2
    xs = {r.x for r in results}
    assert 10 in xs
    assert 130 in xs


def test_match_all_nms_collapses_adjacent_hits() -> None:
    """A single template embedding produces a cluster of high-score pixels.

    NMS should reduce that cluster to a single result.
    """
    img = _make_image((60, 60))
    tmpl = _make_template()

    results = match_all(img, tmpl, threshold=0.9)

    # Should be exactly one match after NMS, not a flood of adjacent pixels.
    assert len(results) == 1


def test_match_all_empty_image_no_matches() -> None:
    img = np.full((_IMG_SIZE, _IMG_SIZE), _BG_VALUE, dtype=np.uint8)
    tmpl = _make_template()

    results = match_all(img, tmpl, threshold=0.9)

    assert results == []


def test_match_all_high_threshold_no_matches() -> None:
    img = _make_image((50, 50))
    tmpl = _make_template()

    # Threshold above 1.0 — nothing can match.
    results = match_all(img, tmpl, threshold=1.01)

    assert results == []


def test_match_all_with_region_finds_only_cross_inside_region() -> None:
    """Cross outside the region must not appear in results."""
    inside = (20, 20)
    outside = (150, 150)
    img = _make_image(inside, outside)
    tmpl = _make_template()
    region = Rect(x=0, y=0, w=80, h=80)

    results = match_all(img, tmpl, threshold=0.9, region=region)

    assert len(results) == 1
    assert results[0].x == inside[0]
    assert results[0].y == inside[1]


def test_match_all_returns_list_of_match_result() -> None:
    img = _make_image((40, 40))
    tmpl = _make_template()

    results = match_all(img, tmpl, threshold=0.9)

    assert isinstance(results, list)
    for r in results:
        assert isinstance(r, MatchResult)


def test_match_all_results_are_sorted_by_score_descending() -> None:
    """Kept results should be ordered best-first (NMS preserves this)."""
    pos_a = (10, 10)
    pos_b = (130, 10)
    img = _make_image(pos_a, pos_b)
    tmpl = _make_template()

    results = match_all(img, tmpl, threshold=0.9)

    assert len(results) >= 2
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# _overlaps (indirectly tested via match_all)
# ---------------------------------------------------------------------------


def test_match_all_three_crosses_three_results() -> None:
    """Three well-separated crosses should each survive NMS."""
    pos_a = (10, 10)
    pos_b = (80, 10)
    pos_c = (150, 10)
    img = _make_image(pos_a, pos_b, pos_c)
    tmpl = _make_template()

    results = match_all(img, tmpl, threshold=0.9)

    assert len(results) == 3
