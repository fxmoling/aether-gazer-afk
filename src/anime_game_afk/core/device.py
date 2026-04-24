"""DeviceAdapter — single point of contact with MaaFramework for device I/O.

Responsibilities:
- Window discovery and connection lifecycle (connect / disconnect)
- Screenshot capture with proportional scaling (height-capped, aspect-ratio preserved)
- Input delegation via fractional coordinates (click, swipe, press_key, hold_key)

Coordinate convention:
    All click/swipe coordinates are **fractional** values in [0.0, 1.0].
    (0.0, 0.0) = top-left, (1.0, 1.0) = bottom-right, (0.5, 0.5) = center.
    Internally converted to actual window pixels for input delivery.

Screenshot scaling:
    Captures are scaled down proportionally so that height ≤ MAX_HEIGHT (720).
    Aspect ratio is always preserved — no stretching.  Never upscales.

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

# Maximum screenshot output height.  Captures taller than this are scaled
# down proportionally (preserving aspect ratio).  Shorter captures are
# returned as-is (never upscaled).  720 keeps ~32 px icons readable and
# matches the effective OCR resolution.
MAX_HEIGHT = 720


class DeviceAdapter:
    """Low-level device I/O adapter wrapping MaaFramework's Win32 controller.

    All click/swipe coordinates are **fractional** ``(fx, fy)`` in [0.0, 1.0].
    Screenshots are proportionally scaled so height ≤ ``MAX_HEIGHT``.

    Example::

        from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG

        device = DeviceAdapter(AETHER_GAZER_CONFIG.to_device_config())
        device.connect()
        img = device.screenshot()       # proportionally-scaled BGR ndarray
        device.click(0.5, 0.5)          # fractional center click
        device.disconnect()
    """

    def __init__(self, config: DeviceConfig) -> None:
        self._config = config
        self._controller: Win32Controller | None = None
        self._hwnd: ctypes.c_void_p | None = None

        # Actual window resolution — set on connect(), None when disconnected.
        self._actual: Resolution | None = None
        # Last screenshot output dimensions (after proportional scaling).
        self._screenshot_res: Resolution | None = None

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
    def actual_resolution(self) -> Resolution:
        """Real window resolution detected after :meth:`connect`.

        Raises ``DeviceConnectionError`` if not connected.
        """
        if self._actual is None:
            raise DeviceConnectionError("Not connected — actual_resolution unavailable")
        return self._actual

    @property
    def resolution(self) -> tuple[int, int]:
        """Current screenshot output dimensions ``(width, height)`` after scaling.

        This is what downstream vision code (matcher, OCR) should use as
        the coordinate reference frame.

        Raises ``DeviceConnectionError`` if no screenshot has been taken yet.
        """
        if self._screenshot_res is None:
            raise DeviceConnectionError("No screenshot taken yet — resolution unknown")
        return (self._screenshot_res.width, self._screenshot_res.height)

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def find_window(self) -> ctypes.c_void_p:
        """Search for the game window by title.

        Two-pass matching:
        1. Exact title match (strongest signal)
        2. Substring match but ONLY for Unity windows (UnityWndClass)
           to avoid attaching to our own tool windows

        Returns:
            Win32 window handle (HWND) of the matching window.

        Raises:
            WindowNotFoundError: No matching window found.
        """
        windows = Toolkit.find_desktop_windows()
        title = self._config.window_title

        # Pass 1: exact title match
        for w in windows:
            if w.window_name == title:
                logger.info(
                    "Found game window (exact): title={!r} hwnd={} class={!r}",
                    w.window_name,
                    w.hwnd,
                    w.class_name,
                )
                return w.hwnd

        # Pass 2: substring match, Unity windows only
        for w in windows:
            if title in w.window_name and w.class_name == "UnityWndClass":
                logger.info(
                    "Found game window (Unity): title={!r} hwnd={} class={!r}",
                    w.window_name,
                    w.hwnd,
                    w.class_name,
                )
                return w.hwnd

        raise WindowNotFoundError(
            f"Window not found: {title!r}"
        )

    def connect(self) -> None:
        """Locate the game window and establish a MaaFw controller connection.

        Raises:
            WindowNotFoundError: Game window not found on the desktop.
            DeviceConnectionError: MaaFw controller could not be initialised.
        """
        self._connect_foreground()

    def _connect_foreground(self) -> None:
        """Standard foreground connection with screencap fallback.

        Tries the configured screencap method first, then falls back through
        increasingly compatible alternatives:
            FramePool → DXGI_DesktopDup → GDI
        """
        from maa.define import MaaWin32ScreencapMethodEnum

        self._hwnd = self.find_window()

        # Fallback chain: preferred method first, then progressively
        # more compatible (but potentially slower) alternatives.
        preferred = self._config.screencap_method
        fallbacks = [
            MaaWin32ScreencapMethodEnum.DXGI_DesktopDup,
            MaaWin32ScreencapMethodEnum.GDI,
        ]
        methods_to_try = [preferred] + [m for m in fallbacks if m != preferred]

        last_error: Exception | None = None
        for method in methods_to_try:
            try:
                logger.info(
                    "Trying screencap method: {}",
                    method.name if hasattr(method, 'name') else method,
                )
                self._controller = Win32Controller(
                    hWnd=self._hwnd,
                    screencap_method=method,
                    mouse_method=self._config.mouse_method,
                    keyboard_method=self._config.keyboard_method,
                )
                self._finish_connection()
                if method != preferred:
                    logger.warning(
                        "Using fallback screencap method '{}' (preferred '{}' failed)",
                        method.name if hasattr(method, 'name') else method,
                        preferred.name if hasattr(preferred, 'name') else preferred,
                    )
                return  # Success
            except (RuntimeError, OSError) as exc:
                last_error = exc
                logger.warning(
                    "Screencap method {} failed: {}",
                    method.name if hasattr(method, 'name') else method,
                    exc,
                )
                self._controller = None
                continue
            except DeviceConnectionError as exc:
                # _finish_connection raised — try next method
                last_error = exc
                logger.warning(
                    "Connection with {} failed: {}",
                    method.name if hasattr(method, 'name') else method,
                    exc,
                )
                self._controller = None
                continue

        # All methods exhausted
        raise DeviceConnectionError(
            f"All screencap methods failed. Last error: {last_error}\n"
            f"Please ensure Visual C++ Redistributable 2015-2022 is installed:\n"
            f"https://aka.ms/vs/17/release/vc_redist.x64.exe"
        )

    def _finish_connection(self) -> None:
        """Shared post-connection setup (raw size, screencap, aspect check)."""
        assert self._controller is not None

        self._controller.post_connection().wait()
        self._controller.set_screenshot_use_raw_size(True)
        self._controller.post_screencap().wait()

        actual_w, actual_h = self._controller.resolution
        self._actual = Resolution(width=actual_w, height=actual_h)

        if actual_w > 0 and actual_h > 0:
            ratio = actual_w / actual_h
            if abs(ratio - 16 / 9) > 0.02:
                self._controller = None
                self._hwnd = None
                self._actual = None
                raise DeviceConnectionError(
                    f"Unsupported aspect ratio: {actual_w}x{actual_h} "
                    f"({ratio:.3f}). Only 16:9 is supported. "
                    f"Please resize the game window to a 16:9 resolution "
                    f"(e.g. 1600x900, 1280x720, 1920x1080)."
                )

        logger.info(
            "DeviceAdapter connected: window={!r} resolution={}x{}",
            self._config.window_title, actual_w, actual_h,
        )

    def disconnect(self) -> None:
        """Release the controller and reset all connection state."""
        self._controller = None
        self._hwnd = None
        self._actual = None
        self._screenshot_res = None

        logger.info("DeviceAdapter disconnected: window={!r}", self._config.window_title)

    # ------------------------------------------------------------------
    # Device I/O
    # ------------------------------------------------------------------

    def screenshot(self) -> np.ndarray:
        """Capture a screenshot, proportionally scaled so height ≤ MAX_HEIGHT.

        Aspect ratio is always preserved.  Images shorter than MAX_HEIGHT
        are returned as-is (never upscaled).

        Returns:
            BGR ``numpy`` array at proportionally-scaled resolution.

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
        if h > MAX_HEIGHT:
            scale = MAX_HEIGHT / h
            new_w = int(w * scale)
            img = cv2.resize(img, (new_w, MAX_HEIGHT), interpolation=cv2.INTER_AREA)
            h, w = MAX_HEIGHT, new_w

        self._screenshot_res = Resolution(width=w, height=h)
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

    def click(self, fx: float, fy: float) -> None:
        """Send a mouse click at fractional coordinates.

        Args:
            fx: Horizontal position as fraction [0.0, 1.0].
            fy: Vertical position as fraction [0.0, 1.0].

        Raises:
            DeviceConnectionError: Not connected.
        """
        self._ensure_connected()
        assert self._controller is not None
        assert self._actual is not None

        ax = int(fx * self._actual.width)
        ay = int(fy * self._actual.height)

        self._controller.post_click(ax, ay).wait()
        logger.debug(
            "click ({:.3f}, {:.3f}) -> actual ({}, {})",
            fx, fy, ax, ay,
        )

    def swipe(
        self,
        fx1: float,
        fy1: float,
        fx2: float,
        fy2: float,
        duration: int = 500,
    ) -> None:
        """Perform a pointer swipe between two fractional coordinates.

        Args:
            fx1: Start X as fraction [0.0, 1.0].
            fy1: Start Y as fraction [0.0, 1.0].
            fx2: End X as fraction [0.0, 1.0].
            fy2: End Y as fraction [0.0, 1.0].
            duration: Swipe duration in milliseconds (default 500).

        Raises:
            DeviceConnectionError: Not connected.
        """
        self._ensure_connected()
        assert self._controller is not None
        assert self._actual is not None

        ax1 = int(fx1 * self._actual.width)
        ay1 = int(fy1 * self._actual.height)
        ax2 = int(fx2 * self._actual.width)
        ay2 = int(fy2 * self._actual.height)

        self._controller.post_swipe(ax1, ay1, ax2, ay2, duration).wait()
        logger.debug(
            "swipe ({:.3f},{:.3f}) -> ({:.3f},{:.3f})",
            fx1, fy1, fx2, fy2,
        )

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
