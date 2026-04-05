"""Push main story process.

Navigates to story mode and clears stages until done or out of stamina.
This replaces the monolithic scripts/ch6_battle.py.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.tasks_v2.navigation_tasks import (
    ReturnToHub,
    EnterMainStory,
)
from anime_game_afk.games.aether_gazer.tasks_v2.combat_tasks import (
    ClearSingleStage,
)
from anime_game_afk.games.aether_gazer.processes.base import (
    ProcessContext,
    ProcessResult,
)


class PushMainStory:
    """Push main story from current progress."""
    name = "push_main_story"
    description = "Clear main story stages sequentially"

    async def execute(self, ctx: ProcessContext) -> ProcessResult:
        max_stages = ctx.config.get("max_stages", 20)
        stages_cleared = 0

        # Step 1: Return to hub
        hub = ReturnToHub()
        result = await hub.execute(ctx)
        if result.status != "success":
            return ProcessResult(status="failed", message="Cannot reach hub")

        # Step 2: Enter main story
        enter = EnterMainStory()
        result = await enter.execute(ctx)
        if result.status != "success":
            return ProcessResult(
                status="failed", message="Cannot enter story"
            )

        # Step 3: Clear stages in loop
        while stages_cleared < max_stages:
            stage = ClearSingleStage()
            result = await stage.execute(ctx)

            if result.status == "success":
                stages_cleared += 1
                ctx.logger.info(
                    f"Stage cleared: {stages_cleared}/{max_stages}"
                )
            else:
                ctx.logger.warning(
                    f"Stage failed, stopping: {result.message}"
                )
                break

        # Step 4: Return to hub
        await hub.execute(ctx)

        return ProcessResult(
            status="success",
            data={"stages_cleared": stages_cleared},
        )
