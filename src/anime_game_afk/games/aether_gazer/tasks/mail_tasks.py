"""Mail tasks — collect all reward mail.

CollectAllMail opens the mailbox and collects every available reward.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.knowledge.keys import VK_H, VK_ENTER
from anime_game_afk.games.aether_gazer.ops.navigate.smart_return import (
    ReturnToHubAction,
)
from anime_game_afk.games.aether_gazer.ops.primitives import (
    ClickOp,
    PressKeyOp,
)
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext, TaskResult

# Verified coordinates (2026-04-06, 291,749 @ 1600x900, OCR verified)
_COLLECT_ALL_X, _COLLECT_ALL_Y = 0.182, 0.832   # 全部领取 button


class CollectAllMail:
    """Open mail panel and collect all available rewards."""
    name = "collect_all_mail"
    description = "Collect all reward mail from mailbox"
    category = "daily"
    requires_pages = ("main_hub", "mail")
    requires_ocr = False
    safe = True

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        ctx.logger.info("=== CollectAllMail: starting ===")

        # Step 1: H shortcut opens the mail panel from hub
        ctx.logger.info("[Step 1] Press H → mail")
        await PressKeyOp(VK_H, wait=1.0).run(ctx)

        # Step 2: Click "全部领取" (collect all) button
        ctx.logger.info(
            f"[Step 2] Click 全部领取 at ({_COLLECT_ALL_X},{_COLLECT_ALL_Y})"
        )
        await ClickOp(x=_COLLECT_ALL_X, y=_COLLECT_ALL_Y, wait=0.5).run(ctx)

        # Step 3: Dismiss reward popup (Enter or click)
        ctx.logger.info("[Step 3] Dismiss reward popup")
        await PressKeyOp(VK_ENTER, wait=1.0).run(ctx)
        # Click again in case multiple popups
        await ClickOp(x=_COLLECT_ALL_X, y=_COLLECT_ALL_Y, wait=1.0).run(ctx)
        await PressKeyOp(VK_ENTER, wait=1.0).run(ctx)

        # Step 4: Return to hub
        ctx.logger.info("[Step 4] Return to hub")
        await ReturnToHubAction().run(ctx)

        ctx.logger.info("=== CollectAllMail: complete ===")
        return TaskResult(status="success", data={"action": "mail_collected"})
