"""Shop tasks — daily shop item purchases.

ClaimFreeStamina opens the shop and claims the free daily stamina pack.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ESCAPE
from anime_game_afk.games.aether_gazer.ops.navigate.goto_page import GotoPageOp
from anime_game_afk.games.aether_gazer.tasks_v2.base import TaskContext, TaskResult


class ClaimFreeStamina:
    """Claim the free daily stamina from the shop."""
    name = "claim_free_stamina"

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        # Navigate to shop page
        goto = GotoPageOp(target_page_id="shop")
        result = await goto.run(ctx)
        if not result.success:
            return TaskResult(status="failed", message="Cannot reach shop")

        # Click the free stamina entry (daily free section)
        ctx.device.click(800, 400)   # Free item area
        await asyncio.sleep(1.5)

        # Confirm purchase
        ctx.device.click(800, 600)   # Confirm button
        await asyncio.sleep(1.5)

        # Dismiss any popup
        ctx.device.press_key(VK_ESCAPE)
        await asyncio.sleep(1.0)

        ctx.logger.info("Free stamina claimed from shop")
        return TaskResult(status="success", data={"claimed": "free_stamina"})
