"""Observation, mission, and protocol tasks.

MimiStationCollect: Collect rewards from 弥弥观测站 and shorten return.
DailyWeeklyMissionClaim: Claim daily + weekly mission rewards.
TacticsTaskClaim: Claim 对策协议 task rewards.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from anime_game_afk.games.aether_gazer.checks.ocr import FindTextCheck
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_G, VK_T
from anime_game_afk.games.aether_gazer.ops.interact.rapid_click import (
    RapidClickAction,
)
from anime_game_afk.games.aether_gazer.ops.navigate.smart_return import (
    ReturnToHubAction,
)
from anime_game_afk.games.aether_gazer.ops.primitives import (
    ClickOp,
    ClickPxOp,
    PressKeyOp,
)
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext, TaskResult

if TYPE_CHECKING:
    from anime_game_afk.runtime.run_log import RunLog


# Verified coordinates (2026-04-06, 1600x900 design resolution)
# 弥弥观测站 button in daily tasks page (110,820 @ 1600x900)
_MIMI_STATION_X, _MIMI_STATION_Y = 0.069, 0.911
# 一键领取 button in 弥弥观测站 (1205,809 @ 1600x900, OCR verified center)
_MIMI_CLAIM_X, _MIMI_CLAIM_Y = 0.753, 0.899
# 每日任务 一键领取 button (1480,860 @ 1600x900, right-bottom of daily tasks page)
_DAILY_CLAIM_X, _DAILY_CLAIM_Y = 0.925, 0.956
# 周常任务 tab (estimated, left sidebar below 每日任务)
# Note: (0.05, 0.217) was proven wrong — that's the 每日任务 tab itself.
# Fallback coord only; prefer OCR to find the tab.
_WEEKLY_TAB_X, _WEEKLY_TAB_Y = 0.05, 0.30


class MimiStationCollect:
    """Collect rewards from 弥弥观测站 and shorten return time.

    Flow: hub → G(daily tasks) → 弥弥观测站(110,820) → 一键领取(1205,809) ×20
          → x10(OCR, weekly reward) ×20 → return to hub

    x10 is a weekly one-time reward (higher multiplier = better value).
    Only clicks when x10 is available; skips if not found.

    Identification methods:
    - Keyboard: G shortcut opens daily tasks
    - Fixed coord: 弥弥观测站 button, 一键领取 button
    - OCR: x10 缩短遣回 button (weekly reward, dynamic position)
    """

    name = "mimi_station_collect"
    description = "Collect 弥弥观测站 rewards and shorten return time"
    category = "daily"
    requires_pages = ("main_hub", "daily_tasks")
    requires_ocr = True
    safe = True

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        run_log: RunLog | None = getattr(ctx, "run_log", None)
        ctx.logger.info("=== MimiStationCollect: starting ===")

        # Step 1: G → daily tasks
        ctx.logger.info("[Step 1] Press G → daily tasks")
        await PressKeyOp(VK_G, wait=1.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "mimi_daily_tasks")

        # Step 2: Click 弥弥观测站
        ctx.logger.info(
            f"[Step 2] Click 弥弥观测站 at ({_MIMI_STATION_X},{_MIMI_STATION_Y})"
        )
        await ClickOp(x=_MIMI_STATION_X, y=_MIMI_STATION_Y, wait=0.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "mimi_station")

        # Step 3: 一键领取 ×20
        ctx.logger.info(
            f"[Step 3] Rapid click 一键领取 at ({_MIMI_CLAIM_X},{_MIMI_CLAIM_Y}) ×20"
        )
        await RapidClickAction(
            x=_MIMI_CLAIM_X, y=_MIMI_CLAIM_Y, times=20, interval=0.15,
        ).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "mimi_after_claim")

        # Step 4: Return to hub
        ctx.logger.info("[Step 4] Return to hub")
        await ReturnToHubAction().run(ctx)
        if run_log:
            run_log.snap(ctx.device, "mimi_done")

        ctx.logger.info("=== MimiStationCollect: complete ===")
        return TaskResult(status="success", data={"task": "mimi_station"})


class DailyWeeklyMissionClaim:
    """Claim daily and weekly mission rewards.

    Flow: hub → G(daily tasks) → 一键领取(1480,860) ×5 (daily)
          → 周常任务(OCR) → 一键领取(1480,860) ×5 (weekly)
          → return to hub

    Identification methods:
    - Keyboard: G shortcut, ESC to close
    - Fixed coord: 一键领取 button
    - OCR: 周常任务 tab (fixed coord unreliable across resolutions)

    Rapid clicks (×5) dismiss any popup that appears after claiming.
    """

    name = "daily_weekly_mission_claim"
    description = "Claim daily and weekly mission rewards"
    category = "daily"
    requires_pages = ("main_hub", "daily_tasks")
    requires_ocr = True
    safe = True

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        run_log: RunLog | None = getattr(ctx, "run_log", None)
        ctx.logger.info("=== DailyWeeklyMissionClaim: starting ===")

        # Step 1: G → daily tasks
        ctx.logger.info("[Step 1] Press G → daily tasks")
        await PressKeyOp(VK_G, wait=1.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "mission_daily_tasks")

        # Step 2: 一键领取 ×5 (daily)
        ctx.logger.info(
            f"[Step 2] Rapid click 一键领取 at "
            f"({_DAILY_CLAIM_X},{_DAILY_CLAIM_Y}) ×5 (daily)"
        )
        await RapidClickAction(
            x=_DAILY_CLAIM_X, y=_DAILY_CLAIM_Y, times=5, interval=0.5,
        ).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "mission_after_daily")

        # Step 3: Switch to 周常任务 (OCR-based, fixed coord unreliable)
        ctx.logger.info("[Step 3] Find and click '周常任务' tab via OCR")
        weekly_result = await FindTextCheck(target="周常任务").evaluate(ctx)
        if weekly_result.passed:
            weekly = weekly_result.data
            wx = weekly.region.x + weekly.region.w // 2
            wy = weekly.region.y + weekly.region.h // 2
            ctx.logger.info(f"  Found '周常任务' at ({wx},{wy})")
            await ClickPxOp(px=wx, py=wy, wait=1.5).run(ctx)
        else:
            ctx.logger.warning(
                "  '周常任务' not found via OCR, using fallback coord"
            )
            await ClickOp(x=_WEEKLY_TAB_X, y=_WEEKLY_TAB_Y, wait=1.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "mission_weekly")

        # Step 4: 一键领取 ×5 (weekly)
        ctx.logger.info(
            f"[Step 4] Rapid click 一键领取 at "
            f"({_DAILY_CLAIM_X},{_DAILY_CLAIM_Y}) ×5 (weekly)"
        )
        await RapidClickAction(
            x=_DAILY_CLAIM_X, y=_DAILY_CLAIM_Y, times=5, interval=0.5,
        ).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "mission_after_weekly")

        # Step 5: Return to hub
        ctx.logger.info("[Step 5] Return to hub")
        await PressKeyOp(0x1B, wait=1.0).run(ctx)  # ESC
        await ReturnToHubAction().run(ctx)
        if run_log:
            run_log.snap(ctx.device, "mission_done")

        ctx.logger.info("=== DailyWeeklyMissionClaim: complete ===")
        return TaskResult(status="success", data={"task": "daily_weekly_claim"})


# Verified coordinates (2026-04-06, 1600x900)
# 对策协议 — tasks button and claim button
_TACTICS_TASK_X, _TACTICS_TASK_Y = 0.101, 0.932     # 任务 button (162,839 @ 1600x900, OCR verified 2026-04-06)
_TACTICS_CLAIM_X, _TACTICS_CLAIM_Y = 0.925, 0.956   # 一键领取 button (1480,860 @ 1600x900, right-bottom)


class TacticsTaskClaim:
    """Claim 对策协议 (Tactics Protocol) task rewards.

    Flow: hub → T(对策协议) → 任务(162,839) → 一键领取(1480,860) ×3 → return to hub

    Identification methods:
    - Keyboard: T shortcut opens tactics protocol
    - Fixed coord: 任务 button, 一键领取 button
    """

    name = "tactics_task_claim"
    description = "Claim 对策协议 task rewards"
    category = "daily"
    requires_pages = ("main_hub", "tactics")
    requires_ocr = False
    safe = True

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        run_log: RunLog | None = getattr(ctx, "run_log", None)
        ctx.logger.info("=== TacticsTaskClaim: starting ===")

        # Step 1: T → 对策协议
        ctx.logger.info("[Step 1] Press T → 对策协议")
        await PressKeyOp(VK_T, wait=1.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "tactics_page")

        # Step 2: Click 任务 button (left-bottom)
        ctx.logger.info(
            f"[Step 2] Click 任务 at ({_TACTICS_TASK_X},{_TACTICS_TASK_Y})"
        )
        await ClickOp(x=_TACTICS_TASK_X, y=_TACTICS_TASK_Y, wait=1.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "tactics_tasks")

        # Step 3: 一键领取 ×3
        ctx.logger.info(
            f"[Step 3] Rapid click 一键领取 at "
            f"({_TACTICS_CLAIM_X},{_TACTICS_CLAIM_Y}) ×3"
        )
        await RapidClickAction(
            x=_TACTICS_CLAIM_X, y=_TACTICS_CLAIM_Y, times=3, interval=0.5,
        ).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "tactics_after_claim")

        # Step 4: Return to hub
        ctx.logger.info("[Step 4] Return to hub")
        await ReturnToHubAction().run(ctx)
        if run_log:
            run_log.snap(ctx.device, "tactics_done")

        ctx.logger.info("=== TacticsTaskClaim: complete ===")
        return TaskResult(status="success", data={"task": "tactics_claim"})
