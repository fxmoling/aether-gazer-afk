"""Daily routine process.

Collects mail, claims free stamina, completes daily checklist.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.tasks.navigation_tasks import (
    ReturnToHub,
)
from anime_game_afk.games.aether_gazer.tasks.mail_tasks import CollectAllMail
from anime_game_afk.games.aether_gazer.tasks.shop_tasks import ClaimFreeStamina
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

        # Must reach hub first
        result = await hub.execute(ctx)
        if result.status != "success":
            return ProcessResult(status="failed", message="Cannot reach hub")

        # Collect mail
        try:
            mail = CollectAllMail()
            if await mail.can_run(ctx):
                result = await mail.execute(ctx)
                if result.status == "success":
                    completed.append("mail")
        except Exception as exc:
            ctx.logger.error(f"Mail task crashed: {exc}")

        await hub.execute(ctx)

        # Claim free stamina
        try:
            stamina = ClaimFreeStamina()
            if await stamina.can_run(ctx):
                result = await stamina.execute(ctx)
                if result.status == "success":
                    completed.append("free_stamina")
        except Exception as exc:
            ctx.logger.error(f"Stamina task crashed: {exc}")

        await hub.execute(ctx)

        return ProcessResult(
            status="success",
            data={"completed": completed},
        )
