"""Advance in-game dialogue.

Presses Space to push dialogue forward. Simple single-action op.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.keys import VK_SPACE
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult


class AdvanceDialogueOp:
    """Press Space to advance dialogue."""

    def __init__(self, wait_after: float = 0.4) -> None:
        self._wait = wait_after

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.device.press_key(VK_SPACE)
        ctx.logger.debug("Advance dialogue: pressed Space")
        await asyncio.sleep(self._wait)
        return OpResult(success=True)
