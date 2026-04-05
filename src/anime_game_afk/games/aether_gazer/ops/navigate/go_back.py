"""Go back one page.

Presses ESC or clicks the back button (35, 35) depending on
the current page's navigation edge. Falls back to ESC if no
edge is found.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.constants import (
    BACK_BUTTON_X,
    BACK_BUTTON_Y,
)
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ESCAPE
from anime_game_afk.games.aether_gazer.knowledge.navigation import (
    NAV_GRAPH,
    NavMethod,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult


class GoBackOp:
    """Go back from current page toward hub.

    Uses the navigation graph to determine the correct back action.
    If current_page is unknown, falls back to ESC.
    """

    def __init__(self, current_page: str = "unknown") -> None:
        self._current_page = current_page

    async def run(self, ctx: OpContext) -> OpResult:
        # Look up the backward edge
        edge = NAV_GRAPH.get_edge(self._current_page, "main_hub")

        if edge is not None:
            action = edge.action
            if action.method == NavMethod.CLICK and action.coord:
                ctx.device.click(action.coord.x, action.coord.y)
                ctx.logger.info(
                    f"Go back: click ({action.coord.x}, {action.coord.y})"
                )
            elif action.method == NavMethod.KEY and action.key_code:
                ctx.device.press_key(action.key_code)
                ctx.logger.info(
                    f"Go back: press key 0x{action.key_code:02X}"
                )
            else:
                ctx.device.press_key(VK_ESCAPE)
                ctx.logger.info("Go back: ESC (default)")
            await asyncio.sleep(action.wait_after)
        else:
            # Unknown page — try ESC
            ctx.device.press_key(VK_ESCAPE)
            ctx.logger.info("Go back: ESC (no edge found)")
            await asyncio.sleep(1.5)

        return OpResult(success=True)
