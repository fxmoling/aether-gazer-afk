"""Navigation tasks — multi-step page navigation.

Composes navigate ops with verification and retry logic.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.ops.navigate.return_to_hub import (
    ReturnToHubOp,
)
from anime_game_afk.games.aether_gazer.ops.navigate.goto_page import GotoPageOp
from anime_game_afk.games.aether_gazer.ops.primitives import ClickOp
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext, TaskResult


class ReturnToHub:
    """Ensure we are at the main hub."""
    name = "return_to_hub"
    description = "Navigate back to main hub from any page"
    category = "navigation"
    requires_pages = ("main_hub",)
    requires_ocr = False
    safe = True

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
    description = "Navigate from hub to main story stage map"
    category = "navigation"
    requires_pages = ("main_hub", "battle_select", "battle_intel", "main_story_map")
    requires_ocr = False
    safe = True

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
        await ClickOp(x=160, y=860, wait=1.5).run(ctx)   # 情报 tab
        await ClickOp(x=533, y=450, wait=2.0).run(ctx)   # Main story entry

        return TaskResult(status="success")
