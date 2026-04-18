"""Amusement Street tasks — 游园街 daily management.

AmusementStreetDaily: Auto-place, feed, collect income, dispatch tasks.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from anime_game_afk.games.aether_gazer.checks.ocr import FindTextCheck
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ENTER, VK_ESCAPE
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

# Verified coordinates (2026-04-06, 1600x900, OCR verified)
_AMUSEMENT_X, _AMUSEMENT_Y = 0.786, 0.944      # Hub bottom bar 游园街 (1257,850 @ 1600x900)
_PANEL_X, _PANEL_Y = 0.775, 0.956               # 游园街面板 button (1240,860 @ 1600x900)
_AUTO_PLACE_X, _AUTO_PLACE_Y = 0.678, 0.918     # 自动放置 button (1084,826 @ 1600x900)
_FEED_X, _FEED_Y = 0.855, 0.918                 # 一键投喂 button (1368,826 @ 1600x900)


class AmusementStreetDaily:
    """Daily 游园街 management: place, feed, collect, dispatch, claim park tasks.

    Flow: hub → 游园街(1257,850) → 游园街面板(1240,860)
          → 自动放置(1084,826) → 一键投喂(1368,826)
          → 领取收益(OCR) → 派遣完成/可委托(OCR) → 确定(Enter)
          → 一键派遣(OCR) → 游园任务(OCR) → 一键领取(OCR)
          → dismiss popups → ESC×2 → return to hub

    Identification methods:
    - Fixed coord: 游园街, 游园街面板, 自动放置, 一键投喂
    - OCR: 领取收益, 派遣完成/可委托, 一键派遣, 游园任务, 一键领取
    - Keyboard: Enter (confirm), ESC (close panels)
    """

    name = "amusement_street_daily"
    description = "游园街: auto-place, feed, collect income, dispatch tasks"
    category = "daily"
    requires_pages = ("main_hub", "amusement")
    requires_ocr = True
    safe = True

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        run_log: RunLog | None = getattr(ctx, "run_log", None)
        ctx.logger.info("=== AmusementStreetDaily: starting ===")

        # Step 1: Click 游园街
        ctx.logger.info(f"[Step 1] Click 游园街 at ({_AMUSEMENT_X},{_AMUSEMENT_Y})")
        await ClickOp(x=_AMUSEMENT_X, y=_AMUSEMENT_Y, wait=1.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "amusement_page")

        # Step 2: Click 游园街面板
        ctx.logger.info(f"[Step 2] Click 游园街面板 at ({_PANEL_X},{_PANEL_Y})")
        await ClickOp(x=_PANEL_X, y=_PANEL_Y, wait=1.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "amusement_panel")

        # Step 3: 自动放置
        ctx.logger.info(
            f"[Step 3] Click 自动放置 at ({_AUTO_PLACE_X},{_AUTO_PLACE_Y})"
        )
        await ClickOp(x=_AUTO_PLACE_X, y=_AUTO_PLACE_Y, wait=1.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "amusement_auto_place")

        # Step 4: 一键投喂
        ctx.logger.info(f"[Step 4] Click 一键投喂 at ({_FEED_X},{_FEED_Y})")
        await ClickOp(x=_FEED_X, y=_FEED_Y, wait=1.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "amusement_after_feed")

        # Step 5: 领取收益 (OCR)
        ctx.logger.info("[Step 5] Find and click '领取收益'")
        income_result = await FindTextCheck(target="领取收益").evaluate(ctx)
        if income_result.passed:
            income = income_result.data
            cx = income.region.x + income.region.w // 2
            cy = income.region.y + income.region.h // 2
            ctx.logger.info(f"  Found '领取收益' at ({cx},{cy})")
            await ClickPxOp(px=cx, py=cy, wait=1.5).run(ctx)
            await PressKeyOp(key=VK_ENTER, wait=1.0).run(ctx)  # Dismiss reward popup
        else:
            ctx.logger.info("  '领取收益' not found (nothing to collect)")
        if run_log:
            run_log.snap(ctx.device, "amusement_after_income")

        # Step 6: Handle completed dispatches and re-dispatch
        ctx.logger.info("[Step 6] Handle completed dispatches")
        for dispatch_round in range(5):  # max 5 completed commissions

            # Check for reward popup first ("委托已完成" or "获得奖励")
            reward_result = await FindTextCheck(target="委托已完成").evaluate(ctx)
            if not reward_result.passed:
                reward_result = await FindTextCheck(target="获得奖励").evaluate(ctx)
            if reward_result.passed:
                ctx.logger.info(
                    f"  dispatch[{dispatch_round}]: reward popup found, "
                    f"clicking 确定 to dismiss"
                )
                # Enter does NOT work for this popup — must click 确定
                confirm_result = await FindTextCheck(target="确定").evaluate(ctx)
                if confirm_result.passed:
                    confirm = confirm_result.data
                    bx = confirm.region.x + confirm.region.w // 2
                    by = confirm.region.y + confirm.region.h // 2
                    await ClickPxOp(px=bx, py=by, wait=1.5).run(ctx)
                else:
                    await ClickOp(x=0.5, y=0.917, wait=1.5).run(ctx)  # fallback (800,825 @ 1600x900)
                continue

            # Check if we're on the dispatch task selection panel
            # (航海达人/渔获超载 etc.) — click 一键派遣 immediately
            auto_d_result = await FindTextCheck(target="一键派遣").evaluate(ctx)
            if auto_d_result.passed:
                auto_d = auto_d_result.data
                dx = auto_d.region.x + auto_d.region.w // 2
                dy = auto_d.region.y + auto_d.region.h // 2
                ctx.logger.info(
                    f"  dispatch[{dispatch_round}]: clicking 一键派遣 "
                    f"at ({dx},{dy})"
                )
                await ClickPxOp(px=dx, py=dy, wait=1.5).run(ctx)
                # Dismiss any confirmation popup
                popup_confirm = await FindTextCheck(target="确定").evaluate(ctx)
                if popup_confirm.passed:
                    pc = popup_confirm.data
                    bx = pc.region.x + pc.region.w // 2
                    by = pc.region.y + pc.region.h // 2
                    await ClickPxOp(px=bx, py=by, wait=1.0).run(ctx)
                else:
                    await PressKeyOp(key=VK_ENTER, wait=1.0).run(ctx)
                if run_log:
                    run_log.snap(
                        ctx.device, f"amusement_dispatch_{dispatch_round}"
                    )
                # After dispatching, click bottom empty area to exit panel
                # (ESC doesn't work here; click left of 一键派遣 button)
                await ClickOp(x=0.563, y=0.867, wait=1.0).run(ctx)
                continue

            # Look for "派遣完成" or "可委托" on the amusement panel overview
            dispatch_result = await FindTextCheck(target="派遣完成").evaluate(ctx)
            if not dispatch_result.passed:
                dispatch_result = await FindTextCheck(target="可委托").evaluate(ctx)
            if dispatch_result.passed:
                dispatch = dispatch_result.data
                cx = dispatch.region.x + dispatch.region.w // 2
                cy = dispatch.region.y + dispatch.region.h // 2
                ctx.logger.info(
                    f"  dispatch[{dispatch_round}]: found '派遣完成' "
                    f"at ({cx},{cy})"
                )
                await ClickPxOp(px=cx, py=cy, wait=1.5).run(ctx)
                continue

            # Nothing actionable found — done
            ctx.logger.info(
                f"  dispatch[{dispatch_round}]: no more dispatch targets"
            )
            break

        if run_log:
            run_log.snap(ctx.device, "amusement_after_dispatch")

        # Step 7: ESC back to street page, then claim 游园任务 rewards
        # 游园任务 button is on the STREET page (bottom bar), NOT the panel.
        # Verified from 04_amusement_street.png vs 05_amusement_panel.png.
        ctx.logger.info("[Step 7] ESC to street → click 游园任务 → claim rewards")
        await PressKeyOp(key=VK_ESCAPE, wait=1.5).run(ctx)

        # Fixed coord: 游园任务 button on street bottom bar (0.621, 0.944)
        _PARK_TASK_X, _PARK_TASK_Y = 0.621, 0.944
        ctx.logger.info(
            f"  clicking 游园任务 at ({_PARK_TASK_X},{_PARK_TASK_Y})"
        )
        await ClickOp(x=_PARK_TASK_X, y=_PARK_TASK_Y, wait=1.5).run(ctx)

        # OCR find 一键领取 on the park task panel
        claim_result = await FindTextCheck(target="一键领取").evaluate(ctx)
        if claim_result.passed:
            claim = claim_result.data
            cx = claim.region.x + claim.region.w // 2
            cy = claim.region.y + claim.region.h // 2
            ctx.logger.info(f"  Found '一键领取' at ({cx},{cy})")
            await ClickPxOp(px=cx, py=cy, wait=1.0).run(ctx)
        else:
            ctx.logger.info("  '一键领取' not found (no rewards to claim)")

        # Dismiss popups: Enter ×3
        for _ in range(3):
            await PressKeyOp(key=VK_ENTER, wait=0.5).run(ctx)
        # Click top-center ×2 to dismiss remaining overlays
        await ClickOp(x=0.5, y=0.005, wait=0.5).run(ctx)
        await ClickOp(x=0.5, y=0.005, wait=0.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "amusement_after_park_tasks")

        # Step 8: ESC + return to hub (only 1 ESC needed — already on street)
        ctx.logger.info("[Step 8] ESC + return to hub")
        await PressKeyOp(key=VK_ESCAPE, wait=1.0).run(ctx)
        await ReturnToHubAction().run(ctx)
        if run_log:
            run_log.snap(ctx.device, "amusement_done")

        ctx.logger.info("=== AmusementStreetDaily: complete ===")
        return TaskResult(
            status="success",
            data={"task": "amusement_street"},
        )
