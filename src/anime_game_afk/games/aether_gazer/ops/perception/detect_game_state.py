"""Detect current game state from screenshot.

Uses template matching against known text templates to determine
whether we're in battle, cutscene, dialogue, menus, etc.
Templates are loaded from assets/aether_gazer/templates/text/.

Migrated from scripts/ch6_battle.py StateDetector.
"""
from __future__ import annotations

import cv2
import numpy as np

from anime_game_afk.core.types import Rect
from anime_game_afk.vision.matcher import match_template
from anime_game_afk.games.aether_gazer.knowledge.resources import (
    STATE_TEMPLATES,
    TEXT_TEMPLATE_DIR,
    StateTemplateDef,
)
from anime_game_afk.games.aether_gazer.ops.base import (
    GameState,
    OpContext,
    OpResult,
)

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


def detect_state(screenshot: np.ndarray) -> tuple[GameState, float]:
    """Detect game state from a 1600x900 screenshot.

    Returns (GameState, confidence). Checks templates in priority
    order; returns the highest-confidence match above threshold.

    Pure utility function — usable by other ops directly.
    """
    images = _load_state_templates()
    half = cv2.resize(screenshot, (800, 450), interpolation=cv2.INTER_AREA)

    best_state = GameState.UNKNOWN
    best_conf = 0.0

    for tdef in STATE_TEMPLATES:
        tpl_img = images.get(tdef.name)
        if tpl_img is None:
            continue

        # Choose image scale: half-size templates match against 800x450
        img = half if tdef.half_scale else screenshot
        region = tdef.search_region

        # Scale search region for half-size templates
        if tdef.half_scale and region is not None:
            region = Rect(
                region.x // 2, region.y // 2,
                region.w // 2, region.h // 2,
            )

        result = match_template(img, tpl_img, region=region)

        if result.score >= tdef.threshold and result.score > best_conf:
            best_conf = result.score
            best_state = _STATE_MAP.get(tdef.name, GameState.UNKNOWN)

    # Black screen = loading (only reliable non-template check).
    # This is NOT pixel-brightness UI detection — it detects a
    # fully black loading screen where mean < 15.
    if best_state == GameState.UNKNOWN and np.mean(screenshot) < 15:
        best_state = GameState.LOADING
        best_conf = 0.99

    return (best_state, best_conf)


class DetectGameStateOp:
    """Op wrapper: take screenshot and detect game state.

    Result data: {"state": GameState, "confidence": float}
    """

    async def run(self, ctx: OpContext) -> OpResult:
        screenshot = ctx.screenshot()
        state, confidence = detect_state(screenshot)
        ctx.logger.debug(
            f"Game state: {state.value} (confidence={confidence:.2f})"
        )
        return OpResult(
            success=True,
            data={"state": state, "confidence": confidence},
        )
