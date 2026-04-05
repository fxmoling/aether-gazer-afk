"""Return to main hub from any page.

Repeatedly detects current page and navigates backward until
main_hub is reached. Uses template matching for verification.
Max 8 attempts before giving up.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.constants import (
    BACK_BUTTON_X,
    BACK_BUTTON_Y,
    SCREEN_CENTER_X,
    SCREEN_CENTER_Y,
)
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ESCAPE
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.perception.identify_page import (
    identify,
)

_MAX_ATTEMPTS = 8
_HUB_THRESHOLD = 0.60


class ReturnToHubOp:
    """Navigate back to main hub from any page."""

    async def run(self, ctx: OpContext) -> OpResult:
        for attempt in range(_MAX_ATTEMPTS):
            # Dismiss any dialog/overlay
            ctx.device.click(SCREEN_CENTER_X, SCREEN_CENTER_Y - 50)
            await asyncio.sleep(0.5)

            # Check current page
            screenshot = ctx.screenshot()
            page_id, conf = identify(screenshot)

            if page_id == "main_hub" and conf >= _HUB_THRESHOLD:
                ctx.logger.info(
                    f"At main hub (attempt {attempt}, conf={conf:.2f})"
                )
                return OpResult(
                    success=True,
                    data={"page_id": "main_hub", "attempts": attempt},
                )

            # Settings panel: just ESC
            if page_id == "settings_panel":
                ctx.device.press_key(VK_ESCAPE)
                ctx.logger.info("Settings panel detected, pressing ESC")
                await asyncio.sleep(1.0)
                continue

            # Alternate between ESC and click-back
            ctx.logger.warning(
                f"Not at hub (page={page_id}, conf={conf:.2f}), "
                f"attempt {attempt}"
            )
            if attempt % 2 == 0:
                ctx.device.press_key(VK_ESCAPE)
            else:
                ctx.device.click(BACK_BUTTON_X, BACK_BUTTON_Y)
            await asyncio.sleep(1.5)

        # Final check
        ctx.device.click(SCREEN_CENTER_X, SCREEN_CENTER_Y - 50)
        await asyncio.sleep(0.5)
        screenshot = ctx.screenshot()
        page_id, conf = identify(screenshot)

        if page_id == "main_hub" and conf >= _HUB_THRESHOLD:
            return OpResult(success=True, data={"page_id": "main_hub"})

        ctx.logger.error("Failed to return to hub after max attempts")
        return OpResult(success=False, error="Could not reach main hub")
