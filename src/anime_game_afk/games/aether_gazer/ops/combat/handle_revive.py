"""Handle revive prompt during battle.

When a character dies, the game shows a revival confirmation.
This op presses Enter to accept the revival.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ENTER
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult


class HandleReviveOp:
    """Accept revival prompt by pressing Enter."""

    def __init__(self, wait_after: float = 3.0) -> None:
        self._wait = wait_after

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.device.press_key(VK_ENTER)
        ctx.logger.info("Revive prompt: pressed Enter to accept")
        await asyncio.sleep(self._wait)
        return OpResult(success=True, data={"action": "revive_accepted"})
