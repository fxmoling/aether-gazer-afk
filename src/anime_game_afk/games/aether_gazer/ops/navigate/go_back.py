"""Go back one page.

Presses ESC or clicks the back button (35, 35) depending on
the current page's navigation edge. Falls back to ESC if no
edge is found.

Composite Action: uses ClickOp/PressKeyOp primitives internally.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ESCAPE
from anime_game_afk.games.aether_gazer.knowledge.navigation import (
    NAV_GRAPH,
    NavMethod,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.primitives import (
    ClickOp,
    PressKeyOp,
)


class GoBackAction:
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
                ctx.logger.info(
                    f"Go back: click ({action.coord.x}, {action.coord.y})"
                )
                await ClickOp(
                    x=action.coord.x, y=action.coord.y,
                    wait=action.wait_after,
                ).run(ctx)
            elif action.method == NavMethod.KEY and action.key_code:
                ctx.logger.info(
                    f"Go back: press key 0x{action.key_code:02X}"
                )
                await PressKeyOp(
                    key=action.key_code, wait=action.wait_after,
                ).run(ctx)
            else:
                ctx.logger.info("Go back: ESC (default)")
                await PressKeyOp(
                    key=VK_ESCAPE, wait=action.wait_after,
                ).run(ctx)
        else:
            # Unknown page — try ESC
            ctx.logger.info("Go back: ESC (no edge found)")
            await PressKeyOp(key=VK_ESCAPE, wait=1.5).run(ctx)

        return OpResult(success=True)
