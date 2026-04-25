"""Click a fixed position multiple times rapidly.

Simple composite Action that wraps ClickOp in a loop. Useful for
dismissing multi-step dialogs, collecting rewards, or spamming
through confirmation screens.
"""
from __future__ import annotations

import time

from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.primitives import ClickOp


class RapidClickAction:
    """Click a fixed position multiple times rapidly.

    Args:
        x: Fractional x coordinate [0.0, 1.0].
        y: Fractional y coordinate [0.0, 1.0].
    """

    def __init__(
        self,
        x: float,
        y: float,
        times: int = 5,
        interval: float = 0.5,
    ) -> None:
        self._x = x
        self._y = y
        self._times = times
        self._interval = interval

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.logger.debug(
            f"rapid_click ({self._x}, {self._y}) x{self._times} "
            f"@{self._interval}s"
        )
        t0 = time.perf_counter()
        click = ClickOp(self._x, self._y, wait=self._interval)

        for i in range(self._times):
            result = await click.run(ctx)
            if not result.success:
                ctx.logger.error(
                    f"rapid_click failed on click {i + 1}/{self._times}: "
                    f"{result.error}"
                )
                return OpResult(
                    success=False,
                    error=f"Failed on click {i + 1}: {result.error}",
                    data={"completed": i, "total": self._times},
                )

        elapsed = time.perf_counter() - t0
        ctx.logger.debug(
            f"rapid_click done: {self._times} clicks in {elapsed:.3f}s"
        )
        return OpResult(
            success=True,
            data={
                "x": self._x,
                "y": self._y,
                "clicks": self._times,
            },
        )
