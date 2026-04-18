"""e2e_test_tasks.py — Test each daily task individually against live game.

Connects to the running game, tests hub detection, then runs each task
one by one with full logging. Reports pass/fail per task.

Usage:
    python scripts/e2e_test_tasks.py                  # all tasks
    python scripts/e2e_test_tasks.py hub              # hub detection only
    python scripts/e2e_test_tasks.py mail              # single task
    python scripts/e2e_test_tasks.py mail guild shop   # multiple tasks
"""
from __future__ import annotations

import asyncio
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from loguru import logger

from anime_game_afk.core.device import DeviceAdapter
from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext, TaskResult
from anime_game_afk.games.aether_gazer.checks.page import AtHubCheck
from anime_game_afk.games.aether_gazer.ops.perception.identify_page import identify
from anime_game_afk.games.aether_gazer.ops.navigate.smart_return import (
    ReturnToHubAction,
)
from anime_game_afk.games.aether_gazer.ops.primitives import SleepOp

# Task imports
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

# Task registry: short_name -> (class, description)
TASK_MAP: dict[str, tuple[type, str]] = {
    "startup":        (SkipStartupPopups,      "跳过启动弹窗"),
    "mail":           (CollectAllMail,          "领取邮件"),
    "intel":          (BuyIntelShards,          "购买情报碎片"),
    "stamina_packs":  (ClaimDailyStaminaPacks,  "吨吨值福利包"),
    "free_stamina":   (ClaimFreeStamina,        "商店免费体力"),
    "mimi":           (MimiStationCollect,      "弥弥观测站"),
    "guild":          (GuildSupplyClaim,        "公会矩阵补给"),
    "amusement":      (AmusementStreetDaily,    "游园街日常"),
    "joint_defense":  (JointDefenseSweep,       "联防协议扫荡"),
    "missions":       (DailyWeeklyMissionClaim, "每日/周常任务"),
    "tactics":        (TacticsTaskClaim,        "对策协议任务"),
}


async def test_hub_detection(ctx: TaskContext) -> bool:
    """Test hub detection (active + idle)."""
    logger.info("=" * 60)
    logger.info("  Testing Hub Detection")
    logger.info("=" * 60)

    img = ctx.device.screenshot()
    page_id, conf = identify(img)
    logger.info(f"  identify() → page={page_id}, confidence={conf:.4f}")

    hub_result = await AtHubCheck().evaluate(ctx)
    logger.info(
        f"  AtHubCheck → passed={hub_result.passed}, "
        f"msg='{hub_result.message}', data={hub_result.data}"
    )

    if hub_result.passed:
        logger.info("  ✅ Hub active — ready for tasks")
        return True

    if hub_result.data and hub_result.data.get("hub_state") == "idle":
        logger.info("  Hub is idle — waking up...")
        from anime_game_afk.games.aether_gazer.ops.primitives import ClickOp
        await ClickOp(0.022, 0.039, wait=2.0).run(ctx)
        hub_result = await AtHubCheck().evaluate(ctx)
        if hub_result.passed:
            logger.info("  ✅ Hub woke up successfully")
            return True
        logger.warning("  ⚠ Hub didn't wake after click")

    # Try ReturnToHub
    logger.info("  Not at hub — trying ReturnToHubAction...")
    r = await ReturnToHubAction().run(ctx)
    if r.success:
        logger.info("  ✅ Reached hub via ReturnToHubAction")
        return True

    logger.error("  ❌ Cannot reach hub")
    return False


async def test_single_task(
    ctx: TaskContext,
    task_name: str,
    task_cls: type,
    task_desc: str,
) -> tuple[str, str, float]:
    """Run one task. Returns (name, status, elapsed_seconds)."""
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"  Task: {task_name} — {task_desc}")
    logger.info("=" * 60)

    t0 = time.perf_counter()
    try:
        task = task_cls()
        can = await task.can_run(ctx)
        if not can:
            logger.info(f"  {task_name}: can_run=False, skipping")
            return (task_name, "skipped(can_run)", time.perf_counter() - t0)

        result: TaskResult = await task.execute(ctx)
        elapsed = time.perf_counter() - t0
        logger.info(
            f"  {task_name}: status={result.status} "
            f"msg='{result.message}' elapsed={elapsed:.1f}s"
        )
        if result.data:
            logger.info(f"  data={result.data}")
        return (task_name, result.status, elapsed)

    except Exception as exc:
        elapsed = time.perf_counter() - t0
        logger.error(f"  {task_name}: CRASHED — {exc}")
        traceback.print_exc()
        return (task_name, f"crashed:{exc}", elapsed)


async def run_tests(device: DeviceAdapter, task_names: list[str]) -> None:
    """Run hub check + specified tasks."""
    ctx = TaskContext(device=device, logger=logger)

    # Always start with hub detection
    hub_ok = await test_hub_detection(ctx)
    if not hub_ok:
        logger.error("Hub detection failed — aborting all tasks")
        return

    results: list[tuple[str, str, float]] = []

    for tname in task_names:
        if tname not in TASK_MAP:
            logger.warning(f"Unknown task: {tname} — skipping")
            results.append((tname, "unknown", 0.0))
            continue

        cls, desc = TASK_MAP[tname]
        r = await test_single_task(ctx, tname, cls, desc)
        results.append(r)

        # Return to hub between tasks
        logger.info(f"  Returning to hub after {tname}...")
        ret = await ReturnToHubAction().run(ctx)
        if not ret.success:
            logger.warning(f"  ⚠ Failed to return to hub after {tname}")
            # Try once more
            await SleepOp(2.0).run(ctx)
            ret2 = await ReturnToHubAction().run(ctx)
            if not ret2.success:
                logger.error("  ❌ Cannot recover hub — stopping")
                break

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("  E2E Test Results")
    logger.info("=" * 60)
    total_time = sum(r[2] for r in results)
    for name, status, elapsed in results:
        icon = "✅" if status == "success" else "⏭" if "skip" in status else "❌"
        logger.info(f"  {icon} {name:20s} {status:15s} {elapsed:6.1f}s")
    logger.info(f"  Total: {len(results)} tasks, {total_time:.1f}s")


def main():
    # Parse args
    args = sys.argv[1:]
    if not args:
        # Default: all tasks in daily routine order
        task_names = list(TASK_MAP.keys())
    elif args == ["hub"]:
        task_names = []  # hub detection only
    else:
        task_names = args

    logger.info(f"E2E Test — tasks: {task_names or ['(hub only)']}")

    config = AETHER_GAZER_CONFIG.to_device_config()
    device = DeviceAdapter(config)

    try:
        device.connect()
        logger.info(f"Connected: actual_resolution={device.actual_resolution}")
    except Exception as e:
        logger.error(f"Cannot connect to game: {e}")
        sys.exit(1)

    try:
        asyncio.run(run_tests(device, task_names))
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal: {e}")
        traceback.print_exc()
    finally:
        device.disconnect()
        logger.info("Done.")


if __name__ == "__main__":
    main()
