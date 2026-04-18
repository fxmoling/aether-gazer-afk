"""Guild tasks — daily guild rewards.

GuildSupplyClaim: Claim daily 矩阵补给 from guild page.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from anime_game_afk.games.aether_gazer.checks.ocr import FindTextCheck
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ENTER
from anime_game_afk.games.aether_gazer.ops.navigate.smart_return import (
    ReturnToHubAction,
)
from anime_game_afk.games.aether_gazer.ops.primitives import (
    ClickPxOp,
    ClickOp,
    PressKeyOp,
    SleepOp,
)
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext, TaskResult

if TYPE_CHECKING:
    from anime_game_afk.runtime.run_log import RunLog

# Verified coordinates (2026-04-06, 1025,850 @ 1600x900)
_GUILD_X, _GUILD_Y = 0.641, 0.944  # Hub bottom bar 公会 button


class GuildSupplyClaim:
    """Claim daily 矩阵补给 (Matrix Supply) from guild.

    Flow: hub → 公会(1025,850) → 矩阵补给(OCR) → 领取(OCR) → return to hub

    Identification methods:
    - Fixed coord: 公会 button on hub bottom bar
    - OCR: 矩阵补给 (bottom bar of guild page), 领取 (claim button)
    """

    name = "guild_supply_claim"
    description = "Claim daily 矩阵补给 from guild"
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
        await ClickOp(x=_GUILD_X, y=_GUILD_Y, wait=1.0).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "guild_page")

        # Step 2: Find and click 矩阵补给
        ctx.logger.info("[Step 2] Find and click '矩阵补给'")
        supply_result = await FindTextCheck(target="矩阵补给").evaluate(ctx)
        if supply_result.passed:
            supply = supply_result.data
            cx = supply.region.x + supply.region.w // 2
            cy = supply.region.y + supply.region.h // 2
            ctx.logger.info(f"  Found '矩阵补给' at ({cx},{cy})")
            await ClickPxOp(px=cx, py=cy, wait=2.0).run(ctx)
        else:
            # OCR can't find the button — skip to avoid clicking wrong things
            ctx.logger.warning(
                "  '矩阵补给' not found via OCR, skipping guild supply"
            )
            await ReturnToHubAction().run(ctx)
            return TaskResult(
                status="skipped",
                message="矩阵补给 button not found via OCR",
            )
        if run_log:
            run_log.snap(ctx.device, "guild_supply")

        # Step 3: Find and click 领取
        ctx.logger.info("[Step 3] Find and click '领取'")
        claim_result = await FindTextCheck(target="领取").evaluate(ctx)
        claimed = False
        if claim_result.passed:
            claim = claim_result.data
            cx = claim.region.x + claim.region.w // 2
            cy = claim.region.y + claim.region.h // 2
            ctx.logger.info(f"  Found '领取' at ({cx},{cy})")
            await ClickPxOp(px=cx, py=cy, wait=1.5).run(ctx)
            # Dismiss reward popup
            await PressKeyOp(key=VK_ENTER, wait=1.0).run(ctx)
            claimed = True
            if run_log:
                run_log.snap(ctx.device, "guild_after_claim")
        else:
            ctx.logger.info("  '领取' not found (already claimed today)")

        # Step 4: Return to hub
        ctx.logger.info("[Step 4] Return to hub")
        await ReturnToHubAction().run(ctx)
        if run_log:
            run_log.snap(ctx.device, "guild_done")

        status = "success" if claimed else "skipped"
        msg = "Guild supply claimed" if claimed else "Already claimed today"
        ctx.logger.info(f"=== GuildSupplyClaim: {status} ===")
        return TaskResult(status=status, message=msg, data={"claimed": claimed})
