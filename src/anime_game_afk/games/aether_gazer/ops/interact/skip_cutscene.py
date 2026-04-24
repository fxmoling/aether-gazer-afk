"""Skip a cutscene.

Sequence: ESC (open skip dialog) -> wait -> Enter (confirm skip).
Uses keyboard shortcuts per the game's UI convention.

Composite Action: uses PressKeyOp primitive internally.
"""
from __future__ import annotations

import time

from anime_game_afk.games.aether_gazer.knowledge.keys import (
    VK_ENTER,
    VK_ESCAPE,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.primitives import PressKeyOp


class SkipCutsceneAction:
    """Skip a cutscene by pressing ESC then Enter."""

    def __init__(self, confirm_wait: float = 1.5) -> None:
        self._confirm_wait = confirm_wait

    async def run(self, ctx: OpContext) -> OpResult:
        t0 = time.perf_counter()
        # ESC opens the "skip?" confirmation dialog
        ctx.logger.info("[skip_cutscene] Pressing ESC to open skip dialog")
        await PressKeyOp(key=VK_ESCAPE, wait=self._confirm_wait).run(ctx)

        # Enter confirms the skip
        ctx.logger.info("[skip_cutscene] Pressing Enter to confirm skip")
        await PressKeyOp(key=VK_ENTER, wait=2.0).run(ctx)

        elapsed = time.perf_counter() - t0
        ctx.logger.debug(f"[skip_cutscene] Completed in {elapsed:.3f}s")
        return OpResult(success=True)
