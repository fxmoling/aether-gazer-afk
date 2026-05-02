"""Daily routine process.

Runs all daily tasks in sequence. Each task is wrapped in try/except
so one failure doesn't block the rest. Returns to hub between tasks.

Task order:
1. 领取所有邮件 — Collect all mail
2. 购买情报碎片 — Buy intel shards from daily shop
3. 领取吨吨值福利包 — Claim daily stamina packs
4. 领取商店免费体力 — Claim free stamina from shop supply
5. 弥弥观测站 — Collect rewards + shorten return
6. 公会矩阵补给 — Guild supply claim
7. 游园街日常管理 — Amusement street daily
8. 联防协议扫荡 — Joint Defense sweep (震动)
9. 联合特勤 — Joint Special Ops sweep (S级)
10. 介质攫取 — Medium Seizure combat + reward claim
11. 每日/周常任务领取 — Daily + weekly mission rewards
12. 对策协议任务领取 — Tactics Protocol task rewards
"""
from __future__ import annotations

import time
from typing import Any

from anime_game_afk.games.aether_gazer.tasks.navigation_tasks import ReturnToHub
from anime_game_afk.games.aether_gazer.tasks.mail_tasks import CollectAllMail
from anime_game_afk.games.aether_gazer.tasks.shop_tasks import (
    BuyIntelShards,
    ClaimDailyStaminaPacks,
    ClaimFreeStamina,
)
from anime_game_afk.games.aether_gazer.tasks.observation_tasks import (
    MimiStationCollect,
    DailyWeeklyMissionClaim,
    TacticsTaskClaim,
)
from anime_game_afk.games.aether_gazer.tasks.guild_tasks import GuildSupplyClaim
from anime_game_afk.games.aether_gazer.tasks.amusement_tasks import (
    AmusementStreetDaily,
)
from anime_game_afk.games.aether_gazer.tasks.activity_tasks import (
    JointDefenseSweep,
)
from anime_game_afk.games.aether_gazer.tasks.keyin_tasks import (
    MediumSeizureCombat,
    JointSpecialOpsSweep,
)
from anime_game_afk.games.aether_gazer.tasks.startup_tasks import (
    SkipStartupPopups,
)
from anime_game_afk.games.aether_gazer.processes.base import (
    ProcessContext,
    ProcessResult,
)


# All daily tasks: (id, class, display_name, safe)
_DAILY_TASKS: list[tuple[str, type, str, bool]] = [
    ("startup", SkipStartupPopups, "启动游戏", True),
    ("mail", CollectAllMail, "领取邮件", True),
    ("intel_shards", BuyIntelShards, "购买情报", False),
    ("stamina_packs", ClaimDailyStaminaPacks, "领取体力包", True),
    ("free_stamina", ClaimFreeStamina, "商店免费体力", True),
    ("mimi_station", MimiStationCollect, "弥弥观测站", True),
    ("guild_supply", GuildSupplyClaim, "公会补给", True),
    ("amusement", AmusementStreetDaily, "游园街日常", True),
    ("joint_defense", JointDefenseSweep, "联防协议", False),
    ("joint_special_ops", JointSpecialOpsSweep, "联合特勤", False),
    ("medium_seizure", MediumSeizureCombat, "介质攫取", False),
    ("missions", DailyWeeklyMissionClaim, "每日周常任务", True),
    ("tactics", TacticsTaskClaim, "对策协议", True),
]


class DailyRoutine:
    """Complete all daily tasks and claim rewards.

    Runs tasks in sequence, returning to hub between each.
    Each task failure is caught independently.

    Supports ``ctx.config["enabled_tasks"]`` to filter which tasks run.
    If not set, all tasks run (backward compatible).
    """
    name = "每日任务"
    description = "自动完成每日任务：邮件、商店、体力、公会、游园街等"

    @classmethod
    def task_defs(cls) -> list[dict[str, Any]]:
        """Return task metadata for UI discovery."""
        return [
            {
                "id": task_id,
                "name": display_name,
                "description": task_cls().description
                if hasattr(task_cls, "description") else "",
                "safe": safe,
            }
            for task_id, task_cls, display_name, safe in _DAILY_TASKS
        ]

    async def execute(self, ctx: ProcessContext) -> ProcessResult:
        hub = ReturnToHub()
        completed: list[str] = []
        failed: list[str] = []

        enabled_tasks: set[str] | None = None
        raw = ctx.config.get("enabled_tasks")
        if raw is not None:
            enabled_tasks = set(raw)

        game_was_launched = ctx.config.get("game_was_launched", False)

        ctx.logger.info("=== DailyRoutine: starting ===")

        # Log full task list: enabled vs disabled
        for task_id, _cls, display, _safe in _DAILY_TASKS:
            if enabled_tasks is not None and task_id not in enabled_tasks:
                ctx.logger.info(f"  task plan: {task_id} ({display}) — DISABLED")
            else:
                ctx.logger.info(f"  task plan: {task_id} ({display}) — enabled")

        routine_t0 = time.monotonic()
        total = len(_DAILY_TASKS)
        for i, (task_id, task_cls, _display, _safe) in enumerate(_DAILY_TASKS):
            # Skip tasks not in the enabled set
            if enabled_tasks is not None and task_id not in enabled_tasks:
                ctx.notify_task(task_id, "skipped", "disabled by user")
                continue

            # Startup task only runs when game was freshly launched
            if task_id == "startup" and not game_was_launched:
                ctx.notify_task(task_id, "skipped", "game already running")
                ctx.logger.info(f"  {task_id}: skipped (game already running)")
                # Go to hub via normal ReturnToHub instead
                await hub.execute(ctx)
                continue

            ctx.logger.info(
                f"--- DailyRoutine: task {i+1}/{total} — {task_id} ---"
            )
            ctx.notify_task(task_id, "running")

            task_t0 = time.monotonic()
            try:
                task = task_cls()
                if await task.can_run(ctx):
                    result = await task.execute(ctx)
                    elapsed = time.monotonic() - task_t0
                    if result.status == "success":
                        summary = task_id
                        if result.data:
                            for key in ("purchased", "claimed", "count"):
                                if key in result.data:
                                    summary = f"{task_id}({result.data[key]})"
                                    break
                        completed.append(summary)
                        ctx.notify_task(task_id, "success", result.message)
                        ctx.logger.info(
                            f"  {task_id}: success ({elapsed:.1f}s)"
                        )
                    elif result.status == "skipped":
                        completed.append(f"{task_id}(skipped)")
                        ctx.notify_task(task_id, "skipped", result.message)
                        ctx.logger.info(
                            f"  {task_id}: skipped — {result.message} "
                            f"({elapsed:.1f}s)"
                        )
                    else:
                        failed.append(task_id)
                        ctx.notify_task(task_id, "failed", result.message)
                        ctx.logger.warning(
                            f"  {task_id}: {result.status} — {result.message} "
                            f"({elapsed:.1f}s)"
                        )
                else:
                    elapsed = time.monotonic() - task_t0
                    ctx.notify_task(task_id, "skipped", "can_run=False")
                    ctx.logger.info(
                        f"  {task_id}: can_run=False, skipping ({elapsed:.1f}s)"
                    )
            except Exception as exc:
                elapsed = time.monotonic() - task_t0
                failed.append(task_id)
                ctx.notify_task(task_id, "failed", str(exc))
                ctx.logger.error(
                    f"  {task_id}: crashed — {exc} ({elapsed:.1f}s)"
                )

            # Return to hub between tasks
            await hub.execute(ctx)

        total_elapsed = time.monotonic() - routine_t0
        ctx.logger.info(
            f"=== DailyRoutine: complete "
            f"({len(completed)} done, {len(failed)} failed) "
            f"in {total_elapsed:.1f}s ===\n"
            f"  completed={completed}\n"
            f"  failed={failed}"
        )
        return ProcessResult(
            status="success",
            data={"completed": completed, "failed": failed},
        )
