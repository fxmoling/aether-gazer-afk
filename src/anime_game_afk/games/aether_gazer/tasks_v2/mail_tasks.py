"""Mail tasks — collect all reward mail.

CollectAllMail opens the mailbox and collects every available reward.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.keys import VK_H, VK_ESCAPE
from anime_game_afk.games.aether_gazer.tasks_v2.base import TaskContext, TaskResult


class CollectAllMail:
    """Open mail panel and collect all available rewards."""
    name = "collect_all_mail"

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        # H shortcut opens the mail panel from hub
        ctx.device.press_key(VK_H)
        await asyncio.sleep(2.0)

        # Click "Collect All" button
        ctx.device.click(1400, 820)   # Collect All button position
        await asyncio.sleep(1.5)

        # Confirm if needed
        ctx.device.click(800, 550)   # Confirmation area
        await asyncio.sleep(1.5)

        # Close mail panel
        ctx.device.press_key(VK_ESCAPE)
        await asyncio.sleep(1.0)

        ctx.logger.info("All mail collected")
        return TaskResult(status="success", data={"action": "mail_collected"})
