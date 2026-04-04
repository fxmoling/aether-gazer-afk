"""GameSession — MaaFw 的唯一封装点

一个游戏实例从连接到断开的完整会话。
所有其他代码只跟 GameSession 交互，不直接接触 MaaFw API。
"""

from __future__ import annotations

import ctypes
from pathlib import Path

import numpy as np
from loguru import logger
from maa.controller import Win32Controller
from maa.define import MaaWin32InputMethodEnum, MaaWin32ScreencapMethodEnum
from maa.resource import Resource
from maa.tasker import Tasker
from maa.toolkit import DesktopWindow, Toolkit

from anime_game_afk.config.models import GameConfig
from anime_game_afk.core.errors import (
    ConnectionError,
    PipelineError,
    ScreenshotError,
    WindowNotFoundError,
)


class GameSession:
    """一个游戏实例的运行会话"""

    def __init__(self, config: GameConfig) -> None:
        self._config = config
        self._controller: Win32Controller | None = None
        self._resource: Resource | None = None
        self._tasker: Tasker | None = None
        self._hwnd: ctypes.c_void_p | None = None

    @property
    def connected(self) -> bool:
        return self._tasker is not None

    @property
    def config(self) -> GameConfig:
        return self._config

    def find_window(self) -> ctypes.c_void_p:
        """查找游戏窗口

        Returns:
            窗口句柄

        Raises:
            WindowNotFoundError: 找不到游戏窗口
        """
        windows = Toolkit.find_desktop_windows()
        for w in windows:
            if self._config.window_title in w.window_name:
                logger.info(
                    "找到游戏窗口: title={!r} hwnd={} class={!r}",
                    w.window_name,
                    w.hwnd,
                    w.class_name,
                )
                return w.hwnd

        raise WindowNotFoundError(
            f"找不到窗口: {self._config.window_title}"
        )

    def connect(self) -> None:
        """连接游戏窗口，初始化 MaaFw

        Raises:
            WindowNotFoundError: 找不到游戏窗口
            ConnectionError: 连接失败
        """
        self._hwnd = self.find_window()

        # 创建控制器
        try:
            self._controller = Win32Controller(
                hWnd=self._hwnd,
                screencap_method=self._config.screencap_method,
                mouse_method=self._config.mouse_method,
                keyboard_method=self._config.keyboard_method,
            )
        except RuntimeError as e:
            raise ConnectionError(f"创建控制器失败: {e}") from e

        self._controller.post_connection().wait()
        logger.info("控制器已连接")

        # 加载资源
        resource_path = self._config.resource_path
        if resource_path.exists():
            self._resource = Resource()
            self._resource.post_bundle(str(resource_path)).wait()
            logger.info("资源已加载: {}", resource_path)
        else:
            self._resource = Resource()
            logger.warning("资源路径不存在，跳过加载: {}", resource_path)

        # 创建 Tasker 并绑定
        self._tasker = Tasker()
        self._tasker.bind(self._resource, self._controller)
        logger.info("GameSession 已就绪: {}", self._config.name)

    def disconnect(self) -> None:
        """断开连接，清理资源"""
        self._tasker = None
        self._resource = None
        self._controller = None
        self._hwnd = None
        logger.info("GameSession 已断开: {}", self._config.name)

    def screenshot(self) -> np.ndarray:
        """后台截图

        Returns:
            BGR 格式的 numpy 数组

        Raises:
            ScreenshotError: 截图失败
        """
        self._ensure_connected()
        assert self._controller is not None

        img = self._controller.post_screencap().wait().get()
        if img is None:
            raise ScreenshotError("截图返回 None")
        return img

    def click(self, x: int, y: int) -> None:
        """后台点击"""
        self._ensure_connected()
        assert self._controller is not None
        self._controller.post_click(x, y).wait()
        logger.debug("点击 ({}, {})", x, y)

    def swipe(
        self, x1: int, y1: int, x2: int, y2: int, duration: int = 500
    ) -> None:
        """后台滑动"""
        self._ensure_connected()
        assert self._controller is not None
        self._controller.post_swipe(x1, y1, x2, y2, duration).wait()
        logger.debug("滑动 ({},{}) -> ({},{})", x1, y1, x2, y2)

    def press_key(self, key_code: int) -> None:
        """后台按键"""
        self._ensure_connected()
        assert self._controller is not None
        self._controller.post_press_key(key_code).wait()
        logger.debug("按键 {}", key_code)

    def run_pipeline(
        self, entry: str, override: dict | None = None
    ) -> bool:
        """执行 JSON 管线

        Args:
            entry: 管线入口节点名
            override: 管线参数覆盖

        Returns:
            是否成功

        Raises:
            PipelineError: 管线执行失败
        """
        self._ensure_connected()
        assert self._tasker is not None

        logger.info("执行管线: {}", entry)
        try:
            job = self._tasker.post_task(entry, override or {})
            job.wait()
            # TODO: 检查 job.status 判断成功/失败
            logger.info("管线完成: {}", entry)
            return True
        except Exception as e:
            raise PipelineError(f"管线执行失败: {entry} - {e}") from e

    def _ensure_connected(self) -> None:
        if not self.connected:
            raise ConnectionError("GameSession 未连接")
