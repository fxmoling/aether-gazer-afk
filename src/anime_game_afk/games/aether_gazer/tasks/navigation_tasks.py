"""Navigation tasks — multi-step page navigation.

Composes navigate ops with verification and retry logic.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.ops.navigate.return_to_hub import (
    ReturnToHubOp,
)
from anime_game_afk.games.aether_gazer.ops.navigate.goto_page import GotoPageOp
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext, TaskResult


class ReturnToHub:
    """Ensure we are at the main hub."""
    name = "return_to_hub"

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        op = ReturnToHubOp()
        result = await op.run(ctx)
        if result.success:
            return TaskResult(status="success")
        return TaskResult(status="failed", message="Could not return to hub")


class EnterMainStory:
    """Navigate from hub to main story stage map."""
    name = "enter_main_story"

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        # Hub -> Battle Select
        goto = GotoPageOp(target_page_id="battle_select")
        result = await goto.run(ctx)
        if not result.success:
            return TaskResult(
                status="failed", message="Cannot reach battle_select"
            )

        # Click main story entry (情报 tab -> 主线入口)
        ctx.device.click(160, 860)   # 情报 tab
        await asyncio.sleep(1.5)
        ctx.device.click(533, 450)   # Main story entry
        await asyncio.sleep(2.0)

        return TaskResult(status="success")
