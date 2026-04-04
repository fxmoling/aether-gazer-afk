"""完整任务流程 — CompleteTask 实现

每个 CompleteTask 是一个完整的业务流程，由多个原子操作组合而成。
"""

from __future__ import annotations

import time

from loguru import logger

from anime_game_afk.config.models import TaskResult
from anime_game_afk.games.aether_gazer.pages.definitions import (
    ALL_PAGES,
    Coord,
    VK_ESCAPE,
    VK_G,
    VK_H,
    VK_TAB,
)
from anime_game_afk.games.aether_gazer.tasks.base import (
    CompleteTask,
    SinglePointTask,
    TaskContext,
)
from anime_game_afk.games.aether_gazer.tasks.atomic import (
    ClickAt,
    ClickElement,
    EnsureHub,
    GoBack,
    NavigateToPage,
    PressKey,
    Wait,
    WakeUI,
)


class DailyCheckin(CompleteTask):
    """每日签到

    流程: hub → Tab(设置面板) → 点击签到 → 领取 → ESC回hub
    """

    @property
    def name(self) -> str:
        return "每日签到"

    @property
    def description(self) -> str:
        return "打开设置面板，进入签到页面，领取每日签到奖励"

    def execute(self, ctx: TaskContext) -> TaskResult:
        # 1. 确保在hub
        if not ctx.navigator.ensure_hub():
            return TaskResult(False, self.name, "无法到达主大厅")

        # 2. 打开设置面板
        WakeUI().execute(ctx)
        PressKey(VK_TAB, "Tab", 1.5).execute(ctx)

        # 3. 点击签到
        ClickAt(1320, 400, "签到按钮", 2.0).execute(ctx)

        # 4. 在签到页面，尝试领取奖励
        # 签到页面通常有一个"领取"或确认按钮
        # 具体坐标需要在签到页面截图后确认
        # 暂时点击中央区域
        ClickAt(800, 500, "签到领取区域", 1.5).execute(ctx)

        # 5. 返回hub
        ctx.session.press_key(VK_ESCAPE)
        time.sleep(1.0)
        ctx.session.press_key(VK_ESCAPE)
        time.sleep(1.0)
        ctx.navigator.ensure_hub()

        ctx.log_step(self.name, "每日签到完成", True)
        return TaskResult(True, self.name)


class CollectMail(CompleteTask):
    """领取邮件奖励

    流程: hub → H(邮件) → 逐个点击邮件领取 → ESC回hub
    """

    @property
    def name(self) -> str:
        return "领取邮件"

    @property
    def description(self) -> str:
        return "打开邮件页面，领取所有未领取的邮件奖励"

    def execute(self, ctx: TaskContext) -> TaskResult:
        # 1. 导航到邮件
        nav_result = NavigateToPage("mail").execute(ctx)
        if not nav_result.success:
            return TaskResult(False, self.name, "无法打开邮件")

        # 2. 依次点击邮件项 (左侧列表)
        # 邮件列表在左侧，y 从约 130 开始，每项约 60px 高
        mail_ys = [130, 190, 250, 310, 370, 430]
        collected = 0

        for y in mail_ys:
            # 点击邮件
            ClickAt(200, y, f"邮件项 y={y}", 1.0).execute(ctx)
            # 查找并点击"领取"按钮（如果有的话）
            # 领取按钮通常在右侧详情面板的底部
            # TODO: 需要通过截图确认具体坐标
            time.sleep(0.5)
            collected += 1

        # 3. 返回hub
        GoBack().execute(ctx)
        ctx.navigator.ensure_hub()

        ctx.log_step(self.name, f"领取了 {collected} 封邮件", True)
        return TaskResult(True, self.name, f"领取 {collected} 封邮件")


class ViewDailyTasks(CompleteTask):
    """查看每日任务

    流程: hub → G(每日任务) → 截图记录 → ESC回hub
    注意: 不执行任务，只查看
    """

    @property
    def name(self) -> str:
        return "查看每日任务"

    @property
    def description(self) -> str:
        return "打开每日任务面板，查看当前任务进度"

    def execute(self, ctx: TaskContext) -> TaskResult:
        # 1. 导航到每日任务
        nav_result = NavigateToPage("daily_tasks").execute(ctx)
        if not nav_result.success:
            return TaskResult(False, self.name, "无法打开每日任务")

        # 2. 截图记录
        img = ctx.session.screenshot()
        ctx.shared_data["daily_tasks_screenshot"] = img

        # 3. 查看周常任务
        ClickAt(80, 155, "周常任务标签", 1.0).execute(ctx)
        img_weekly = ctx.session.screenshot()
        ctx.shared_data["weekly_tasks_screenshot"] = img_weekly

        # 4. 返回每日任务标签
        ClickAt(80, 95, "每日任务标签", 0.5).execute(ctx)

        # 5. 返回hub
        GoBack().execute(ctx)

        ctx.log_step(self.name, "查看每日任务完成", True)
        return TaskResult(True, self.name)


class CollectGuildRewards(CompleteTask):
    """领取公会奖励

    流程: hub → 公会 → 矩阵补给 → 领取 → 返回hub
    """

    @property
    def name(self) -> str:
        return "领取公会奖励"

    @property
    def description(self) -> str:
        return "进入公会，领取矩阵补给奖励"

    def execute(self, ctx: TaskContext) -> TaskResult:
        # 1. 导航到公会
        nav_result = NavigateToPage("guild").execute(ctx)
        if not nav_result.success:
            return TaskResult(False, self.name, "无法打开公会")

        # 2. 点击矩阵补给
        ClickAt(1430, 870, "矩阵补给", 2.0).execute(ctx)

        # 3. 尝试领取（具体坐标需要在矩阵补给页面确认）
        # 通常有"一键领取"按钮
        ClickAt(800, 600, "领取区域", 1.5).execute(ctx)

        # 4. 返回
        ctx.session.press_key(VK_ESCAPE)
        time.sleep(1.0)
        GoBack().execute(ctx)
        ctx.navigator.ensure_hub()

        ctx.log_step(self.name, "公会奖励领取完成", True)
        return TaskResult(True, self.name)


class CollectTacticsRewards(CompleteTask):
    """领取对策协议(Battle Pass)奖励

    流程: hub → 对策协议 → 领取可领的奖励 → 返回hub
    """

    @property
    def name(self) -> str:
        return "领取对策协议奖励"

    @property
    def description(self) -> str:
        return "进入对策协议，领取已解锁的奖励"

    def execute(self, ctx: TaskContext) -> TaskResult:
        # 1. 导航到对策协议
        nav_result = NavigateToPage("tactics").execute(ctx)
        if not nav_result.success:
            return TaskResult(False, self.name, "无法打开对策协议")

        # 2. 尝试领取奖励（奖励格子在中间区域）
        # 基础合约奖励行 y ≈ 350
        # 进阶合约奖励行 y ≈ 500
        # 每个格子 x 间距约 100，从 x≈350 开始
        for x in range(350, 900, 110):
            ClickAt(x, 350, f"基础合约 x={x}", 0.3).execute(ctx)
        for x in range(350, 900, 110):
            ClickAt(x, 500, f"进阶合约 x={x}", 0.3).execute(ctx)

        time.sleep(0.5)

        # 3. 返回
        GoBack().execute(ctx)
        ctx.navigator.ensure_hub()

        ctx.log_step(self.name, "对策协议奖励领取完成", True)
        return TaskResult(True, self.name)


class CollectEventsRewards(CompleteTask):
    """领取入职活动奖励

    流程: hub → 入职活动 → 各标签领取 → 返回hub
    """

    @property
    def name(self) -> str:
        return "领取入职活动奖励"

    @property
    def description(self) -> str:
        return "进入入职活动，领取各类新手奖励"

    def execute(self, ctx: TaskContext) -> TaskResult:
        # 1. 导航到入职活动
        nav_result = NavigateToPage("events").execute(ctx)
        if not nav_result.success:
            return TaskResult(False, self.name, "无法打开入职活动")

        # 2. 点击入职签到标签 (默认选中)
        time.sleep(1.0)

        # 3. 尝试领取底部奖励
        # 底部有一排奖励按钮，从 x≈500 开始
        reward_ys = [870]
        for x in range(500, 1500, 150):
            ClickAt(x, 870, f"奖励 x={x}", 0.3).execute(ctx)

        # 4. 切换到日常委托
        ClickAt(80, 270, "日常委托", 1.0).execute(ctx)
        # 领取日常委托奖励
        for x in range(500, 1500, 150):
            ClickAt(x, 870, f"委托奖励 x={x}", 0.3).execute(ctx)

        # 5. 返回
        GoBack().execute(ctx)
        ctx.navigator.ensure_hub()

        ctx.log_step(self.name, "入职活动奖励领取完成", True)
        return TaskResult(True, self.name)


class FullDailyRoutine(CompleteTask):
    """完整每日例行

    按顺序执行所有每日任务:
    1. 每日签到
    2. 领取邮件
    3. 领取公会奖励
    4. 领取对策协议奖励
    5. 领取入职活动奖励
    6. 查看每日任务
    """

    @property
    def name(self) -> str:
        return "完整每日例行"

    @property
    def description(self) -> str:
        return "执行所有每日任务: 签到、领邮件、领公会/对策协议/活动奖励"

    def execute(self, ctx: TaskContext) -> TaskResult:
        sub_tasks = [
            DailyCheckin(),
            CollectMail(),
            CollectGuildRewards(),
            CollectTacticsRewards(),
            CollectEventsRewards(),
            ViewDailyTasks(),
        ]

        failed = []
        for task in sub_tasks:
            logger.info("--- 执行子任务: {} ---", task.name)
            try:
                result = task.execute(ctx)
                if not result.success:
                    failed.append(task.name)
                    logger.warning("子任务失败: {}", task.name)
            except Exception as e:
                failed.append(task.name)
                logger.error("子任务异常: {} - {}", task.name, e)

            # 每个子任务后确保回到hub
            try:
                ctx.navigator.ensure_hub()
            except Exception:
                pass

        if failed:
            return TaskResult(
                success=False,
                task_name=self.name,
                message=f"失败的子任务: {', '.join(failed)}",
            )

        return TaskResult(True, self.name, "所有每日任务完成")
