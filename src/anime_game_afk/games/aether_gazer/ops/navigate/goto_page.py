"""Navigate to a specific page via the hub.

Route: current_page -> main_hub -> target_page.
Uses NavGraph to determine actions, template matching to verify.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.constants import (
    SCREEN_CENTER_X,
    SCREEN_CENTER_Y,
)
from anime_game_afk.games.aether_gazer.knowledge.navigation import (
    NAV_GRAPH,
    NavAction,
    NavMethod,
)
from anime_game_afk.games.aether_gazer.knowledge.pages import ALL_PAGES
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.perception.identify_page import (
    identify,
    is_on_page,
)

_MAX_RETRIES = 2


def _execute_nav_action(ctx: OpContext, action: NavAction) -> None:
    """Execute a single NavAction on the device."""
    if action.method == NavMethod.CLICK and action.coord:
        ctx.device.click(action.coord.x, action.coord.y)
    elif action.method == NavMethod.KEY and action.key_code:
        ctx.device.press_key(action.key_code)
    elif action.method == NavMethod.ESC:
        from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ESCAPE
        ctx.device.press_key(VK_ESCAPE)


class GotoPageOp:
    """Navigate from current location to target page.

    Finds route via NavGraph, executes each edge's action,
    and verifies arrival with template matching.
    """

    def __init__(self, target_page_id: str) -> None:
        self._target = target_page_id

    async def run(self, ctx: OpContext) -> OpResult:
        if self._target not in ALL_PAGES:
            return OpResult(
                success=False, error=f"Unknown page: {self._target}"
            )

        # Already there?
        screenshot = ctx.screenshot()
        if is_on_page(screenshot, self._target):
            ctx.logger.info(f"Already on page: {self._target}")
            return OpResult(
                success=True,
                data={"page_id": self._target, "already_there": True},
            )

        # Detect current page
        current, _ = identify(screenshot)

        for attempt in range(_MAX_RETRIES + 1):
            # Find route
            route = NAV_GRAPH.find_route(current, self._target)
            if route is None:
                return OpResult(
                    success=False,
                    error=f"No route from {current} to {self._target}",
                )

            # Execute each edge
            for edge in route:
                # Wake UI before navigation
                ctx.device.click(SCREEN_CENTER_X, SCREEN_CENTER_Y)
                await asyncio.sleep(0.3)

                _execute_nav_action(ctx, edge.action)
                await asyncio.sleep(edge.action.wait_after)

            # Verify arrival
            screenshot = ctx.screenshot()
            if is_on_page(screenshot, self._target):
                ctx.logger.info(
                    f"Navigation success: {self._target} "
                    f"(attempt {attempt})"
                )
                return OpResult(
                    success=True,
                    data={"page_id": self._target},
                )

            # Failed — re-detect and retry
            current, _ = identify(screenshot)
            ctx.logger.warning(
                f"Navigation verify failed: expected={self._target}, "
                f"actual={current} (attempt {attempt})"
            )

        return OpResult(
            success=False,
            error=f"Failed to reach {self._target} after {_MAX_RETRIES} retries",
        )
