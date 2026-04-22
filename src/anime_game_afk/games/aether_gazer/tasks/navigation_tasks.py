"""Navigation tasks — multi-step page navigation.

Composes navigate ops with verification and retry logic.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.ops.navigate.smart_return import (
    ReturnToHubAction,
)
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
        op = ReturnToHubAction()
        result = await op.run(ctx)
        if result.success:
            return TaskResult(status="success")
        return TaskResult(status="failed", message="Could not return to hub")
