"""Wake up hub UI from idle mode.

Clicks screen center to dismiss any idle overlay,
then waits briefly for the UI to appear.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.constants import (
    SCREEN_CENTER_X,
    SCREEN_CENTER_Y,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult


class WakeHubUiOp:
    """Click screen center to wake idle hub UI."""

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.device.click(SCREEN_CENTER_X, SCREEN_CENTER_Y)
        ctx.logger.debug("Clicked screen center to wake UI")
        await asyncio.sleep(0.5)
        return OpResult(success=True)
