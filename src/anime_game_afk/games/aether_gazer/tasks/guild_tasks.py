"""Guild tasks — daily guild rewards.

GuildSupplyClaim: Claim daily 矩阵补给 + 公会任务 rewards from guild page.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from anime_game_afk.games.aether_gazer.checks.ocr import FindTextCheck
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ENTER, VK_ESCAPE
from anime_game_afk.games.aether_gazer.ops.navigate.smart_return import (
    ReturnToHubAction,
)
from anime_game_afk.games.aether_gazer.ops.primitives import (
    ClickOp,
    PressKeyOp,
    SleepOp,
)
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext, TaskResult

if TYPE_CHECKING:
    from anime_game_afk.runtime.run_log import RunLog

# Hub bottom bar 公会 button (1025,850 @ 1600x900)
_GUILD_X, _GUILD_Y = 0.641, 0.944

# Guild bottom bar tabs (verified from guild_main.png at 1280×720)
_SUPPLY_TAB_X, _SUPPLY_TAB_Y = 0.926, 0.958    # 矩阵补给 tab
_TASK_TAB_X, _TASK_TAB_Y = 0.797, 0.958         # 公会任务 tab

# 领取 button inside 矩阵补给 panel (verified from 02_guild_supply_panel.png)
_SUPPLY_CLAIM_X, _SUPPLY_CLAIM_Y = 0.5, 0.71

# 一键领取 button for 公会任务 (verified from 03_guild_task_panel.png)
_GUILD_DAILY_CLAIM_X, _GUILD_DAILY_CLAIM_Y = 0.898, 0.919


class GuildSupplyClaim:
    """Claim daily 矩阵补给 and 公会任务 rewards from guild.

    Flow: hub → 公会 → OCR verify 矩阵补给 (guild membership check)
          → click 矩阵补给 tab → 领取 (fixed coord) → Enter
          → click 公会任务 tab → 一键领取 → Enter → return to hub

    If OCR cannot find 矩阵补给, user likely has no guild — skip entirely.

    Identification methods:
    - Fixed coord: 公会 button, guild bottom bar tabs, 领取, 一键领取
    - OCR: 矩阵补给 text (guild membership verification only)
    """

    name = "guild_supply_claim"
    description = "Claim daily 矩阵补给 and 公会任务 rewards"
    category = "daily"
    requires_pages = ("main_hub", "guild")
    requires_ocr = True
    safe = True

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        run_log: RunLog | None = getattr(ctx, "run_log", None)
        ctx.logger.info("=== GuildSupplyClaim: starting ===")

        # Step 1: Click 公会
        ctx.logger.info(f"[Step 1] Click 公会 at ({_GUILD_X},{_GUILD_Y})")
        await ClickOp(x=_GUILD_X, y=_GUILD_Y, wait=1.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "guild_page")

        # Step 2: Verify guild membership via OCR
        ctx.logger.info("[Step 2] OCR verify '矩阵补给' (guild membership check)")
        supply_result = await FindTextCheck(target="矩阵补给").evaluate(ctx)
        if not supply_result.passed:
            ctx.logger.warning(
                "  '矩阵补给' not found — user may not be in a guild, skipping"
            )
            await ReturnToHubAction().run(ctx)
            return TaskResult(
                status="skipped",
                message="矩阵补给 not found (no guild membership)",
            )

        # Step 3: Click 矩阵补给 tab (fixed coord from guild bottom bar)
        ctx.logger.info(
            f"[Step 3] Click 矩阵补给 tab at ({_SUPPLY_TAB_X},{_SUPPLY_TAB_Y})"
        )
        await ClickOp(x=_SUPPLY_TAB_X, y=_SUPPLY_TAB_Y, wait=1.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "guild_supply_panel")

        # Step 4: Click 领取 at fixed position
        ctx.logger.info(
            f"[Step 4] Click 领取 at ({_SUPPLY_CLAIM_X},{_SUPPLY_CLAIM_Y})"
        )
        await ClickOp(x=_SUPPLY_CLAIM_X, y=_SUPPLY_CLAIM_Y, wait=1.0).run(ctx)
        # Dismiss reward popup
        await PressKeyOp(key=VK_ENTER, wait=1.0).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "guild_after_supply_claim")

        # Step 5: ESC to close supply panel overlay, then click 公会任务 tab
        ctx.logger.info("[Step 5] ESC to close supply panel")
        await PressKeyOp(key=VK_ESCAPE, wait=1.5).run(ctx)

        ctx.logger.info(
            f"[Step 5] Click 公会任务 tab at ({_TASK_TAB_X},{_TASK_TAB_Y})"
        )
        await ClickOp(x=_TASK_TAB_X, y=_TASK_TAB_Y, wait=1.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "guild_task_panel")

        # Step 6: Click 一键领取
        ctx.logger.info(
            f"[Step 6] Click 一键领取 at "
            f"({_GUILD_DAILY_CLAIM_X},{_GUILD_DAILY_CLAIM_Y})"
        )
        await ClickOp(
            x=_GUILD_DAILY_CLAIM_X, y=_GUILD_DAILY_CLAIM_Y, wait=1.0,
        ).run(ctx)
        # Dismiss reward popup
        await PressKeyOp(key=VK_ENTER, wait=1.0).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "guild_after_task_claim")

        # Step 7: Return to hub
        ctx.logger.info("[Step 7] Return to hub")
        await ReturnToHubAction().run(ctx)
        if run_log:
            run_log.snap(ctx.device, "guild_done")

        ctx.logger.info("=== GuildSupplyClaim: complete ===")
        return TaskResult(
            status="success",
            message="Guild supply + task rewards claimed",
            data={"supply_claimed": True, "task_claimed": True},
        )
