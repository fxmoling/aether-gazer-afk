"""Detect current game state from screenshot.

Uses template matching against known text templates to determine
whether we're in battle, cutscene, dialogue, menus, etc.
Templates are loaded from assets/aether_gazer/templates/text/.

Templates are stored at a reference resolution (``ref_height``).
When the screenshot height differs, templates are proportionally
scaled before matching.  Search regions are fractional [0..1].
"""
from __future__ import annotations

import cv2
import numpy as np

from anime_game_afk.core.types import Rect
from anime_game_afk.vision.matcher import match_template
from anime_game_afk.games.aether_gazer.knowledge.resources import (
    STATE_TEMPLATES,
    TEXT_TEMPLATE_DIR,
)
from anime_game_afk.games.aether_gazer.ops.base import GameState

# Mapping from template name to GameState enum
_STATE_MAP: dict[str, GameState] = {
    "mission_failed": GameState.MISSION_FAILED,
    "revive_prompt": GameState.REVIVE_PROMPT,
    "skip_story_confirm": GameState.SKIP_STORY_CONFIRM,
    "continuous_battle": GameState.CONTINUOUS_BATTLE,
    "prep_battle": GameState.PREP_BATTLE,
    "battle_hud": GameState.BATTLE,
    "stage_map": GameState.STAGE_MAP,
}

# Module-level cache: template name -> loaded image
_loaded: dict[str, np.ndarray] | None = None


def _load_state_templates() -> dict[str, np.ndarray]:
    """Load all state detection templates from disk."""
    global _loaded
    if _loaded is not None:
        return _loaded

    _loaded = {}
    for tdef in STATE_TEMPLATES:
        path = TEXT_TEMPLATE_DIR / tdef.filename
        img = cv2.imread(str(path))
        if img is None:
            continue
        _loaded[tdef.name] = img
    return _loaded


def _scale_template(
    tpl: np.ndarray, ref_height: int, screenshot_h: int,
) -> np.ndarray:
    """Proportionally scale a template to match the screenshot resolution."""
    if ref_height == screenshot_h:
        return tpl
    scale = screenshot_h / ref_height
    new_w = max(1, int(tpl.shape[1] * scale))
    new_h = max(1, int(tpl.shape[0] * scale))
    return cv2.resize(tpl, (new_w, new_h), interpolation=cv2.INTER_AREA)


def _frac_to_rect(
    frac: tuple[float, float, float, float], img_w: int, img_h: int,
) -> Rect:
    """Convert fractional (x1, y1, x2, y2) to pixel Rect."""
    fx1, fy1, fx2, fy2 = frac
    x1 = int(fx1 * img_w)
    y1 = int(fy1 * img_h)
    x2 = int(fx2 * img_w)
    y2 = int(fy2 * img_h)
    return Rect(x1, y1, x2 - x1, y2 - y1)


def detect_state(screenshot: np.ndarray) -> tuple[GameState, float]:
    """Detect game state from a screenshot.

    Returns (GameState, confidence). Checks templates in priority
    order; returns the highest-confidence match above threshold.
    """
    images = _load_state_templates()
    img_h, img_w = screenshot.shape[:2]

    best_state = GameState.UNKNOWN
    best_conf = 0.0

    for tdef in STATE_TEMPLATES:
        tpl_img = images.get(tdef.name)
        if tpl_img is None:
            continue

        scaled = _scale_template(tpl_img, tdef.ref_height, img_h)

        region = None
        if tdef.search_frac is not None:
            region = _frac_to_rect(tdef.search_frac, img_w, img_h)

        result = match_template(screenshot, scaled, region=region)

        if result.score >= tdef.threshold and result.score > best_conf:
            best_conf = result.score
            best_state = _STATE_MAP.get(tdef.name, GameState.UNKNOWN)

    # Black screen = loading (only reliable non-template check).
    if best_state == GameState.UNKNOWN and np.mean(screenshot) < 15:
        best_state = GameState.LOADING
        best_conf = 0.99

    return (best_state, best_conf)
