"""Navigate to a specific page via the hub.

Route: current_page -> main_hub -> target_page.
Uses NavGraph to determine actions, template matching to verify.

Composite Op: uses primitives + checks internally.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.checks.page import (
    IdentifyPageCheck,
    OnPageCheck,
)
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
from anime_game_afk.games.aether_gazer.ops.primitives import (
    ClickOp,
    PressKeyOp,
    SleepOp,
)

_MAX_RETRIES = 2


async def _execute_nav_action(ctx: OpContext, action: NavAction) -> None:
    """Execute a single NavAction using primitive ops."""
    if action.method == NavMethod.CLICK and action.coord:
        await ClickOp(
            x=action.coord.x, y=action.coord.y, wait=0.0,
        ).run(ctx)
    elif action.method == NavMethod.KEY and action.key_code:
        await PressKeyOp(key=action.key_code, wait=0.0).run(ctx)
    elif action.method == NavMethod.ESC:
        from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ESCAPE
        await PressKeyOp(key=VK_ESCAPE, wait=0.0).run(ctx)


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
        on_page = await OnPageCheck(page=self._target).evaluate(ctx)
        if on_page.passed:
            ctx.logger.info(f"Already on page: {self._target}")
            return OpResult(
                success=True,
                data={"page_id": self._target, "already_there": True},
            )

        # Detect current page
        id_result = await IdentifyPageCheck().evaluate(ctx)
        current = id_result.data["page"] if id_result.data else "unknown"

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
                await ClickOp(
                    x=SCREEN_CENTER_X, y=SCREEN_CENTER_Y, wait=0.3,
                ).run(ctx)

                await _execute_nav_action(ctx, edge.action)
                await SleepOp(seconds=edge.action.wait_after).run(ctx)

            # Verify arrival
            on_target = await OnPageCheck(page=self._target).evaluate(ctx)
            if on_target.passed:
                ctx.logger.info(
                    f"Navigation success: {self._target} "
                    f"(attempt {attempt})"
                )
                return OpResult(
                    success=True,
                    data={"page_id": self._target},
                )

            # Failed — re-detect and retry
            id_result = await IdentifyPageCheck().evaluate(ctx)
            current = id_result.data["page"] if id_result.data else "unknown"
            ctx.logger.warning(
                f"Navigation verify failed: expected={self._target}, "
                f"actual={current} (attempt {attempt})"
            )

        return OpResult(
            success=False,
            error=f"Failed to reach {self._target} after {_MAX_RETRIES} retries",
        )
