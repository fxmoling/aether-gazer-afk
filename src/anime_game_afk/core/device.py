"""DeviceAdapter — single point of contact with MaaFramework for device I/O.

Responsibilities:
- Window discovery and connection lifecycle (connect / disconnect)
- Screenshot capture with automatic design-resolution scaling
- Input delegation (click, swipe, press_key, hold_key)

Explicitly out of scope:
- Resource loading (no ``maa.resource.Resource``)
- Pipeline / Tasker execution (no ``maa.tasker.Tasker``)
"""
from __future__ import annotations

import ctypes
import time

import cv2
import numpy as np
from loguru import logger
from maa.controller import Win32Controller
from maa.toolkit import Toolkit

from anime_game_afk.core.errors import (
    DeviceConnectionError,
    ScreenshotError,
    WindowNotFoundError,
)
from anime_game_afk.core.types import DeviceConfig, Resolution


class DeviceAdapter:
    """Low-level device I/O adapter wrapping MaaFramework's Win32 controller.

    All public coordinate arguments are in *design resolution* space.
    The adapter scales them to the actual window resolution automatically.

    Example::

        config = DeviceConfig(window_title="MyGame")
        device = DeviceAdapter(config)
        device.connect()
        img = device.screenshot()          # design-res BGR ndarray
        device.click(800, 450)             # design-res coords
        device.disconnect()
    """

    def __init__(self, config: DeviceConfig) -> None:
        self._config = config
        self._controller: Win32Controller | None = None
        self._hwnd: ctypes.c_void_p | None = None

        design_w, design_h = config.design_resolution
        self._design = Resolution(width=design_w, height=design_h)
        self._actual = Resolution(width=design_w, height=design_h)
        self._scale_x: float = 1.0
        self._scale_y: float = 1.0

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def connected(self) -> bool:
        """True when a controller connection is active."""
        return self._controller is not None

    @property
    def config(self) -> DeviceConfig:
        """The :class:`DeviceConfig` this adapter was created with."""
        return self._config

    @property
    def design_resolution(self) -> Resolution:
        """Target resolution used for all input/output coordinates."""
        return self._design

    @property
    def actual_resolution(self) -> Resolution:
        """Real window resolution detected after :meth:`connect`."""
        return self._actual

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def find_window(self) -> ctypes.c_void_p:
        """Search for the game window by title substring.

        Returns:
            Win32 window handle (HWND) of the matching window.

        Raises:
            WindowNotFoundError: No visible window contains
                ``config.window_title`` in its name.
        """
        windows = Toolkit.find_desktop_windows()
        for w in windows:
            if self._config.window_title in w.window_name:
                logger.info(
                    "Found game window: title={!r} hwnd={} class={!r}",
                    w.window_name,
                    w.hwnd,
                    w.class_name,
                )
                return w.hwnd

        raise WindowNotFoundError(
            f"Window not found: {self._config.window_title!r}"
        )

    def connect(self) -> None:
        """Locate the game window and establish a MaaFw controller connection.

        Raises:
            WindowNotFoundError: Game window not found on the desktop.
            DeviceConnectionError: MaaFw controller could not be initialised.
        """
        self._hwnd = self.find_window()

        try:
            self._controller = Win32Controller(
                hWnd=self._hwnd,
                screencap_method=self._config.screencap_method,
                mouse_method=self._config.mouse_method,
                keyboard_method=self._config.keyboard_method,
            )
        except RuntimeError as exc:
            raise DeviceConnectionError(
                f"Failed to create Win32Controller: {exc}"
            ) from exc

        self._controller.post_connection().wait()

        # Raw-size mode ensures screenshot pixel coords == click coords.
        self._controller.set_screenshot_use_raw_size(True)

        # MaaFw reports (0, 0) before the first screencap; take one now.
        self._controller.post_screencap().wait()

        actual_w, actual_h = self._controller.resolution
        self._actual = Resolution(width=actual_w, height=actual_h)
        self._scale_x = actual_w / self._design.width
        self._scale_y = actual_h / self._design.height

        if self._scale_x != 1.0 or self._scale_y != 1.0:
            logger.warning(
                "Resolution scaling active: design={}x{} actual={}x{} "
                "scale=({:.3f}, {:.3f})",
                self._design.width, self._design.height,
                actual_w, actual_h,
                self._scale_x, self._scale_y,
            )

        logger.info(
            "DeviceAdapter connected: window={!r} resolution={}x{}",
            self._config.window_title, actual_w, actual_h,
        )

    def disconnect(self) -> None:
        """Release the controller and reset all connection state."""
        self._controller = None
        self._hwnd = None
        # Reset actual resolution back to design so stale callers don't
        # operate with an old scale factor.
        self._actual = Resolution(
            width=self._design.width, height=self._design.height
        )
        self._scale_x = 1.0
        self._scale_y = 1.0
        logger.info("DeviceAdapter disconnected: window={!r}", self._config.window_title)

    # ------------------------------------------------------------------
    # Device I/O
    # ------------------------------------------------------------------

    def screenshot(self) -> np.ndarray:
        """Capture a screenshot scaled to design resolution.

        Returns:
            BGR ``numpy`` array of shape ``(design_h, design_w, 3)``.

        Raises:
            ScreenshotError: Controller returned ``None`` for the image.
            DeviceConnectionError: Not connected.
        """
        self._ensure_connected()
        assert self._controller is not None

        img: np.ndarray | None = (
            self._controller.post_screencap().wait().get()
        )
        if img is None:
            raise ScreenshotError("post_screencap returned None")

        h, w = img.shape[:2]
        if w != self._design.width or h != self._design.height:
            img = cv2.resize(
                img,
                (self._design.width, self._design.height),
                interpolation=cv2.INTER_AREA,
            )
        return img

    def screenshot_raw(self) -> np.ndarray:
        """Capture a screenshot at native window resolution (no scaling).

        Use when pixel-perfect accuracy at actual resolution is required.

        Returns:
            BGR ``numpy`` array at actual window dimensions.

        Raises:
            ScreenshotError: Controller returned ``None`` for the image.
            DeviceConnectionError: Not connected.
        """
        self._ensure_connected()
        assert self._controller is not None

        img: np.ndarray | None = (
            self._controller.post_screencap().wait().get()
        )
        if img is None:
            raise ScreenshotError("post_screencap returned None")
        return img

    def click(self, x: int, y: int) -> None:
        """Send a mouse click at design-resolution coordinates.

        Args:
            x: Horizontal position in design-resolution pixels.
            y: Vertical position in design-resolution pixels.

        Raises:
            DeviceConnectionError: Not connected.
        """
        self._ensure_connected()
        assert self._controller is not None

        ax = int(x * self._scale_x)
        ay = int(y * self._scale_y)
        self._controller.post_click(ax, ay).wait()
        logger.debug("click ({}, {}) -> actual ({}, {})", x, y, ax, ay)

    def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration: int = 500,
    ) -> None:
        """Perform a pointer swipe between two design-resolution points.

        Args:
            x1: Start X in design-resolution pixels.
            y1: Start Y in design-resolution pixels.
            x2: End X in design-resolution pixels.
            y2: End Y in design-resolution pixels.
            duration: Swipe duration in milliseconds (default 500).

        Raises:
            DeviceConnectionError: Not connected.
        """
        self._ensure_connected()
        assert self._controller is not None

        ax1, ay1 = int(x1 * self._scale_x), int(y1 * self._scale_y)
        ax2, ay2 = int(x2 * self._scale_x), int(y2 * self._scale_y)
        self._controller.post_swipe(ax1, ay1, ax2, ay2, duration).wait()
        logger.debug("swipe ({},{}) -> ({},{})", x1, y1, x2, y2)

    def press_key(self, vk_code: int) -> None:
        """Send a single key press (press + release cycle).

        Args:
            vk_code: Virtual-key code (Win32 VK_* constant).

        Raises:
            DeviceConnectionError: Not connected.
        """
        self._ensure_connected()
        assert self._controller is not None

        self._controller.post_press_key(vk_code).wait()
        logger.debug("press_key 0x{:02X}", vk_code)

    def hold_key(self, vk_code: int, duration_s: float) -> None:
        """Simulate holding a key for a given duration.

        MaaFramework does not expose separate key-down / key-up primitives.
        This method approximates a hold by rapidly pressing the key in a
        loop for *duration_s* seconds (every ~100ms).  This produces
        continuous movement for WASD exploration.

        Args:
            vk_code: Virtual-key code (Win32 VK_* constant).
            duration_s: How long to "hold" the key in seconds.

        Raises:
            DeviceConnectionError: Not connected.
        """
        self._ensure_connected()
        assert self._controller is not None

        interval = 0.1  # press every 100ms
        end_time = time.monotonic() + duration_s
        presses = 0
        while time.monotonic() < end_time:
            self._controller.post_press_key(vk_code).wait()
            presses += 1
            remaining = end_time - time.monotonic()
            if remaining > 0:
                time.sleep(min(interval, remaining))
        logger.debug(
            "hold_key 0x{:02X} for {:.2f}s ({} presses)",
            vk_code, duration_s, presses,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_connected(self) -> None:
        """Raise :exc:`DeviceConnectionError` if not currently connected."""
        if not self.connected:
            raise DeviceConnectionError("DeviceAdapter is not connected")
