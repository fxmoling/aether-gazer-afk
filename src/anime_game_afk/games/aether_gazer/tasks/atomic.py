"""原子操作 — SinglePointTask 实现

这些是最基础的操作单元，可以组合成更复杂的任务。
"""

from __future__ import annotations

import time

from loguru import logger

from anime_game_afk.config.models import TaskResult
from anime_game_afk.games.aether_gazer.pages.definitions import (
    ALL_PAGES,
    UNSAFE_PAGES,
    Coord,
    VK_ESCAPE,
)
from anime_game_afk.games.aether_gazer.tasks.base import (
    SinglePointTask,
    TaskContext,
)


class NavigateToPage(SinglePointTask):
    """导航到指定页面"""

    def __init__(self, page_id: str) -> None:
        self._page_id = page_id

    @property
    def name(self) -> str:
        page = ALL_PAGES.get(self._page_id)
        page_name = page.name if page else self._page_id
        return f"导航到{page_name}"

    @property
    def description(self) -> str:
        return f"navigate_to({self._page_id})"

    def execute(self, ctx: TaskContext) -> TaskResult:
        if ctx.dry_run:
            ctx.log_step(self.name, f"[DRY] 导航到 {self._page_id}", True)
            return TaskResult(success=True, task_name=self.name)

        success = ctx.navigator.navigate_to(self._page_id)
        ctx.log_step(self.name, f"导航到 {self._page_id}", success)
        return TaskResult(
            success=success,
            task_name=self.name,
            message="" if success else f"无法导航到 {self._page_id}",
        )


class EnsureHub(SinglePointTask):
    """确保在主大厅"""

    @property
    def name(self) -> str:
        return "确保在主大厅"

    def execute(self, ctx: TaskContext) -> TaskResult:
        if ctx.dry_run:
            return TaskResult(success=True, task_name=self.name)

        success = ctx.navigator.ensure_hub()
        ctx.log_step(self.name, "确保在主大厅", success)
        return TaskResult(
            success=success,
            task_name=self.name,
            message="" if success else "无法返回主大厅",
        )


class ClickAt(SinglePointTask):
    """点击指定坐标"""

    def __init__(self, x: int, y: int, description: str = "",
                 wait_after: float = 1.0) -> None:
        self._coord = Coord(x, y)
        self._description = description
        self._wait_after = wait_after

    @property
    def name(self) -> str:
        return f"点击({self._coord.x},{self._coord.y})"

    @property
    def description(self) -> str:
        return self._description

    def execute(self, ctx: TaskContext) -> TaskResult:
        if ctx.dry_run:
            ctx.log_step(self.name, f"[DRY] 点击 {self._coord}", True)
            return TaskResult(success=True, task_name=self.name)

        ctx.session.click(self._coord.x, self._coord.y)
        ctx.log_step(self.name, f"点击 {self._coord}", True)
        time.sleep(self._wait_after)
        return TaskResult(success=True, task_name=self.name)


class PressKey(SinglePointTask):
    """按键"""

    def __init__(self, key_code: int, key_name: str = "",
                 wait_after: float = 1.0) -> None:
        self._key_code = key_code
        self._key_name = key_name or f"0x{key_code:02X}"
        self._wait_after = wait_after

    @property
    def name(self) -> str:
        return f"按键 {self._key_name}"

    def execute(self, ctx: TaskContext) -> TaskResult:
        if ctx.dry_run:
            ctx.log_step(self.name, f"[DRY] 按键 {self._key_name}", True)
            return TaskResult(success=True, task_name=self.name)

        ctx.session.press_key(self._key_code)
        ctx.log_step(self.name, f"按键 {self._key_name}", True)
        time.sleep(self._wait_after)
        return TaskResult(success=True, task_name=self.name)


class Wait(SinglePointTask):
    """等待指定秒数"""

    def __init__(self, seconds: float, reason: str = "") -> None:
        self._seconds = seconds
        self._reason = reason

    @property
    def name(self) -> str:
        return f"等待{self._seconds}秒"

    @property
    def description(self) -> str:
        return self._reason

    def execute(self, ctx: TaskContext) -> TaskResult:
        if ctx.dry_run:
            return TaskResult(success=True, task_name=self.name)

        time.sleep(self._seconds)
        return TaskResult(success=True, task_name=self.name)


class ClickElement(SinglePointTask):
    """在指定页面点击指定元素（按名称查找）"""

    def __init__(self, page_id: str, element_name: str,
                 wait_after: float = 1.5) -> None:
        self._page_id = page_id
        self._element_name = element_name
        self._wait_after = wait_after

    @property
    def name(self) -> str:
        return f"点击[{self._page_id}].{self._element_name}"

    def execute(self, ctx: TaskContext) -> TaskResult:
        if ctx.dry_run:
            ctx.log_step(self.name, f"[DRY] {self.name}", True)
            return TaskResult(success=True, task_name=self.name)

        page = ALL_PAGES.get(self._page_id)
        if page is None:
            return TaskResult(
                success=False,
                task_name=self.name,
                message=f"未知页面: {self._page_id}",
            )

        for elem in page.elements:
            if elem.name == self._element_name:
                if not elem.safe:
                    return TaskResult(
                        success=False,
                        task_name=self.name,
                        message=f"元素 {self._element_name} 不安全",
                    )
                ctx.session.click(elem.coord.x, elem.coord.y)
                ctx.log_step(
                    self.name,
                    f"点击 {self._element_name} at ({elem.coord.x},{elem.coord.y})",
                    True,
                )
                time.sleep(self._wait_after)
                return TaskResult(success=True, task_name=self.name)

        return TaskResult(
            success=False,
            task_name=self.name,
            message=f"找不到元素: {self._element_name}",
        )


class GoBack(SinglePointTask):
    """从当前页面返回"""

    def __init__(self, method: str = "esc") -> None:
        """
        Args:
            method: "esc" 或 "click_back"
        """
        self._method = method

    @property
    def name(self) -> str:
        return "返回上一页"

    def execute(self, ctx: TaskContext) -> TaskResult:
        if ctx.dry_run:
            return TaskResult(success=True, task_name=self.name)

        success = ctx.navigator.go_back()
        ctx.log_step(self.name, "返回上一页", success)
        return TaskResult(
            success=success,
            task_name=self.name,
        )


class WakeUI(SinglePointTask):
    """唤醒UI（点击空白区域）"""

    @property
    def name(self) -> str:
        return "唤醒UI"

    def execute(self, ctx: TaskContext) -> TaskResult:
        if ctx.dry_run:
            return TaskResult(success=True, task_name=self.name)

        ctx.session.click(800, 450)
        time.sleep(0.5)
        return TaskResult(success=True, task_name=self.name)
