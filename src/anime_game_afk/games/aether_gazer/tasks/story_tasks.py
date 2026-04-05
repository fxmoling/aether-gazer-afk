"""Story navigation tasks — chapter and stage selection.

NavigateToChapter scrolls to a chapter in the stage map.
SelectLatestStage picks the last available (uncompleted) stage.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.tasks.base import TaskContext, TaskResult

# Approximate row height between chapter entries in the stage select scroll list
_CHAPTER_ROW_HEIGHT = 80


class NavigateToChapter:
    """Scroll to a specific chapter in the main story map."""
    name = "navigate_to_chapter"

    def __init__(self, chapter_index: int = 0) -> None:
        self._chapter = chapter_index

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        if self._chapter <= 0:
            # Default: stay at current chapter
            return TaskResult(status="success", data={"chapter": 0})

        # Scroll down by clicking a relative position for the target chapter.
        # Chapter entries are stacked vertically; each chapter_index step
        # moves one row down from the top of the list area.
        target_y = 200 + self._chapter * _CHAPTER_ROW_HEIGHT
        ctx.device.click(800, target_y)
        await asyncio.sleep(1.5)

        ctx.logger.info(f"Navigated to chapter index {self._chapter}")
        return TaskResult(
            status="success", data={"chapter": self._chapter}
        )


class SelectLatestStage:
    """Select the latest available (in-progress) stage."""
    name = "select_latest_stage"

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        # The latest stage entry is typically highlighted/marked differently.
        # Click the currently active stage, which tends to be near the center
        # of the stage list column.
        ctx.device.click(533, 450)   # Active stage area (center-left)
        await asyncio.sleep(2.0)

        ctx.logger.info("Selected latest/active stage")
        return TaskResult(
            status="success", data={"action": "stage_selected"}
        )
