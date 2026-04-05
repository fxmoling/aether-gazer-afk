"""每日任务执行脚本

用法:
    python scripts/run_daily.py              # 执行完整每日例行
    python scripts/run_daily.py --dry-run    # 仅打印计划
    python scripts/run_daily.py --task X     # 执行单个任务
    python scripts/run_daily.py --list       # 列出可用任务
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
from anime_game_afk.core.session import GameSession
from anime_game_afk.games.aether_gazer.nav.navigator import Navigator
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext, TaskSequence
from anime_game_afk.games.aether_gazer.tasks.daily import (
    CollectEventsRewards,
    CollectGuildRewards,
    CollectMail,
    CollectTacticsRewards,
    DailyCheckin,
    FullDailyRoutine,
    ViewDailyTasks,
)

# 可用任务注册表
AVAILABLE_TASKS = {
    "checkin": DailyCheckin,
    "mail": CollectMail,
    "guild": CollectGuildRewards,
    "tactics": CollectTacticsRewards,
    "events": CollectEventsRewards,
    "daily_view": ViewDailyTasks,
    "full": FullDailyRoutine,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="每日任务执行")
    parser.add_argument("--dry-run", action="store_true", help="仅打印计划")
    parser.add_argument("--task", "-t", help="执行单个任务 (checkin/mail/guild/tactics/events/daily_view/full)")
    parser.add_argument("--list", action="store_true", help="列出可用任务")
    args = parser.parse_args()

    if args.list:
        logger.info("可用任务:")
        for name, cls in AVAILABLE_TASKS.items():
            task = cls()
            logger.info("  {:15s} - {}", name, task.description)
        return

    # 创建会话
    session = GameSession(AETHER_GAZER_CONFIG)
    session.connect()

    try:
        # 创建导航器和上下文
        navigator = Navigator(session)
        ctx = TaskContext(
            session=session,
            navigator=navigator,
            dry_run=args.dry_run,
        )

        # 确定要执行的任务
        if args.task:
            if args.task not in AVAILABLE_TASKS:
                logger.error("未知任务: {}. 可用: {}", args.task, list(AVAILABLE_TASKS.keys()))
                return
            task = AVAILABLE_TASKS[args.task]()
        else:
            task = FullDailyRoutine()

        # 确保在hub
        logger.info("=== 开始执行: {} ===", task.name)
        if not args.dry_run:
            navigator.ensure_hub()

        # 执行
        start_time = time.time()
        result = task.execute(ctx)
        duration = time.time() - start_time

        # 报告
        logger.info("=== 执行完成 ===")
        logger.info("任务: {}", task.name)
        logger.info("结果: {}", "成功" if result.success else "失败")
        logger.info("耗时: {:.1f}秒", duration)
        if result.message:
            logger.info("消息: {}", result.message)

        logger.info("\n执行历史:")
        for entry in ctx.history:
            status = "OK" if entry["success"] else "FAIL"
            logger.info("  [{}] {} - {}", status, entry["task"], entry["action"])

    finally:
        session.disconnect()


if __name__ == "__main__":
    main()
