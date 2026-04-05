"""Walk forward by holding W key.

Used during exploration segments between battles.
Holds W for a configurable duration (default 2 seconds).
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.constants import (
    WALK_DEFAULT_DURATION,
)
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_W
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult


class WalkForwardOp:
    """Hold W to walk forward for a duration."""

    def __init__(self, duration: float = WALK_DEFAULT_DURATION) -> None:
        self._duration = duration

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.device.hold_key(VK_W, self._duration)
        ctx.logger.info(f"Walking forward for {self._duration}s")
        await asyncio.sleep(self._duration + 0.2)
        return OpResult(
            success=True,
            data={"direction": "forward", "duration": self._duration},
        )
