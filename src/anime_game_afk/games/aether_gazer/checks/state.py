"""Game state checks.

Checks for detecting game state (battle, cutscene, loading, etc.)
and screen change detection. No side effects.
"""
from __future__ import annotations

import numpy as np

from anime_game_afk.games.aether_gazer.checks.base import CheckResult
from anime_game_afk.games.aether_gazer.ops.base import GameState, OpContext
from anime_game_afk.games.aether_gazer.ops.perception.detect_game_state import (
    detect_state,
)


class DetectGameStateCheck:
    """Detect the current game state from screenshot.

    Always passes. data contains state (GameState) and confidence.
    """

    async def evaluate(self, ctx: OpContext) -> CheckResult:
        img = ctx.device.screenshot()
        state, confidence = detect_state(img)
        return CheckResult(
            passed=(state != GameState.UNKNOWN),
            data={"state": state, "confidence": confidence},
            message=f"state={state.value} conf={confidence:.2f}",
        )


class ScreenUnchangedCheck:
    """Check if the screen has not changed compared to a previous screenshot.

    Compares mean absolute pixel difference. If diff < threshold,
    the screen is considered unchanged (passed=True).

    Note: Unlike other checks, this one does NOT take a screenshot internally.
    It compares the provided prev_image against a new screenshot from ctx.
    """

    def __init__(
        self,
        prev_image: np.ndarray,
        threshold: float = 5.0,
    ) -> None:
        self._prev = prev_image
        self._threshold = threshold

    async def evaluate(self, ctx: OpContext) -> CheckResult:
        img = ctx.device.screenshot()
        diff = float(np.mean(np.abs(
            img.astype(float) - self._prev.astype(float)
        )))
        unchanged = diff < self._threshold
        return CheckResult(
            passed=unchanged,
            data={"diff": diff},
            message=(
                f"screen {'unchanged' if unchanged else 'changed'} "
                f"(diff={diff:.1f}, threshold={self._threshold})"
            ),
        )
