"""GameSession — MaaFw 的唯一封装点 (DEPRECATED)

.. deprecated::
    :class:`GameSession` is superseded by
    :class:`anime_game_afk.core.device.DeviceAdapter`.
    This module is kept for backward compatibility and will be removed in a
    future release.  New code should import ``DeviceAdapter`` directly.

一个游戏实例从连接到断开的完整会话。
所有其他代码只跟 GameSession 交互，不直接接触 MaaFw API。
"""

from __future__ import annotations

import ctypes
import warnings
from pathlib import Path

import cv2
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
        warnings.warn(
            "GameSession is deprecated and will be removed in a future "
            "release.  Use anime_game_afk.core.device.DeviceAdapter instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._config = config
        self._controller: Win32Controller | None = None
        self._resource: Resource | None = None
        self._tasker: Tasker | None = None
        self._hwnd: ctypes.c_void_p | None = None
        # 分辨率缩放 — connect() 时根据实际窗口分辨率计算
        self._design_w, self._design_h = config.design_resolution
        self._scale_x: float = 1.0
        self._scale_y: float = 1.0
        self._actual_w: int = self._design_w
        self._actual_h: int = self._design_h

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

        # 使用原始分辨率截图，确保截图像素坐标 = 点击坐标
        # 不做内部缩放，避免坐标映射问题
        self._controller.set_screenshot_use_raw_size(True)

        # 关键: MaaFw 的 resolution 在首次截图前为 (0,0)
        # 这会导致 post_click 坐标映射错误
        # 必须在 connect 后立即做一次截图来初始化 resolution
        self._controller.post_screencap().wait()

        # 计算设计分辨率 → 实际分辨率的缩放比
        self._actual_w, self._actual_h = self._controller.resolution
        self._scale_x = self._actual_w / self._design_w
        self._scale_y = self._actual_h / self._design_h

        if self._scale_x != 1.0 or self._scale_y != 1.0:
            logger.warning(
                "分辨率缩放启用: 设计={}x{}, 实际={}x{}, "
                "scale=({:.3f}, {:.3f})",
                self._design_w, self._design_h,
                self._actual_w, self._actual_h,
                self._scale_x, self._scale_y,
            )
        logger.info(
            "控制器已连接 (原始分辨率模式, resolution={})",
            self._controller.resolution,
        )

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
        """后台截图，返回设计分辨率的图像

        始终返回 design_resolution 大小的 BGR numpy 数组。
        如果实际窗口分辨率不同，自动缩放到设计分辨率。
        这样所有下游代码（模板匹配、坐标定位）都在同一个坐标系工作。

        Returns:
            BGR 格式的 numpy 数组，尺寸为 design_resolution

        Raises:
            ScreenshotError: 截图失败
        """
        self._ensure_connected()
        assert self._controller is not None

        img = self._controller.post_screencap().wait().get()
        if img is None:
            raise ScreenshotError("截图返回 None")

        # 如果实际分辨率 != 设计分辨率，缩放到设计分辨率
        h, w = img.shape[:2]
        if w != self._design_w or h != self._design_h:
            img = cv2.resize(
                img,
                (self._design_w, self._design_h),
                interpolation=cv2.INTER_AREA,
            )
        return img

    def screenshot_raw(self) -> np.ndarray:
        """后台截图，返回原始分辨率（不缩放）

        仅在需要原始像素精度时使用（如保存高清截图）。
        大多数情况下应使用 screenshot()。

        Returns:
            BGR 格式的 numpy 数组，尺寸为实际窗口分辨率
        """
        self._ensure_connected()
        assert self._controller is not None

        img = self._controller.post_screencap().wait().get()
        if img is None:
            raise ScreenshotError("截图返回 None")
        return img

    def click(self, x: int, y: int) -> None:
        """后台点击

        接受设计分辨率坐标，自动缩放到实际窗口分辨率。
        """
        self._ensure_connected()
        assert self._controller is not None
        actual_x = int(x * self._scale_x)
        actual_y = int(y * self._scale_y)
        self._controller.post_click(actual_x, actual_y).wait()
        if self._scale_x != 1.0 or self._scale_y != 1.0:
            logger.debug(
                "点击 ({}, {}) → 实际 ({}, {})", x, y, actual_x, actual_y
            )
        else:
            logger.debug("点击 ({}, {})", x, y)

    def swipe(
        self, x1: int, y1: int, x2: int, y2: int, duration: int = 500
    ) -> None:
        """后台滑动

        接受设计分辨率坐标，自动缩放到实际窗口分辨率。
        """
        self._ensure_connected()
        assert self._controller is not None
        ax1 = int(x1 * self._scale_x)
        ay1 = int(y1 * self._scale_y)
        ax2 = int(x2 * self._scale_x)
        ay2 = int(y2 * self._scale_y)
        self._controller.post_swipe(ax1, ay1, ax2, ay2, duration).wait()
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
