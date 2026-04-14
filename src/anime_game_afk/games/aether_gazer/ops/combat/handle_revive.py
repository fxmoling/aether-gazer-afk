"""Handle revive prompt during battle.

When a character dies, the game shows a revival confirmation.
This op presses Enter to accept the revival.

Composite Action: uses PressKeyOp primitive internally.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ENTER
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.primitives import PressKeyOp


class HandleReviveAction:
    """Accept revival prompt by pressing Enter."""

    def __init__(self, wait_after: float = 3.0) -> None:
        self._wait = wait_after

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.logger.info("Revive prompt: pressing Enter to accept")
        await PressKeyOp(key=VK_ENTER, wait=self._wait).run(ctx)
        return OpResult(success=True, data={"action": "revive_accepted"})
