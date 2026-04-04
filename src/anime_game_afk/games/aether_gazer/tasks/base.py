"""任务基类和原子操作

任务层次:
  SinglePointTask — 单步原子操作 (如: 导航到某页面)
  CompleteTask    — 完整业务流程 (如: 每日签到)
  TaskSequence    — 任务编排 (如: 登录→签到→领邮件→每日任务)
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from anime_game_afk.config.models import TaskResult
from anime_game_afk.core.session import GameSession
from anime_game_afk.games.aether_gazer.nav.navigator import Navigator


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskContext:
    """任务执行上下文 — 在任务间共享状态"""
    session: GameSession
    navigator: Navigator
    dry_run: bool = False
    # 任务间共享数据
    shared_data: dict[str, Any] = field(default_factory=dict)
    # 执行历史
    history: list[dict] = field(default_factory=list)

    def log_step(self, task_name: str, action: str, success: bool) -> None:
        """记录执行步骤"""
        entry = {
            "task": task_name,
            "action": action,
            "success": success,
            "timestamp": time.time(),
        }
        self.history.append(entry)
        if success:
            logger.info("[{}] {}", task_name, action)
        else:
            logger.error("[{}] FAILED: {}", task_name, action)


class BaseTask(ABC):
    """任务基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """任务名称"""

    @property
    def description(self) -> str:
        """任务描述"""
        return ""

    @abstractmethod
    def execute(self, ctx: TaskContext) -> TaskResult:
        """执行任务"""

    def can_execute(self, ctx: TaskContext) -> bool:
        """检查是否可以执行（前置条件）"""
        return True


class SinglePointTask(BaseTask):
    """单步原子操作

    最小的可执行单元，如:
    - 导航到某个页面
    - 点击某个按钮
    - 等待某个条件
    """
    pass


class CompleteTask(BaseTask):
    """完整业务流程

    由多个 SinglePointTask 组合而成，如:
    - 每日签到完整流程
    - 领取邮件奖励
    - 做每日任务
    """

    @property
    def steps(self) -> list[SinglePointTask]:
        """返回组成此任务的步骤列表"""
        return []

    def execute(self, ctx: TaskContext) -> TaskResult:
        """默认实现: 依次执行所有步骤"""
        for step in self.steps:
            if not step.can_execute(ctx):
                logger.warning("跳过步骤: {} (前置条件不满足)", step.name)
                continue

            result = step.execute(ctx)
            if not result.success:
                return TaskResult(
                    success=False,
                    task_name=self.name,
                    message=f"步骤失败: {step.name} - {result.message}",
                )

        return TaskResult(success=True, task_name=self.name)


class TaskSequence:
    """任务编排 — 按顺序执行多个任务"""

    def __init__(
        self,
        tasks: list[BaseTask],
        name: str = "TaskSequence",
        stop_on_failure: bool = False,
    ) -> None:
        self._tasks = tasks
        self._name = name
        self._stop_on_failure = stop_on_failure

    @property
    def name(self) -> str:
        return self._name

    def execute(self, ctx: TaskContext) -> list[TaskResult]:
        """执行所有任务，返回结果列表"""
        results = []

        for task in self._tasks:
            logger.info("=" * 50)
            logger.info("执行任务: {} ({})", task.name, task.description)
            logger.info("=" * 50)

            if not task.can_execute(ctx):
                logger.warning("跳过任务: {} (前置条件不满足)", task.name)
                results.append(TaskResult(
                    success=False,
                    task_name=task.name,
                    message="前置条件不满足",
                ))
                continue

            try:
                result = task.execute(ctx)
                results.append(result)

                if result.success:
                    logger.info("任务成功: {}", task.name)
                else:
                    logger.error(
                        "任务失败: {} - {}", task.name, result.message
                    )
                    if self._stop_on_failure:
                        logger.error("stop_on_failure=True, 停止执行")
                        break

            except Exception as e:
                logger.error("任务异常: {} - {}", task.name, e)
                results.append(TaskResult(
                    success=False,
                    task_name=task.name,
                    message=f"异常: {e}",
                ))
                if self._stop_on_failure:
                    break

            # 每个任务执行后确保回到hub
            try:
                ctx.navigator.ensure_hub()
            except Exception:
                logger.warning("任务后回hub失败, 尝试继续")

        return results
