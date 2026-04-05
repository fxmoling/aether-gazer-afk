"""Confirm or dismiss a popup dialog.

Presses Enter to confirm or ESC to cancel.
The action is configurable; default is confirm (Enter).
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.keys import (
    VK_ENTER,
    VK_ESCAPE,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult


class ConfirmPopupOp:
    """Respond to a popup dialog."""

    def __init__(
        self, confirm: bool = True, wait_after: float = 2.0
    ) -> None:
        self._confirm = confirm
        self._wait = wait_after

    async def run(self, ctx: OpContext) -> OpResult:
        if self._confirm:
            ctx.device.press_key(VK_ENTER)
            ctx.logger.info("Popup confirmed: pressed Enter")
        else:
            ctx.device.press_key(VK_ESCAPE)
            ctx.logger.info("Popup dismissed: pressed ESC")

        await asyncio.sleep(self._wait)
        return OpResult(success=True, data={"confirmed": self._confirm})
