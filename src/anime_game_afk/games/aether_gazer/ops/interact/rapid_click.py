"""Click a fixed position multiple times rapidly.

Simple composite Action that wraps ClickOp in a loop. Useful for
dismissing multi-step dialogs, collecting rewards, or spamming
through confirmation screens.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.primitives import ClickOp, ClickPxOp


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

        return OpResult(
            success=True,
            data={
                "x": self._x,
                "y": self._y,
                "clicks": self._times,
            },
        )


class RapidClickPxAction:
    """Click a pixel position multiple times (OCR/vision coords).

    Converts screenshot-space pixel coords to fractional using
    ``ctx.device.resolution`` before clicking.
    """

    def __init__(
        self,
        px: int,
        py: int,
        times: int = 5,
        interval: float = 0.5,
    ) -> None:
        self._px = px
        self._py = py
        self._times = times
        self._interval = interval

    async def run(self, ctx: OpContext) -> OpResult:
        img_w, img_h = ctx.device.resolution
        fx = self._px / img_w
        fy = self._py / img_h
        ctx.logger.debug(
            f"rapid_click_px ({self._px},{self._py}) -> "
            f"frac ({fx:.3f},{fy:.3f}) x{self._times} @{self._interval}s"
        )
        click = ClickOp(fx, fy, wait=self._interval)

        for i in range(self._times):
            result = await click.run(ctx)
            if not result.success:
                return OpResult(
                    success=False,
                    error=f"Failed on click {i + 1}: {result.error}",
                    data={"completed": i, "total": self._times},
                )

        return OpResult(
            success=True,
            data={"px": self._px, "py": self._py, "clicks": self._times},
        )
