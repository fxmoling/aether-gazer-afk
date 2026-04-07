"""Confirm or dismiss a popup dialog.

Presses Enter to confirm or ESC to cancel.
The action is configurable; default is confirm (Enter).

Composite Op: uses PressKeyOp primitive internally.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.knowledge.keys import (
    VK_ENTER,
    VK_ESCAPE,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.primitives import PressKeyOp


class ConfirmPopupOp:
    """Respond to a popup dialog."""

    def __init__(
        self, confirm: bool = True, wait_after: float = 2.0
    ) -> None:
        self._confirm = confirm
        self._wait = wait_after

    async def run(self, ctx: OpContext) -> OpResult:
        if self._confirm:
            ctx.logger.info("Popup confirmed: pressing Enter")
            await PressKeyOp(key=VK_ENTER, wait=self._wait).run(ctx)
        else:
            ctx.logger.info("Popup dismissed: pressing ESC")
            await PressKeyOp(key=VK_ESCAPE, wait=self._wait).run(ctx)

        return OpResult(success=True, data={"confirmed": self._confirm})
