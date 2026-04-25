"""Screen change detection check.

No side effects.
"""
from __future__ import annotations

import numpy as np

from anime_game_afk.games.aether_gazer.checks.base import CheckResult
from anime_game_afk.games.aether_gazer.ops.base import OpContext


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
