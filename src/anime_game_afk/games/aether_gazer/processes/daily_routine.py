"""Daily routine process.

Collects mail, claims free stamina, completes daily checklist.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.tasks_v2.navigation_tasks import (
    ReturnToHub,
)
from anime_game_afk.games.aether_gazer.tasks_v2.mail_tasks import CollectAllMail
from anime_game_afk.games.aether_gazer.tasks_v2.shop_tasks import ClaimFreeStamina
from anime_game_afk.games.aether_gazer.processes.base import (
    ProcessContext,
    ProcessResult,
)


class DailyRoutine:
    """Complete all daily tasks and claim rewards."""
    name = "daily_routine"
    description = "Collect mail, claim free stamina, do daily tasks"

    async def execute(self, ctx: ProcessContext) -> ProcessResult:
        hub = ReturnToHub()
        completed: list[str] = []

        await hub.execute(ctx)

        # Collect mail
        mail = CollectAllMail()
        if await mail.can_run(ctx):
            result = await mail.execute(ctx)
            if result.status == "success":
                completed.append("mail")

        await hub.execute(ctx)

        # Claim free stamina
        stamina = ClaimFreeStamina()
        if await stamina.can_run(ctx):
            result = await stamina.execute(ctx)
            if result.status == "success":
                completed.append("free_stamina")

        await hub.execute(ctx)

        return ProcessResult(
            status="success",
            data={"completed": completed},
        )
