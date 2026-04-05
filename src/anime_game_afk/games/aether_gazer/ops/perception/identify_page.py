"""Identify current page from screenshot.

Loads page templates from index.json, matches against screenshot
using vision.matcher. Returns (page_id, confidence).

Migrated from pages/template_identifier.py.
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
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult


# Module-level template cache (loaded once, reused)
_page_templates: dict[str, list[dict]] | None = None


def _load_templates() -> dict[str, list[dict]]:
    """Load page templates from index.json.

    Returns dict: page_id -> list of {image, search_region}.
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
            img_path = TEMPLATE_DIR / tpl["path"] if not Path(tpl["path"]).is_absolute() else Path(tpl["path"])
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            search = tpl.get("search")
            region = None
            if search and len(search) == 4:
                x1, y1, x2, y2 = search
                region = Rect(x1, y1, x2 - x1, y2 - y1)
            loaded.append({"image": img, "region": region})
        if loaded:
            _page_templates[page_id] = loaded

    return _page_templates


def identify(screenshot: np.ndarray) -> tuple[str, float]:
    """Identify which page the screenshot shows.

    Returns (page_id, confidence). Returns ("unknown", 0.0) if
    no page matches above MATCH_THRESHOLD.

    This is a pure utility function — usable by other ops directly.
    """
    templates = _load_templates()
    best_page = "unknown"
    best_score = 0.0

    for page_id, tpl_list in templates.items():
        scores = []
        for tpl in tpl_list:
            result = match_template(
                screenshot, tpl["image"], region=tpl["region"],
            )
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
    scores = []
    for tpl in tpl_list:
        result = match_template(
            screenshot, tpl["image"], region=tpl["region"],
        )
        scores.append(result.score)
    avg = sum(scores) / len(scores) if scores else 0.0
    return avg >= MATCH_THRESHOLD


class IdentifyPageOp:
    """Op wrapper: take screenshot and identify current page.

    Result data: {"page_id": str, "confidence": float}
    """

    async def run(self, ctx: OpContext) -> OpResult:
        screenshot = ctx.screenshot()
        page_id, confidence = identify(screenshot)
        ctx.logger.info(
            f"Page identified: {page_id} (confidence={confidence:.2f})"
        )
        return OpResult(
            success=(page_id != "unknown"),
            data={"page_id": page_id, "confidence": confidence},
        )
