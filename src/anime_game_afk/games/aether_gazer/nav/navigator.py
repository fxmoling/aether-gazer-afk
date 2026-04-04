"""导航模块 — 页面间导航和原子操作

提供:
- navigate_to(page_id) — 从当前位置导航到目标页面
- ensure_hub() — 确保在主大厅
- go_back() — 返回上一页
- atomic actions — 点击、等待、截图验证等
"""

from __future__ import annotations

import time

from loguru import logger

from anime_game_afk.core.session import GameSession
from anime_game_afk.games.aether_gazer.pages.definitions import (
    ALL_PAGES,
    UNSAFE_PAGES,
    NavMethod,
    PageDef,
    VK_ESCAPE,
)
from anime_game_afk.games.aether_gazer.pages.identifier import (
    check_bottom_nav_present,
    identify_page,
)


class Navigator:
    """页面导航器

    所有导航都经过 hub → 目标页面 的路径。
    不支持页面间直接跳转（除非明确定义了路径）。
    """

    def __init__(self, session: GameSession) -> None:
        self._session = session
        self._current_page: str = "unknown"

    @property
    def current_page(self) -> str:
        return self._current_page

    def detect_current_page(self) -> str:
        """截图并识别当前页面"""
        img = self._session.screenshot()
        page_id, confidence = identify_page(img)
        self._current_page = page_id
        logger.info(
            "当前页面: {} (confidence={:.2f})", page_id, confidence
        )
        return page_id

    def ensure_hub(self, max_attempts: int = 5) -> bool:
        """确保当前在主大厅

        通过反复按 ESC + 检查底部导航栏来回到主大厅。

        Returns:
            是否成功到达主大厅
        """
        for attempt in range(max_attempts):
            img = self._session.screenshot()
            if check_bottom_nav_present(img):
                self._current_page = "main_hub"
                logger.info("已在主大厅 (attempt {})", attempt)
                return True

            logger.warning(
                "不在主大厅, 尝试ESC返回 (attempt {})", attempt
            )
            self._session.press_key(VK_ESCAPE)
            time.sleep(1.5)

        # 最终检查
        img = self._session.screenshot()
        if check_bottom_nav_present(img):
            self._current_page = "main_hub"
            return True

        logger.error("无法返回主大厅")
        return False

    def navigate_to(self, target_page_id: str) -> bool:
        """从当前位置导航到目标页面

        路径: 当前位置 → hub → 目标页面

        Args:
            target_page_id: 目标页面ID

        Returns:
            是否成功到达目标页面
        """
        if target_page_id not in ALL_PAGES:
            logger.error("未知页面: {}", target_page_id)
            return False

        target = ALL_PAGES[target_page_id]

        # 安全检查
        if target_page_id in UNSAFE_PAGES:
            logger.warning(
                "目标页面 {} 标记为不安全, 将仅导航不操作",
                target_page_id,
            )

        # 如果已经在目标页面
        if self._current_page == target_page_id:
            logger.info("已在目标页面: {}", target_page_id)
            return True

        # 如果目标就是hub
        if target_page_id == "main_hub":
            return self.ensure_hub()

        # 先回到hub
        if self._current_page != "main_hub":
            if not self.ensure_hub():
                return False

        # 从hub导航到目标
        if target.nav_from_hub is None:
            logger.error("页面 {} 没有定义 nav_from_hub", target_page_id)
            return False

        # 唤醒UI（hub的UI可能自动隐藏）
        self._wake_ui()
        time.sleep(0.3)

        # 执行导航动作
        nav = target.nav_from_hub
        self._execute_nav_action(nav, f"导航到 {target.name}")

        # 等待页面加载
        time.sleep(nav.wait_after)

        # 验证到达
        self._current_page = target_page_id
        logger.info("已导航到: {} ({})", target.name, target_page_id)
        return True

    def go_back(self) -> bool:
        """从当前页面返回上一级（通常是hub）

        Returns:
            是否成功返回
        """
        if self._current_page == "main_hub":
            logger.info("已在主大厅，无需返回")
            return True

        if self._current_page == "unknown":
            return self.ensure_hub()

        page = ALL_PAGES.get(self._current_page)
        if page is None or page.back_to_hub is None:
            # 尝试ESC
            self._session.press_key(VK_ESCAPE)
            time.sleep(1.5)
            return self.ensure_hub()

        self._execute_nav_action(
            page.back_to_hub, f"返回 from {page.name}"
        )
        time.sleep(page.back_to_hub.wait_after)

        self._current_page = page.parent_page or "main_hub"
        return True

    def click_element(self, page_id: str, element_name: str) -> bool:
        """在指定页面点击指定元素

        Args:
            page_id: 当前页面ID
            element_name: 元素名称

        Returns:
            是否成功点击
        """
        page = ALL_PAGES.get(page_id)
        if page is None:
            logger.error("未知页面: {}", page_id)
            return False

        for elem in page.elements:
            if elem.name == element_name:
                if not elem.safe:
                    logger.error(
                        "元素 {} 标记为不安全, 拒绝点击", element_name
                    )
                    return False
                self._session.click(elem.coord.x, elem.coord.y)
                logger.info(
                    "点击 {} ({}, {})",
                    element_name, elem.coord.x, elem.coord.y,
                )
                return True

        logger.error(
            "页面 {} 中找不到元素: {}", page_id, element_name
        )
        return False

    def _wake_ui(self) -> None:
        """唤醒UI（点击屏幕中央）"""
        self._session.click(800, 450)

    def _execute_nav_action(self, nav, description: str = "") -> None:
        """执行导航动作"""
        if nav.method == NavMethod.CLICK:
            assert nav.coord is not None
            logger.debug(
                "{}: 点击 ({}, {})", description, nav.coord.x, nav.coord.y
            )
            self._session.click(nav.coord.x, nav.coord.y)
        elif nav.method == NavMethod.KEY:
            assert nav.key_code is not None
            logger.debug(
                "{}: 按键 0x{:02X}", description, nav.key_code
            )
            self._session.press_key(nav.key_code)
        elif nav.method == NavMethod.ESC:
            logger.debug("{}: ESC", description)
            self._session.press_key(VK_ESCAPE)
