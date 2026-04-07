"""Wake up hub UI from idle mode.

When the hub is idle (screensaver-like), the UI is hidden.
Uses ESC key to wake (works with PostMessageWithWindowPos mouse),
then checks for and cancels the "exit game" dialog if triggered.

Important: Hub active + ESC = "是否退出游戏?" dialog.
           Hub idle + ESC = wake UI.
So we must detect and cancel the exit dialog after pressing ESC.

Composite Op: uses PressKeyOp/ClickOp primitives + HasTextCheck.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.checks.ocr import HasTextCheck
from anime_game_afk.games.aether_gazer.knowledge.constants import (
    SCREEN_CENTER_X,
    SCREEN_CENTER_Y,
)
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ESCAPE
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.primitives import (
    ClickOp,
    PressKeyOp,
)


class WakeHubUiOp:
    """Wake idle hub UI using ESC key, with exit-dialog safety check."""

    async def run(self, ctx: OpContext) -> OpResult:
        # Press ESC to wake idle hub
        await PressKeyOp(key=VK_ESCAPE, wait=1.5).run(ctx)

        # One OCR check for exit-game dialog
        r = await HasTextCheck(target="退出游戏").evaluate(ctx)
        if r.passed:
            # Cancel the exit dialog with ESC (= 取消 button)
            ctx.logger.debug("Exit dialog detected, canceling with ESC")
            await PressKeyOp(key=VK_ESCAPE, wait=1.0).run(ctx)
        else:
            # Also check alternate text
            r2 = await HasTextCheck(target="是否退出").evaluate(ctx)
            if r2.passed:
                ctx.logger.debug("Exit dialog detected (alt), canceling")
                await PressKeyOp(key=VK_ESCAPE, wait=1.0).run(ctx)
            else:
                # Click center as fallback for other overlays
                await ClickOp(
                    x=SCREEN_CENTER_X, y=SCREEN_CENTER_Y, wait=0.5,
                ).run(ctx)

        ctx.logger.debug("Woke hub UI")
        return OpResult(success=True)
