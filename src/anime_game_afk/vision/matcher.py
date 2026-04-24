"""Template matching utilities.

Pure functions wrapping cv2.matchTemplate.  No state, no side effects.
All coordinates are in the source-image space (offsets applied automatically
when a ``region`` argument is given).

Scoring convention: higher score = better match, regardless of cv2 method.
For SQDIFF variants the raw distance is inverted (score = 1 - raw_value) so
callers always compare against a consistent threshold in [0, 1].
"""
from __future__ import annotations

import time

import cv2
import numpy as np
from loguru import logger

from anime_game_afk.core.types import Rect
from anime_game_afk.vision.types import MatchResult

# cv2 methods where the *minimum* location is the best match.
_MIN_IS_BEST: frozenset[int] = frozenset({cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED})

# A zero-score sentinel for cases where matching cannot proceed.
# Use _no_match() factory to avoid returning a shared mutable instance.
def _no_match() -> MatchResult:
    """Return a fresh zero-score unmatched result."""
    return MatchResult(score=0.0, x=0, y=0, w=0, h=0, matched=False)


def _best_from_result(
    result: np.ndarray,
    method: int,
    template_w: int,
    template_h: int,
    offset_x: int,
    offset_y: int,
    threshold: float,
) -> MatchResult:
    """Extract the single best match from a cv2.matchTemplate result map."""
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    if method in _MIN_IS_BEST:
        score = float(1.0 - min_val)
        loc = min_loc
    else:
        score = float(max_val)
        loc = max_loc
    x = int(loc[0]) + offset_x
    y = int(loc[1]) + offset_y
    return MatchResult(
        score=score,
        x=x,
        y=y,
        w=template_w,
        h=template_h,
        matched=score >= threshold,
    )


def match_template(
    image: np.ndarray,
    template: np.ndarray,
    region: Rect | None = None,
    method: int = cv2.TM_CCOEFF_NORMED,
    threshold: float = 0.7,
    mask: np.ndarray | None = None,
) -> MatchResult:
    """Match a single template against an image.

    If *region* is provided, only the pixels within that rectangle are
    searched.  The returned coordinates are always in full-image space.

    If *mask* is provided, only the masked pixels contribute to matching.
    The mask must be the same size as the template (single-channel uint8,
    255 = include, 0 = exclude).  Masked matching forces ``TM_CCORR_NORMED``
    because OpenCV only supports masks with ``TM_SQDIFF`` and
    ``TM_CCORR_NORMED``.

    Returns a :class:`MatchResult` with ``matched=False`` when the template
    is larger than the search area or when the best score is below *threshold*.
    """
    if region is not None:
        search = image[region.y : region.y2, region.x : region.x2]
        offset_x, offset_y = region.x, region.y
    else:
        search = image
        offset_x, offset_y = 0, 0

    th, tw = template.shape[:2]
    sh, sw = search.shape[:2]

    # Template must fit inside the search area.
    if th > sh or tw > sw:
        return MatchResult(score=0.0, x=offset_x, y=offset_y, w=tw, h=th, matched=False)

    _start = time.perf_counter()
    if mask is not None:
        # Masked matching only works with TM_CCORR_NORMED (and TM_SQDIFF)
        method = cv2.TM_CCORR_NORMED
        result_map = cv2.matchTemplate(search, template, method, mask=mask)
    else:
        result_map = cv2.matchTemplate(search, template, method)

    mr = _best_from_result(result_map, method, tw, th, offset_x, offset_y, threshold)
    _elapsed_ms = (time.perf_counter() - _start) * 1000
    if mr.matched:
        logger.debug(
            "match_template: {:.0f}ms, score={:.3f} at ({},{}) {}x{} (threshold={})",
            _elapsed_ms, mr.score, mr.x, mr.y, mr.w, mr.h, threshold,
        )
    else:
        logger.debug(
            "match_template: {:.0f}ms, no match (best={:.3f}, threshold={})",
            _elapsed_ms, mr.score, threshold,
        )
    return mr


def match_best(
    image: np.ndarray,
    templates: list[np.ndarray],
    region: Rect | None = None,
    threshold: float = 0.7,
) -> MatchResult:
    """Try multiple templates and return the one with the highest score.

    If *templates* is empty, returns an unmatched zero-score result.
    """
    if not templates:
        return _no_match()

    best: MatchResult = _no_match()
    for tmpl in templates:
        candidate = match_template(image, tmpl, region=region, threshold=threshold)
        if candidate.score > best.score:
            best = candidate
    logger.debug(
        "match_best: {} templates, best score={:.3f}, matched={}",
        len(templates), best.score, best.matched,
    )
    return best


def match_all(
    image: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.7,
    region: Rect | None = None,
) -> list[MatchResult]:
    """Find all matches above *threshold* using greedy non-maximum suppression.

    The search honours *region* the same way as :func:`match_template`.
    Overlapping detections (within one template footprint) are collapsed to the
    highest-scoring one.

    Returns an empty list when no match exceeds *threshold*.
    """
    method = cv2.TM_CCOEFF_NORMED  # match_all only supports TM_CCOEFF_NORMED

    if region is not None:
        search = image[region.y : region.y2, region.x : region.x2]
        offset_x, offset_y = region.x, region.y
    else:
        search = image
        offset_x, offset_y = 0, 0

    th, tw = template.shape[:2]
    sh, sw = search.shape[:2]

    if th > sh or tw > sw:
        return []

    result_map: np.ndarray = cv2.matchTemplate(search, template, method)

    # Collect all candidate locations above threshold.
    ys, xs = np.where(result_map >= threshold)
    if len(xs) == 0:
        return []

    scores = result_map[ys, xs]
    # Sort descending by score.
    order = np.argsort(scores)[::-1]

    candidates: list[MatchResult] = []
    for idx in order:
        cx = int(xs[idx])
        cy = int(ys[idx])
        candidates.append(
            MatchResult(
                score=float(scores[idx]),
                x=cx + offset_x,
                y=cy + offset_y,
                w=tw,
                h=th,
                matched=True,
            )
        )

    # Greedy NMS: keep a match only if it does not overlap any kept match.
    kept: list[MatchResult] = []
    for cand in candidates:
        if not any(_overlaps(cand, k) for k in kept):
            kept.append(cand)

    logger.debug(
        "match_all: {} candidates above threshold={}, {} kept after NMS",
        len(candidates), threshold, len(kept),
    )
    return kept


def _overlaps(a: MatchResult, b: MatchResult) -> bool:
    """Return True if two MatchResult bounding boxes intersect."""
    return not (
        a.x + a.w <= b.x
        or b.x + b.w <= a.x
        or a.y + a.h <= b.y
        or b.y + b.h <= a.y
    )
