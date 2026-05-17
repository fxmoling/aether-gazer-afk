"""InputGuard — pin the OS cursor in place by absorbing user mouse input.

Background
----------
For Unity-based games (like Aether Gazer) the click position is read from
``GetCursorPos()`` at the time the game processes ``WM_LBUTTONDOWN`` /
``WM_LBUTTONUP``.  Our automation must therefore move the real cursor to
the target position before each click.  If the user happens to be moving
their mouse at that exact moment, the user's input races our
``SetCursorPos`` and the click lands at the wrong screen coord — which
can be catastrophic on commerce pages (one wrong click can spend gems).

``BlockInput`` is unusable: it requires admin, blocks the keyboard too,
has known stuck-Ctrl side effects under admin, and only the blocking
thread can release it.

Solution
--------
Install a low-level mouse hook (``WH_MOUSE_LL``) on a dedicated thread
that runs a Win32 message pump.  While locked, the hook returns ``1``
for any non-``INJECTED`` mouse event, which **drops the event before it
reaches the OS input queue** — the cursor physically cannot be moved by
the user.  Our own ``SetCursorPos`` calls do not go through the hook
(they don't generate hook events), so we can freely position the cursor.

This is the same technique MaaFw's ``WithWindowPos`` mode uses
internally; we adopt it for cursor pinning.

Properties
----------
- Per-process: no system-wide effect.  Other apps unaffected.
- Mouse-only: keyboard input is unaffected (no ``WH_KEYBOARD_LL``).
- Auto-cleanup: when the process exits, Windows unhooks automatically.
- No ``BlockInput``: zero risk of stuck modifiers / stuck input.
"""
from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes

from loguru import logger

# ---------------------------------------------------------------------------
# Win32 constants & structures
# ---------------------------------------------------------------------------

_WH_MOUSE_LL = 14
_HC_ACTION = 0
_LLMHF_INJECTED = 0x00000001
_WM_QUIT = 0x0012


class _MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


_HOOKPROC = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM,
)


class InputGuard:
    """Suppresses user mouse input while locked.

    Usage::

        guard = InputGuard()
        guard.start()
        try:
            with guard.locked():
                ctypes.windll.user32.SetCursorPos(x, y)
                send_click(...)
        finally:
            guard.stop()

    All ``lock()`` / ``unlock()`` calls are thread-safe.  The guard
    can be reused across many clicks; you do not need to start/stop
    around every click — ``locked()`` is the per-click gate.
    """

    def __init__(self) -> None:
        self._locked = False
        self._thread: threading.Thread | None = None
        self._tid: int = 0
        self._ready = threading.Event()
        self._stop_evt = threading.Event()
        self._hook: int | None = None
        # IMPORTANT: keep a strong reference to the trampoline so ctypes
        # doesn't garbage-collect it while the OS is still calling it.
        self._proc = _HOOKPROC(self._hook_proc)
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        # Configure signatures
        self._user32.SetWindowsHookExW.restype = wintypes.HHOOK
        self._user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int, _HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD,
        ]
        self._user32.CallNextHookEx.restype = ctypes.c_long
        self._user32.CallNextHookEx.argtypes = [
            wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM,
        ]
        self._user32.UnhookWindowsHookEx.restype = wintypes.BOOL
        self._user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
        self._user32.GetMessageW.restype = wintypes.BOOL
        self._user32.GetMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG), wintypes.HWND,
            wintypes.UINT, wintypes.UINT,
        ]
        self._user32.PostThreadMessageW.restype = wintypes.BOOL
        self._user32.PostThreadMessageW.argtypes = [
            wintypes.DWORD, wintypes.UINT,
            wintypes.WPARAM, wintypes.LPARAM,
        ]
        self._kernel32.GetCurrentThreadId.restype = wintypes.DWORD

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, timeout: float = 2.0) -> bool:
        """Spawn the guard thread and install the hook.

        Returns True on success (hook installed), False otherwise.
        Safe to call multiple times — subsequent calls are no-ops.
        """
        if self._thread is not None:
            return self._hook is not None
        self._ready.clear()
        self._stop_evt.clear()
        self._thread = threading.Thread(
            target=self._run, name="InputGuard", daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(timeout=timeout):
            logger.warning("InputGuard: hook install timed out")
            return False
        ok = self._hook is not None
        if ok:
            logger.info("InputGuard: ready")
        return ok

    def stop(self) -> None:
        """Uninstall the hook and stop the guard thread."""
        if self._thread is None:
            return
        self._stop_evt.set()
        if self._tid:
            try:
                self._user32.PostThreadMessageW(self._tid, _WM_QUIT, 0, 0)
            except Exception as exc:  # noqa: BLE001
                logger.debug("InputGuard: PostThreadMessage failed: {}", exc)
        self._thread.join(timeout=2.0)
        self._thread = None
        self._tid = 0
        self._locked = False

    # ------------------------------------------------------------------
    # Per-click gate
    # ------------------------------------------------------------------

    def lock(self) -> None:
        """Begin absorbing user mouse input."""
        self._locked = True

    def unlock(self) -> None:
        """Resume normal user mouse input."""
        self._locked = False

    @property
    def is_active(self) -> bool:
        """True when the guard thread is running and the hook is installed."""
        return self._thread is not None and self._hook is not None

    def locked(self) -> "_LockedContext":
        """Context manager: lock for the body, unlock on exit."""
        return _LockedContext(self)

    # ------------------------------------------------------------------
    # Hook callback (runs on the guard thread)
    # ------------------------------------------------------------------

    def _hook_proc(self, nCode, wParam, lParam):
        if nCode == _HC_ACTION and self._locked:
            info = ctypes.cast(
                lParam, ctypes.POINTER(_MSLLHOOKSTRUCT),
            ).contents
            # Only absorb real user events.  Our SetCursorPos doesn't
            # generate hook events, but defensively pass through anything
            # the OS marks as INJECTED in case other tools are involved.
            if not (info.flags & _LLMHF_INJECTED):
                return 1
        return self._user32.CallNextHookEx(
            wintypes.HHOOK(0), nCode, wParam, lParam,
        )

    # ------------------------------------------------------------------
    # Guard thread main
    # ------------------------------------------------------------------

    def _run(self) -> None:
        self._tid = self._kernel32.GetCurrentThreadId()
        self._hook = self._user32.SetWindowsHookExW(
            _WH_MOUSE_LL, self._proc, wintypes.HINSTANCE(0), 0,
        )
        if not self._hook:
            err = ctypes.get_last_error()
            logger.warning(
                "InputGuard: SetWindowsHookExW failed (err={})", err,
            )
            self._hook = None
            self._ready.set()
            return
        logger.info(
            "InputGuard: hook installed handle={:#x} tid={}",
            self._hook, self._tid,
        )
        self._ready.set()

        msg = wintypes.MSG()
        try:
            while not self._stop_evt.is_set():
                ret = self._user32.GetMessageW(
                    ctypes.byref(msg), wintypes.HWND(0), 0, 0,
                )
                if ret == 0 or ret == -1:  # WM_QUIT or error
                    break
                # No special dispatch needed; the hook runs out-of-band.
        except Exception as exc:  # noqa: BLE001
            logger.warning("InputGuard: message pump exception: {}", exc)
        finally:
            try:
                if self._hook:
                    self._user32.UnhookWindowsHookEx(self._hook)
            except Exception:  # noqa: BLE001
                pass
            self._hook = None
            logger.info("InputGuard: hook uninstalled")


class _LockedContext:
    __slots__ = ("_guard",)

    def __init__(self, guard: InputGuard) -> None:
        self._guard = guard

    def __enter__(self) -> InputGuard:
        self._guard.lock()
        return self._guard

    def __exit__(self, *args) -> None:
        self._guard.unlock()
