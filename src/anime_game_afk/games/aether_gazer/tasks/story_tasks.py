"""Story navigation tasks — chapter and stage selection.

NavigateToChapter scrolls to a chapter in the stage map.
SelectLatestStage picks the last available (uncompleted) stage.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.ops.primitives import ClickOp
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext, TaskResult

# Approximate row height between chapter entries in the stage select scroll list
_CHAPTER_ROW_HEIGHT = 80


class NavigateToChapter:
    """Scroll to a specific chapter in the main story map."""
    name = "navigate_to_chapter"
    description = "Navigate to a specific story chapter"
    category = "navigation"
    requires_pages = ("main_story_map",)
    requires_ocr = False
    safe = True

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
        # Original pixel formula: target_y = 200 + chapter * 80
        target_y = (200 + self._chapter * _CHAPTER_ROW_HEIGHT) / 900
        await ClickOp(x=0.5, y=target_y, wait=1.5).run(ctx)  # x=800 @ 1600x900

        ctx.logger.info(f"Navigated to chapter index {self._chapter}")
        return TaskResult(
            status="success", data={"chapter": self._chapter}
        )


class SelectLatestStage:
    """Select the latest available (in-progress) stage."""
    name = "select_latest_stage"
    description = "Select the latest uncompleted stage on story map"
    category = "navigation"
    requires_pages = ("main_story_map",)
    requires_ocr = False
    safe = True

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        # The latest stage entry is typically highlighted/marked differently.
        # Click the currently active stage, which tends to be near the center
        # of the stage list column.
        await ClickOp(x=0.333, y=0.5, wait=2.0).run(ctx)   # Active stage area (533,450 @ 1600x900, center-left)

        ctx.logger.info("Selected latest/active stage")
        return TaskResult(
            status="success", data={"action": "stage_selected"}
        )
