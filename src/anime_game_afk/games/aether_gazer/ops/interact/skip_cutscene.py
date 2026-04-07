"""Skip a cutscene.

Sequence: ESC (open skip dialog) -> wait -> Enter (confirm skip).
Uses keyboard shortcuts per the game's UI convention.

Composite Op: uses PressKeyOp primitive internally.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.knowledge.keys import (
    VK_ENTER,
    VK_ESCAPE,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.primitives import PressKeyOp


class SkipCutsceneOp:
    """Skip a cutscene by pressing ESC then Enter."""

    def __init__(self, confirm_wait: float = 1.5) -> None:
        self._confirm_wait = confirm_wait

    async def run(self, ctx: OpContext) -> OpResult:
        # ESC opens the "skip?" confirmation dialog
        ctx.logger.info("Skip cutscene: pressing ESC")
        await PressKeyOp(key=VK_ESCAPE, wait=self._confirm_wait).run(ctx)

        # Enter confirms the skip
        ctx.logger.info("Skip cutscene: pressing Enter to confirm")
        await PressKeyOp(key=VK_ENTER, wait=2.0).run(ctx)

        return OpResult(success=True)
