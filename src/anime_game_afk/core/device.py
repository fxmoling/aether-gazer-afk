"""DeviceAdapter — single point of contact with MaaFramework for device I/O.

Responsibilities:
- Window discovery and connection lifecycle (connect / disconnect)
- Screenshot capture with proportional scaling (height-capped, aspect-ratio preserved)
- Input delegation via fractional coordinates (click, swipe, press_key, hold_key)
- Custom click implementation that hides cursor instead of BlockInput

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
import ctypes.wintypes
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

# Win32 API constants and functions
_user32 = ctypes.windll.user32

WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001

# SWP flags
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.wintypes.LONG), ("y", ctypes.wintypes.LONG)]


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.wintypes.LONG),
        ("top", ctypes.wintypes.LONG),
        ("right", ctypes.wintypes.LONG),
        ("bottom", ctypes.wintypes.LONG),
    ]


def _client_to_screen(hwnd, x: int, y: int) -> tuple[int, int]:
    """Convert client coordinates to screen coordinates."""
    pt = _POINT(x, y)
    _user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return pt.x, pt.y


def _send_click(hwnd, client_x: int, client_y: int) -> None:
    """Send a click via SetCursorPos + SendMessage, with cursor hidden.

    This avoids MaaFramework's BlockInput(TRUE) which blocks all
    keyboard and mouse input system-wide. Instead we:
    1. Hide the cursor (ShowCursor(FALSE))
    2. Save + move cursor to target screen position
    3. SendMessage WM_MOUSEMOVE + WM_LBUTTONDOWN + WM_LBUTTONUP
    4. Restore cursor to original position
    5. Show cursor (ShowCursor(TRUE))

    The cursor is invisible during the move so users see no flicker,
    and keyboard input is never blocked.
    """
    # Save original cursor position
    orig = _POINT()
    _user32.GetCursorPos(ctypes.byref(orig))

    # Convert client coords to screen coords
    sx, sy = _client_to_screen(hwnd, client_x, client_y)

    # Hide cursor → move → click → restore → show
    _user32.ShowCursor(False)
    try:
        _user32.SetCursorPos(sx, sy)
        time.sleep(0.001)  # 1ms settle (MaaFw uses 1ms too)

        lparam = client_y << 16 | (client_x & 0xFFFF)
        _user32.SendMessageW(hwnd, WM_MOUSEMOVE, 0, lparam)
        _user32.SendMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
        time.sleep(0.01)  # 10ms hold
        _user32.SendMessageW(hwnd, WM_LBUTTONUP, 0, lparam)

        time.sleep(0.001)
        _user32.SetCursorPos(orig.x, orig.y)
    finally:
        _user32.ShowCursor(True)


class DeviceAdapter:
    """Low-level device I/O adapter wrapping MaaFramework's Win32 controller.

    All click/swipe coordinates are **fractional** ``(fx, fy)`` in [0.0, 1.0].
    Screenshots are proportionally scaled so height ≤ ``MAX_HEIGHT``.

    Example::

        config = DeviceConfig(window_title="MyGame")
        device = DeviceAdapter(config)
        device.connect()
        img = device.screenshot()       # proportionally-scaled BGR ndarray
        device.click(0.5, 0.5)          # fractional center click
        device.disconnect()
    """

    def __init__(self, config: DeviceConfig) -> None:
        self._config = config
        self._controller: Win32Controller | None = None
        self._hwnd: ctypes.c_void_p | None = None
        self._use_custom_click: bool = False

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

        logger.info(
            "DeviceAdapter connected: window={!r} resolution={}x{}",
            self._config.window_title, actual_w, actual_h,
        )

        # Enable custom click (ShowCursor hide instead of BlockInput)
        self._use_custom_click = True

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
        logger.debug("click ({:.3f}, {:.3f}) -> actual ({}, {})", fx, fy, ax, ay)

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
