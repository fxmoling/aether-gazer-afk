"""Identify current page from screenshot.

Loads page templates from index.json, matches against screenshot
using vision.matcher. Returns (page_id, confidence).

Templates are stored at a reference resolution (``ref_height``).  When the
screenshot height differs, templates are proportionally scaled before
matching.  Search regions are stored as fractional coordinates [0..1]
and converted to pixel coordinates at runtime.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from loguru import logger as _loguru

from anime_game_afk.core.types import Rect
from anime_game_afk.vision.matcher import match_template
from anime_game_afk.games.aether_gazer.knowledge.constants import (
    MATCH_THRESHOLD,
)
from anime_game_afk.games.aether_gazer.knowledge.resources import (
    TEMPLATE_DIR,
    TEMPLATE_INDEX,
)


# Module-level template cache (loaded once, reused)
_page_templates: dict[str, list[dict]] | None = None


def _load_templates() -> dict[str, list[dict]]:
    """Load page templates from index.json.

    Returns dict: page_id -> list of {image, ref_height, search_frac}.
    ``search_frac`` is a fractional tuple (fx1, fy1, fx2, fy2) or None.
    Cached at module level after first call.
    """
    global _page_templates
    if _page_templates is not None:
        return _page_templates

    _page_templates = {}
    if not TEMPLATE_INDEX.exists():
        return _page_templates

    try:
        with open(TEMPLATE_INDEX, encoding="utf-8") as f:
            index = json.load(f)
    except (json.JSONDecodeError, ValueError) as exc:
        _loguru.warning(
            "Corrupt template index {}, starting with empty templates: {}",
            TEMPLATE_INDEX, exc,
        )
        return _page_templates

    for page_id, templates in index.items():
        loaded = []
        for tpl in templates:
            raw_path = tpl["path"]
            img_path = Path(raw_path) if not Path(raw_path).is_absolute() else Path(raw_path)
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            search = tpl.get("search")
            search_frac: tuple[float, float, float, float] | None = None
            if search and len(search) == 4:
                search_frac = tuple(search)  # type: ignore[assignment]
            ref_height = tpl.get("ref_height", 900)
            loaded.append({
                "image": img,
                "ref_height": ref_height,
                "search_frac": search_frac,
            })
        if loaded:
            _page_templates[page_id] = loaded

    return _page_templates


def _prepare_template(
    tpl_image: np.ndarray,
    ref_height: int,
    screenshot_h: int,
) -> np.ndarray:
    """Scale template to match the screenshot resolution."""
    if ref_height == screenshot_h:
        return tpl_image
    scale = screenshot_h / ref_height
    new_w = max(1, int(tpl_image.shape[1] * scale))
    new_h = max(1, int(tpl_image.shape[0] * scale))
    return cv2.resize(tpl_image, (new_w, new_h), interpolation=cv2.INTER_AREA)


def _frac_to_pixel_region(
    search_frac: tuple[float, float, float, float],
    img_w: int,
    img_h: int,
) -> Rect:
    """Convert fractional search region to pixel Rect."""
    fx1, fy1, fx2, fy2 = search_frac
    x1 = int(fx1 * img_w)
    y1 = int(fy1 * img_h)
    x2 = int(fx2 * img_w)
    y2 = int(fy2 * img_h)
    return Rect(x1, y1, x2 - x1, y2 - y1)


def identify(screenshot: np.ndarray) -> tuple[str, float]:
    """Identify which page the screenshot shows.

    Returns (page_id, confidence). Returns ("unknown", 0.0) if
    no page matches above MATCH_THRESHOLD.
    """
    templates = _load_templates()
    best_page = "unknown"
    best_score = 0.0
    img_h, img_w = screenshot.shape[:2]

    for page_id, tpl_list in templates.items():
        scores = []
        for tpl in tpl_list:
            scaled = _prepare_template(tpl["image"], tpl["ref_height"], img_h)
            region = None
            if tpl["search_frac"] is not None:
                region = _frac_to_pixel_region(tpl["search_frac"], img_w, img_h)
            result = match_template(screenshot, scaled, region=region)
            scores.append(result.score)
        if scores:
            avg = sum(scores) / len(scores)
            if avg > best_score:
                best_score = avg
                best_page = page_id

    if best_score < MATCH_THRESHOLD:
        return ("unknown", best_score)
    return (best_page, best_score)


def is_on_page(screenshot: np.ndarray, page_id: str) -> bool:
    """Quick check: is the screenshot showing the given page?"""
    templates = _load_templates()
    tpl_list = templates.get(page_id, [])
    if not tpl_list:
        return False
    img_h, img_w = screenshot.shape[:2]
    scores = []
    for tpl in tpl_list:
        scaled = _prepare_template(tpl["image"], tpl["ref_height"], img_h)
        region = None
        if tpl["search_frac"] is not None:
            region = _frac_to_pixel_region(tpl["search_frac"], img_w, img_h)
        result = match_template(screenshot, scaled, region=region)
        scores.append(result.score)
    avg = sum(scores) / len(scores) if scores else 0.0
    return avg >= MATCH_THRESHOLD
