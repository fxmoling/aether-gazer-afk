"""Walk forward by holding W key.

Used during exploration segments between battles.
Holds W for a configurable duration (default 2 seconds).

Composite Action: uses HoldKeyOp primitive internally.
"""
from __future__ import annotations

import time

from anime_game_afk.games.aether_gazer.knowledge.constants import (
    WALK_DEFAULT_DURATION,
)
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_W
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.primitives import HoldKeyOp


class WalkForwardAction:
    """Hold W to walk forward for a duration."""

    def __init__(self, duration: float = WALK_DEFAULT_DURATION) -> None:
        self._duration = duration

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.logger.info(
            f"[walk_forward] Holding W (0x{VK_W:02X}) for {self._duration}s"
        )
        t0 = time.perf_counter()
        await HoldKeyOp(
            key=VK_W,
            duration=self._duration,
            wait=0.2,
        ).run(ctx)
        elapsed = time.perf_counter() - t0
        ctx.logger.debug(f"[walk_forward] Completed in {elapsed:.3f}s")
        return OpResult(
            success=True,
            data={"direction": "forward", "duration": self._duration},
        )
