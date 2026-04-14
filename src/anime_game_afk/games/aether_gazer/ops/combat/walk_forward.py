"""Walk forward by holding W key.

Used during exploration segments between battles.
Holds W for a configurable duration (default 2 seconds).

Composite Action: uses HoldKeyOp primitive internally.
"""
from __future__ import annotations

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
        ctx.logger.info(f"Walking forward for {self._duration}s")
        await HoldKeyOp(
            key=VK_W,
            duration=self._duration,
            wait=0.2,
        ).run(ctx)
        return OpResult(
            success=True,
            data={"direction": "forward", "duration": self._duration},
        )
