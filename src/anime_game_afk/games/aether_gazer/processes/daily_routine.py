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
9. 每日/周常任务领取 — Daily + weekly mission rewards
10. 对策协议任务领取 — Tactics Protocol task rewards
"""
from __future__ import annotations

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
from anime_game_afk.games.aether_gazer.tasks.startup_tasks import (
    SkipStartupPopups,
)
from anime_game_afk.games.aether_gazer.processes.base import (
    ProcessContext,
    ProcessResult,
)


# All daily tasks in execution order
_DAILY_TASKS = [
    ("startup", SkipStartupPopups),                   # 0. 启动/跳过弹窗 (已在hub则自动跳过)
    ("mail", CollectAllMail),                          # 1. 领取所有邮件
    ("intel_shards", BuyIntelShards),                  # 2. 购买情报碎片
    ("stamina_packs", ClaimDailyStaminaPacks),         # 3. 领取吨吨值福利包
    ("free_stamina", ClaimFreeStamina),                # 4. 领取商店免费体力
    ("mimi_station", MimiStationCollect),              # 5. 弥弥观测站
    ("guild_supply", GuildSupplyClaim),                # 6. 公会矩阵补给
    ("amusement", AmusementStreetDaily),               # 7. 游园街日常管理
    ("joint_defense", JointDefenseSweep),              # 8. 联防协议扫荡
    ("missions", DailyWeeklyMissionClaim),             # 9. 每日/周常任务领取
    ("tactics", TacticsTaskClaim),                     # 10. 对策协议任务领取
]


class DailyRoutine:
    """Complete all daily tasks and claim rewards.

    Runs 10 tasks in sequence, returning to hub between each.
    Each task failure is caught independently.
    """
    name = "daily_routine"
    description = (
        "Full daily routine: mail, shop, stamina, mimi station, "
        "missions, tactics, guild, amusement street"
    )

    async def execute(self, ctx: ProcessContext) -> ProcessResult:
        hub = ReturnToHub()
        completed: list[str] = []
        failed: list[str] = []

        # Must reach hub first
        ctx.logger.info("=== DailyRoutine: starting ===")
        result = await hub.execute(ctx)
        if result.status != "success":
            ctx.logger.error("Cannot reach hub, aborting daily routine")
            return ProcessResult(status="failed", message="Cannot reach hub")

        total = len(_DAILY_TASKS)
        for i, (task_name, task_cls) in enumerate(_DAILY_TASKS):
            ctx.logger.info(
                f"--- DailyRoutine: task {i+1}/{total} — {task_name} ---"
            )
            try:
                task = task_cls()
                if await task.can_run(ctx):
                    result = await task.execute(ctx)
                    if result.status == "success":
                        # Include data summary if available
                        summary = task_name
                        if result.data:
                            for key in ("purchased", "claimed", "count"):
                                if key in result.data:
                                    summary = f"{task_name}({result.data[key]})"
                                    break
                        completed.append(summary)
                        ctx.logger.info(f"  {task_name}: success")
                    elif result.status == "skipped":
                        completed.append(f"{task_name}(skipped)")
                        ctx.logger.info(
                            f"  {task_name}: skipped — {result.message}"
                        )
                    else:
                        failed.append(task_name)
                        ctx.logger.warning(
                            f"  {task_name}: {result.status} — {result.message}"
                        )
                else:
                    ctx.logger.info(f"  {task_name}: can_run=False, skipping")
            except Exception as exc:
                failed.append(task_name)
                ctx.logger.error(f"  {task_name}: crashed — {exc}")

            # Return to hub between tasks
            await hub.execute(ctx)

        ctx.logger.info(
            f"=== DailyRoutine: complete "
            f"({len(completed)} done, {len(failed)} failed) ===\n"
            f"  completed={completed}\n"
            f"  failed={failed}"
        )
        return ProcessResult(
            status="success",
            data={"completed": completed, "failed": failed},
        )
