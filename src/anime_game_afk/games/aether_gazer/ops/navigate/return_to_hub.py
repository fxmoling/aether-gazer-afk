"""Return to main hub from any page.

Repeatedly detects current page and navigates backward until
main_hub is reached. Uses template matching + batch OCR for verification.
Max 8 attempts before giving up.

Composite Op: uses primitives + checks internally.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.checks.ocr import HasTextCheck, OcrScanCheck
from anime_game_afk.games.aether_gazer.checks.page import AtHubCheck, IdentifyPageCheck
from anime_game_afk.games.aether_gazer.knowledge.constants import (
    BACK_BUTTON_X,
    BACK_BUTTON_Y,
)
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ESCAPE
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.primitives import (
    ClickOp,
    PressKeyOp,
)

_MAX_ATTEMPTS = 8


class ReturnToHubOp:
    """Navigate back to main hub from any page."""

    async def run(self, ctx: OpContext) -> OpResult:
        for attempt in range(_MAX_ATTEMPTS):
            # Check if already at hub
            hub_r = await AtHubCheck().evaluate(ctx)
            if hub_r.passed:
                ctx.logger.info(
                    f"At main hub (attempt {attempt})"
                )
                return OpResult(
                    success=True,
                    data={"page_id": "main_hub", "attempts": attempt},
                )

            # Identify current page for strategy selection
            page_r = await IdentifyPageCheck().evaluate(ctx)
            page_id = page_r.data["page"] if page_r.data else "unknown"

            # Settings panel: just ESC
            if page_id == "settings_panel":
                ctx.logger.info("Settings panel detected, pressing ESC")
                await PressKeyOp(key=VK_ESCAPE, wait=1.0).run(ctx)
                continue

            # Alternate between ESC and click-back
            ctx.logger.warning(
                f"Not at hub (page={page_id}), attempt {attempt}"
            )
            if attempt % 2 == 0:
                await PressKeyOp(key=VK_ESCAPE, wait=1.5).run(ctx)

                # Check if ESC triggered "退出游戏" dialog (happens at hub)
                exit_r = await HasTextCheck(target="退出游戏").evaluate(ctx)
                if exit_r.passed:
                    ctx.logger.info(
                        "Exit dialog detected — we are at hub, "
                        "cancelling dialog"
                    )
                    await PressKeyOp(key=VK_ESCAPE, wait=1.0).run(ctx)
                    return OpResult(
                        success=True,
                        data={"page_id": "main_hub", "attempts": attempt},
                    )
                # Also check alternate text
                exit_r2 = await HasTextCheck(target="是否退出").evaluate(ctx)
                if exit_r2.passed:
                    ctx.logger.info(
                        "Exit dialog (alt) detected — at hub, cancelling"
                    )
                    await PressKeyOp(key=VK_ESCAPE, wait=1.0).run(ctx)
                    return OpResult(
                        success=True,
                        data={"page_id": "main_hub", "attempts": attempt},
                    )
            else:
                await ClickOp(
                    x=BACK_BUTTON_X, y=BACK_BUTTON_Y, wait=1.5,
                ).run(ctx)

        # Final check
        hub_r = await AtHubCheck().evaluate(ctx)
        if hub_r.passed:
            return OpResult(success=True, data={"page_id": "main_hub"})

        ctx.logger.error("Failed to return to hub after max attempts")
        return OpResult(success=False, error="Could not reach main hub")
