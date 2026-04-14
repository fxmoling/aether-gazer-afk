"""Advance in-game dialogue.

Presses Space to push dialogue forward. Simple single-action op.

Composite Action: uses PressKeyOp primitive internally.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.knowledge.keys import VK_SPACE
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.primitives import PressKeyOp


class AdvanceDialogueAction:
    """Press Space to advance dialogue."""

    def __init__(self, wait_after: float = 0.4) -> None:
        self._wait = wait_after

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.logger.debug("Advance dialogue: pressing Space")
        await PressKeyOp(key=VK_SPACE, wait=self._wait).run(ctx)
        return OpResult(success=True)
