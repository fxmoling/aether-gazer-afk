"""Page template matching — ``is_on_page`` check.

Loads page templates from index.json, matches against screenshot
using vision.matcher.  Provides ``is_on_page(screenshot, page_id)``
for targeted page checks (pass/fail).

Templates are stored at a reference resolution (``ref_height``).  When the
screenshot height differs, templates are proportionally scaled before
matching.  Search regions are stored as fractional coordinates [0..1]
and converted to pixel coordinates at runtime.

Masked templates (e.g. circular crop for the idle-hub disc icon) are
supported via an optional ``"mask": "circle"`` field in index.json.
Masked matching uses ``TM_CCORR_NORMED`` instead of the default
``TM_CCOEFF_NORMED``, so each masked template should specify its own
``"threshold"`` value.
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
    ASSETS_ROOT,
    TEMPLATE_DIR,
    TEMPLATE_INDEX,
)


# Module-level template cache (loaded once, reused)
_page_templates: dict[str, list[dict]] | None = None


def _load_templates() -> dict[str, list[dict]]:
    """Load page templates from index.json.

    Returns dict: page_id -> list of template dicts with keys:
      image, ref_height, search_frac, mask, threshold.

    ``search_frac`` is a fractional tuple (fx1, fy1, fx2, fy2) or None.
    ``mask`` is a single-channel uint8 ndarray (same size as image) or None.
    ``threshold`` is a float or None (None = use global MATCH_THRESHOLD).
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

    # Resolve base directory for relative template paths in index.json.
    # Paths in index.json start with "assets/..." — relative to project root (dev)
    # or sys._MEIPASS (frozen).
    _tpl_base = ASSETS_ROOT.parent.parent  # assets/aether_gazer -> assets -> base

    for page_id, templates in index.items():
        loaded = []
        for tpl in templates:
            raw_path = tpl["path"]
            img_path = Path(raw_path)
            if not img_path.is_absolute():
                img_path = _tpl_base / img_path
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            search = tpl.get("search")
            search_frac: tuple[float, float, float, float] | None = None
            if search and len(search) == 4:
                search_frac = tuple(search)  # type: ignore[assignment]
            ref_height = tpl.get("ref_height", 900)

            # Generate mask from type descriptor
            mask_type = tpl.get("mask")
            mask: np.ndarray | None = None
            if mask_type == "circle":
                mh, mw = img.shape[:2]
                mask = np.zeros((mh, mw), dtype=np.uint8)
                cv2.circle(
                    mask,
                    (mw // 2, mh // 2),
                    min(mw, mh) // 2 - 1,
                    255,
                    -1,
                )

            threshold = tpl.get("threshold")  # None = global default
            grayscale = tpl.get("grayscale", False)

            loaded.append({
                "image": img,
                "ref_height": ref_height,
                "search_frac": search_frac,
                "mask": mask,
                "threshold": threshold,
                "grayscale": grayscale,
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


def _prepare_mask(
    mask: np.ndarray,
    ref_height: int,
    screenshot_h: int,
) -> np.ndarray:
    """Scale mask to match the screenshot resolution.

    Uses ``INTER_NEAREST`` to keep binary values, then re-binarizes
    to ensure clean {0, 255} values after scaling.
    """
    if ref_height == screenshot_h:
        return mask
    scale = screenshot_h / ref_height
    new_w = max(1, int(mask.shape[1] * scale))
    new_h = max(1, int(mask.shape[0] * scale))
    scaled = cv2.resize(mask, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
    _, binary = cv2.threshold(scaled, 127, 255, cv2.THRESH_BINARY)
    return binary


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


def _match_one(
    tpl: dict,
    screenshot: np.ndarray,
    img_w: int,
    img_h: int,
) -> tuple[float, float]:
    """Match a single template, return (score, threshold)."""
    scaled = _prepare_template(tpl["image"], tpl["ref_height"], img_h)
    mask = (
        _prepare_mask(tpl["mask"], tpl["ref_height"], img_h)
        if tpl.get("mask") is not None
        else None
    )
    region = (
        _frac_to_pixel_region(tpl["search_frac"], img_w, img_h)
        if tpl["search_frac"] is not None
        else None
    )
    # Grayscale mode: convert both to single-channel before matching.
    # CCOEFF_NORMED on grayscale is robust to color/brightness shifts.
    ss = screenshot
    tpl_img = scaled
    if tpl.get("grayscale"):
        if len(ss.shape) == 3:
            ss = cv2.cvtColor(ss, cv2.COLOR_BGR2GRAY)
        if len(tpl_img.shape) == 3:
            tpl_img = cv2.cvtColor(tpl_img, cv2.COLOR_BGR2GRAY)
    result = match_template(ss, tpl_img, region=region, mask=mask)
    threshold = tpl.get("threshold") if tpl.get("threshold") is not None else MATCH_THRESHOLD
    return result.score, threshold


def is_on_page(screenshot: np.ndarray, page_id: str) -> bool:
    """Quick check: is the screenshot showing the given page?

    Returns True only when *every* template for *page_id* scores at
    or above its threshold.
    """
    templates = _load_templates()
    tpl_list = templates.get(page_id, [])
    if not tpl_list:
        return False
    img_h, img_w = screenshot.shape[:2]
    for tpl in tpl_list:
        score, threshold = _match_one(tpl, screenshot, img_w, img_h)
        if score < threshold:
            _loguru.debug(
                "[is_on_page] {} FAIL: score={:.3f} < threshold={:.3f} "
                "(screenshot {}x{}, ref_height={})",
                page_id, score, threshold, img_w, img_h, tpl["ref_height"],
            )
            return False
    return True
