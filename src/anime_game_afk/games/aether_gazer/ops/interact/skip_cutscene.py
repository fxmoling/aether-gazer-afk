"""Skip a cutscene.

Sequence: ESC (open skip dialog) -> wait -> Enter (confirm skip).
Uses keyboard shortcuts per the game's UI convention.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.keys import (
    VK_ENTER,
    VK_ESCAPE,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult


class SkipCutsceneOp:
    """Skip a cutscene by pressing ESC then Enter."""

    def __init__(self, confirm_wait: float = 1.5) -> None:
        self._confirm_wait = confirm_wait

    async def run(self, ctx: OpContext) -> OpResult:
        # ESC opens the "skip?" confirmation dialog
        ctx.device.press_key(VK_ESCAPE)
        ctx.logger.info("Skip cutscene: pressed ESC")
        await asyncio.sleep(self._confirm_wait)

        # Enter confirms the skip
        ctx.device.press_key(VK_ENTER)
        ctx.logger.info("Skip cutscene: pressed Enter to confirm")
        await asyncio.sleep(2.0)

        return OpResult(success=True)
