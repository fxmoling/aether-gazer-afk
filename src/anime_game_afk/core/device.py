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
import threading
import time
from ctypes import wintypes as _wintypes

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


# OS-level KEYUP for common modifiers via SendInput.
# MaaFw's `post_key_up` only sends WM_KEYUP scoped to the game window
# and cannot clear the OS global modifier state.  If something leaves
# Ctrl/Shift/Alt/Win "down" globally (BlockInput leftover, Ctrl-signal
# tricks, etc.) the user's own clicks/keys behave wrong even after the
# script stops.  SendInput pushes a real KEYUP into the OS input queue
# and is the only reliable cure.  Safe to call when keys aren't down.
_KEYEVENTF_KEYUP = 0x0002
_INPUT_KEYBOARD = 1
_MODIFIER_VKS = (
    0x10, 0x11, 0x12,  # Shift, Ctrl, Alt (generic)
    0xA0, 0xA1,        # L/R Shift
    0xA2, 0xA3,        # L/R Ctrl
    0xA4, 0xA5,        # L/R Alt
    0x5B, 0x5C,        # L/R Win
)


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_uint),
        ("time", ctypes.c_uint),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT)]


class _INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", ctypes.c_uint), ("u", _INPUT_UNION)]


def _release_modifiers_globally() -> int:
    """Send OS-level KEYUP for all common modifiers via SendInput.

    Returns the number of events Windows accepted.  No-op safe.
    """
    try:
        inputs = (_INPUT * len(_MODIFIER_VKS))()
        for i, vk in enumerate(_MODIFIER_VKS):
            inputs[i].type = _INPUT_KEYBOARD
            inputs[i].ki = _KEYBDINPUT(
                wVk=vk, wScan=0, dwFlags=_KEYEVENTF_KEYUP,
                time=0, dwExtraInfo=None,
            )
        sent = ctypes.windll.user32.SendInput(
            len(inputs), ctypes.byref(inputs), ctypes.sizeof(_INPUT)
        )
        return int(sent)
    except (AttributeError, OSError) as exc:
        logger.debug("SendInput modifier release failed: {}", exc)
        return 0


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
        self._input_lock = threading.Lock()
        # Low-level mouse hook guard: pins the cursor in place while we
        # click, so a user moving the mouse cannot deflect the click.
        # Started lazily on first connect(); stopped on disconnect().
        from anime_game_afk.core.input_guard import InputGuard
        self._input_guard: InputGuard = InputGuard()

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
        # Start the low-level mouse hook so subsequent clicks can pin the
        # cursor.  Best-effort: if the hook fails to install (rare, e.g.
        # restrictive AV policy) clicks still work, just without the user
        # mouse protection.
        if not self._input_guard.is_active:
            self._input_guard.start()

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
                # NOTE: do NOT reset self._hwnd here — the fallback loop
                # in _connect_foreground still needs it for the next method.
                self._actual = None
                raise DeviceConnectionError(
                    f"Unsupported aspect ratio: {actual_w}x{actual_h} "
                    f"({ratio:.3f}). Only 16:9 is supported. "
                    f"Please resize the game window to a 16:9 resolution "
                    f"(e.g. 1600x900, 1280x720, 1920x1080)."
                )

        logger.info(
            "Device connected: hwnd={}, resolution={}x{}, screencap={}, mouse={}, keyboard={}",
            self._hwnd, actual_w, actual_h,
            self._config.screencap_method.name if hasattr(self._config.screencap_method, 'name') else self._config.screencap_method,
            self._config.mouse_method.name if hasattr(self._config.mouse_method, 'name') else self._config.mouse_method,
            self._config.keyboard_method.name if hasattr(self._config.keyboard_method, 'name') else self._config.keyboard_method,
        )

    def disconnect(self) -> None:
        """Release the controller and reset all connection state.

        Calls MAA's ``post_inactive()`` first — this is the only API that
        triggers MaaFw's C++ ``unblock_input()`` (i.e. ``BlockInput(FALSE)``
        from the same thread that called ``BlockInput(TRUE)``).  Without
        this the user's keyboard/mouse can stay blocked until Python GC
        eventually destroys the controller, which can take seconds or
        require manual intervention (e.g. pressing Ctrl).

        Then releases any keys we may have left held, clears local state,
        and drops the controller reference.  Best-effort throughout —
        disconnect must never raise.
        """
        logger.info("Device disconnecting: hwnd={}", self._hwnd)

        # 1. Tell MaaFw to unblock input + restore window position.
        #    This is THE call that releases BlockInput from MaaFw's
        #    internal worker thread (the only thread allowed to do so).
        if self._controller is not None:
            try:
                self._controller.post_inactive().wait()
            except Exception as exc:  # noqa: BLE001
                logger.warning("disconnect: post_inactive failed: {}", exc)

        # 2. Send key_up for any key we may have left held + final
        #    BlockInput(FALSE) safety net from this Python thread.
        try:
            self.release_all_held_keys()
        except Exception as exc:  # noqa: BLE001
            logger.warning("disconnect: release_all_held_keys failed: {}", exc)

        # 3. Stop the input guard (uninstalls the WH_MOUSE_LL hook).
        try:
            self._input_guard.stop()
        except Exception as exc:  # noqa: BLE001
            logger.warning("disconnect: input_guard stop failed: {}", exc)

        self._controller = None
        self._hwnd = None
        self._actual = None
        self._screenshot_res = None

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

        _start = time.perf_counter()
        img: np.ndarray | None = (
            self._controller.post_screencap().wait().get()
        )
        if img is None:
            raise ScreenshotError("post_screencap returned None")

        raw_h, raw_w = img.shape[:2]
        if raw_h > MAX_HEIGHT:
            scale = MAX_HEIGHT / raw_h
            new_w = int(raw_w * scale)
            img = cv2.resize(img, (new_w, MAX_HEIGHT), interpolation=cv2.INTER_AREA)
            h, w = MAX_HEIGHT, new_w
        else:
            h, w = raw_h, raw_w

        _elapsed_ms = (time.perf_counter() - _start) * 1000
        logger.debug(
            "Screenshot: {:.0f}ms, raw={}x{}, scaled={}x{}",
            _elapsed_ms, raw_w, raw_h, w, h,
        )

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

        While the click is being delivered we lock the InputGuard, which
        absorbs any real user mouse input via WH_MOUSE_LL.  Combined
        with our own ``SetCursorPos`` to the target, this guarantees the
        cursor is exactly at the target screen position when the game
        processes ``WM_LBUTTONDOWN`` / ``WM_LBUTTONUP``, regardless of
        what the user does with their mouse.

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

        # Resolve target in screen coords and snapshot the current cursor
        # so we can restore it after the click.
        target_screen = self._client_to_screen(ax, ay)
        orig_cursor = self._get_cursor_pos()

        with self._input_lock:
            with self._input_guard.locked():
                if target_screen is not None:
                    self._set_cursor_pos(*target_screen)
                    # Brief settle so the OS observes the new cursor pos
                    # before the game receives the click message.
                    time.sleep(0.008)
                try:
                    self._controller.post_click(ax, ay).wait()
                finally:
                    # Let the game finish reading WM_LBUTTONUP before we
                    # restore the cursor; otherwise the restored position
                    # could leak into the click handler.
                    time.sleep(0.008)
                    if orig_cursor is not None:
                        self._set_cursor_pos(*orig_cursor)
        logger.debug(
            "click ({:.3f}, {:.3f}) -> actual ({}, {}) screen={}",
            fx, fy, ax, ay, target_screen,
        )

    # ------------------------------------------------------------------
    # Win32 cursor helpers (used by click() to pin cursor on target)
    # ------------------------------------------------------------------

    # DPI awareness context: PER_MONITOR_AWARE_V2 makes ClientToScreen and
    # SetCursorPos work in *physical* pixels — the same coordinate system
    # the (DPI-aware) game window uses.  Python's main thread is usually
    # DPI-unaware, so without this call, ClientToScreen returns virtualized
    # logical coords and SetCursorPos lands the cursor in the wrong screen
    # position under HiDPI display scaling (125%/150% etc).
    _DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4

    @staticmethod
    def _ensure_thread_dpi_aware() -> None:
        """Switch the calling thread to PER_MONITOR_AWARE_V2.

        Best-effort, idempotent at the Windows kernel level (cheap to call
        repeatedly).  DPI awareness is per-thread; we set it inline before
        every ClientToScreen / SetCursorPos so any thread that ends up
        running click() is in the correct coordinate space.
        """
        try:
            ctypes.windll.user32.SetThreadDpiAwarenessContext(
                ctypes.c_void_p(
                    DeviceAdapter._DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
                )
            )
        except (AttributeError, OSError) as exc:
            logger.debug("SetThreadDpiAwarenessContext failed: {}", exc)

    def _client_to_screen(self, ax: int, ay: int) -> tuple[int, int] | None:
        """Translate client-area pixel coords to absolute screen coords."""
        self._ensure_thread_dpi_aware()
        if self._hwnd is None:
            return None
        pt = _wintypes.POINT(int(ax), int(ay))
        try:
            ok = ctypes.windll.user32.ClientToScreen(
                self._hwnd, ctypes.byref(pt),
            )
            if not ok:
                return None
        except (AttributeError, OSError) as exc:
            logger.debug("ClientToScreen failed: {}", exc)
            return None
        return (pt.x, pt.y)

    @staticmethod
    def _get_cursor_pos() -> tuple[int, int] | None:
        DeviceAdapter._ensure_thread_dpi_aware()
        pt = _wintypes.POINT()
        try:
            if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
                return (pt.x, pt.y)
        except (AttributeError, OSError) as exc:
            logger.debug("GetCursorPos failed: {}", exc)
        return None

    @staticmethod
    def _set_cursor_pos(x: int, y: int) -> bool:
        DeviceAdapter._ensure_thread_dpi_aware()
        try:
            return bool(
                ctypes.windll.user32.SetCursorPos(int(x), int(y))
            )
        except (AttributeError, OSError) as exc:
            logger.debug("SetCursorPos failed: {}", exc)
            return False

    def swipe(
        self,
        fx1: float,
        fy1: float,
        fx2: float,
        fy2: float,
        duration: int = 500,
    ) -> None:
        """Perform a pointer swipe between two fractional coordinates.

        Under the plain ``SendMessage`` mouse method MaaFw does not move
        the cursor.  To make swipes work for Unity (which reads
        ``GetCursorPos()`` during drag), we run a parallel interpolation
        thread that linearly walks the cursor from start to end over the
        swipe ``duration``.  The InputGuard absorbs any user mouse input
        during that window so the user cannot deflect the swipe.

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

        start_screen = self._client_to_screen(ax1, ay1)
        end_screen = self._client_to_screen(ax2, ay2)
        orig_cursor = self._get_cursor_pos()

        with self._input_lock:
            with self._input_guard.locked():
                stop_evt = threading.Event()
                mover: threading.Thread | None = None
                if start_screen is not None and end_screen is not None:
                    mover = threading.Thread(
                        target=self._cursor_walk,
                        args=(start_screen, end_screen,
                              duration / 1000.0, stop_evt),
                        name="CursorWalk",
                        daemon=True,
                    )
                    mover.start()
                    # Brief settle so the start position is visible to
                    # the game before MaaFw sends WM_LBUTTONDOWN.
                    time.sleep(0.008)
                try:
                    self._controller.post_swipe(
                        ax1, ay1, ax2, ay2, duration,
                    ).wait()
                finally:
                    stop_evt.set()
                    if mover is not None:
                        mover.join(timeout=0.5)
                    # Park cursor at end before restore so the game's
                    # mouse-up handler sees the final position.
                    if end_screen is not None:
                        self._set_cursor_pos(*end_screen)
                        time.sleep(0.008)
                    if orig_cursor is not None:
                        self._set_cursor_pos(*orig_cursor)
        logger.debug(
            "swipe ({:.3f},{:.3f})->({:.3f},{:.3f}) duration={}ms -> "
            "pixel ({},{})->({},{}) screen={}->{}",
            fx1, fy1, fx2, fy2, duration, ax1, ay1, ax2, ay2,
            start_screen, end_screen,
        )

    def _cursor_walk(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        duration_s: float,
        stop_evt: threading.Event,
    ) -> None:
        """Linearly interpolate the cursor from ``start`` to ``end``.

        Runs on a dedicated thread so it can race MaaFw's WM_MOUSEMOVE
        sequence.  Each interpolation step calls SetCursorPos so the
        game's ``GetCursorPos()`` reads the right intermediate position.
        """
        # Ensure this thread is DPI-aware too.
        self._ensure_thread_dpi_aware()
        x1, y1 = start
        x2, y2 = end
        # 120Hz step rate (≥ display refresh) keeps the path smooth.
        step_dt = 0.008
        t0 = time.perf_counter()
        while not stop_evt.is_set():
            elapsed = time.perf_counter() - t0
            t = elapsed / duration_s if duration_s > 0 else 1.0
            if t >= 1.0:
                self._set_cursor_pos(x2, y2)
                return
            x = int(x1 + (x2 - x1) * t)
            y = int(y1 + (y2 - y1) * t)
            self._set_cursor_pos(x, y)
            # Use the stop_evt as a wakeable sleep so we exit promptly
            # when MaaFw's post_swipe returns early.
            if stop_evt.wait(step_dt):
                self._set_cursor_pos(x2, y2)
                return

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
        """Hold a key for a given duration using key_down + sleep + key_up.

        Args:
            vk_code: Virtual-key code (Win32 VK_* constant).
            duration_s: How long to hold the key in seconds.

        Raises:
            DeviceConnectionError: Not connected.

        Notes:
            ``key_up`` is sent even if ``time.sleep`` is interrupted (e.g. by
            ``KeyboardInterrupt``) to avoid leaving the game with a key stuck
            in the held-down state.  If the entire process is killed mid-sleep,
            this guard cannot run — :meth:`release_all_held_keys` should be
            called by the parent process after killing the worker.
        """
        self._ensure_connected()
        assert self._controller is not None

        self._controller.post_key_down(vk_code).wait()
        try:
            time.sleep(duration_s)
        finally:
            try:
                self._controller.post_key_up(vk_code).wait()
            except Exception as exc:  # noqa: BLE001 — best-effort release
                logger.warning(
                    "hold_key 0x{:02X}: key_up failed during cleanup: {}",
                    vk_code, exc,
                )
        logger.debug(
            "hold_key 0x{:02X} for {:.2f}s (key_down/key_up)",
            vk_code, duration_s,
        )

    # ------------------------------------------------------------------
    # Recovery / cleanup — release stuck input state
    # ------------------------------------------------------------------

    # Keys that any task / combat script may have left held in the game
    # window.  Sending ``key_up`` for each of these is harmless when the key
    # wasn't held; it costs ~1 SendMessage per key (well under 50ms total).
    _RECOVERY_VK_CODES: tuple[int, ...] = (
        # Movement / camera
        0x57, 0x41, 0x53, 0x44, 0x51, 0x45,            # W A S D Q E
        # Combat
        0x4A, 0x4B, 0x55, 0x49, 0x4F, 0x52,            # J K U I O R
        0x31, 0x32,                                     # 1 2
        # UI / panels
        0x47, 0x48, 0x54,                               # G H T
        # Special
        0x0D, 0x1B, 0x09, 0x20,                         # Enter Esc Tab Space
        # Modifiers (extra-stuck-prone)
        0x10, 0x11, 0x12,                               # Shift Ctrl Alt
        0xA0, 0xA1, 0xA2, 0xA3,                         # L/R Shift, L/R Ctrl
        0x5B, 0x5C,                                     # L/R Win
    )

    def release_all_held_keys(self) -> None:
        """Send ``key_up`` for every key the bot might have left held.

        Idempotent and safe to call when no keys are stuck.  Used to recover
        from worker crashes / forced stops where ``hold_key`` did not get
        a chance to finish its cleanup.

        Sends WM_KEYUP via the MAA controller (window-targeted, harmless to
        other apps).  Also calls Win32 ``BlockInput(FALSE)`` from the current
        thread as a safety net in case a previous operation left the system
        with input blocked.
        """
        if self._controller is None:
            logger.debug("release_all_held_keys: not connected, skipping")
            return

        for vk in self._RECOVERY_VK_CODES:
            try:
                self._controller.post_key_up(vk).wait()
            except Exception as exc:  # noqa: BLE001 — best-effort cleanup
                logger.debug("release_all_held_keys: 0x{:02X} failed: {}", vk, exc)

        try:
            ctypes.windll.user32.BlockInput(False)
        except Exception as exc:  # noqa: BLE001
            logger.debug("release_all_held_keys: BlockInput(FALSE) failed: {}", exc)

        # OS-level modifier release. The post_key_up calls above only
        # send WM_KEYUP to the game window and cannot clear stuck
        # Ctrl/Shift/Alt/Win in the global OS key state.
        sent = _release_modifiers_globally()

        logger.info(
            "release_all_held_keys: window key_up x{} + BlockInput(FALSE) + global modifier release x{}",
            len(self._RECOVERY_VK_CODES), sent,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_connected(self) -> None:
        """Raise :exc:`DeviceConnectionError` if not currently connected."""
        if not self.connected:
            raise DeviceConnectionError("DeviceAdapter is not connected")
