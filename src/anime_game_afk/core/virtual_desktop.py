"""Win32 virtual desktop lifecycle manager for background game execution.

Creates a hidden desktop via ``CreateDesktopW``, launches the game there,
and provides window discovery via ``EnumDesktopWindows`` (which, unlike
``FindWindow``, searches the specified desktop rather than the caller's).

Usage::

    with VirtualDesktop() as vd:
        vd.launch(r"C:\\Games\\AetherGazer.exe")
        hwnd = vd.find_window("AetherGazer", timeout=120)
        # ... use hwnd with Win32Controller ...
"""
from __future__ import annotations

import atexit
import ctypes
import ctypes.wintypes
import time
from typing import Callable

from anime_game_afk.runtime.logger import get_logger

logger = get_logger("core.virtual_desktop")

# ---------------------------------------------------------------------------
# Win32 constants
# ---------------------------------------------------------------------------

GENERIC_ALL = 0x10000000
DESKTOP_CREATEWINDOW = 0x0002
DESKTOP_ENUMERATE = 0x0040
CREATE_NEW_CONSOLE = 0x00000010
NORMAL_PRIORITY_CLASS = 0x00000020
PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_INFORMATION = 0x0400
STILL_ACTIVE = 259
INFINITE = 0xFFFFFFFF

# ---------------------------------------------------------------------------
# Win32 struct definitions
# ---------------------------------------------------------------------------


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.wintypes.DWORD),
        ("lpReserved", ctypes.wintypes.LPWSTR),
        ("lpDesktop", ctypes.wintypes.LPWSTR),
        ("lpTitle", ctypes.wintypes.LPWSTR),
        ("dwX", ctypes.wintypes.DWORD),
        ("dwY", ctypes.wintypes.DWORD),
        ("dwXSize", ctypes.wintypes.DWORD),
        ("dwYSize", ctypes.wintypes.DWORD),
        ("dwXCountChars", ctypes.wintypes.DWORD),
        ("dwYCountChars", ctypes.wintypes.DWORD),
        ("dwFillAttribute", ctypes.wintypes.DWORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("wShowWindow", ctypes.wintypes.WORD),
        ("cbReserved2", ctypes.wintypes.WORD),
        ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", ctypes.wintypes.HANDLE),
        ("hStdOutput", ctypes.wintypes.HANDLE),
        ("hStdError", ctypes.wintypes.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", ctypes.wintypes.HANDLE),
        ("hThread", ctypes.wintypes.HANDLE),
        ("dwProcessId", ctypes.wintypes.DWORD),
        ("dwThreadId", ctypes.wintypes.DWORD),
    ]


# ---------------------------------------------------------------------------
# Win32 API bindings
# ---------------------------------------------------------------------------

_kernel32 = ctypes.windll.kernel32
_user32 = ctypes.windll.user32

_CreateDesktopW = _user32.CreateDesktopW
_CreateDesktopW.restype = ctypes.wintypes.HDESK
_CreateDesktopW.argtypes = [
    ctypes.wintypes.LPCWSTR,  # lpszDesktop
    ctypes.wintypes.LPCWSTR,  # lpszDevice (NULL)
    ctypes.c_void_p,          # pDevmode (NULL)
    ctypes.wintypes.DWORD,    # dwFlags
    ctypes.wintypes.DWORD,    # dwDesiredAccess
    ctypes.c_void_p,          # lpsa (NULL)
]

_CloseDesktop = _user32.CloseDesktop
_CloseDesktop.restype = ctypes.wintypes.BOOL
_CloseDesktop.argtypes = [ctypes.wintypes.HDESK]

_CreateProcessW = _kernel32.CreateProcessW
_CreateProcessW.restype = ctypes.wintypes.BOOL
_CreateProcessW.argtypes = [
    ctypes.wintypes.LPCWSTR,              # lpApplicationName
    ctypes.wintypes.LPWSTR,               # lpCommandLine
    ctypes.c_void_p,                      # lpProcessAttributes
    ctypes.c_void_p,                      # lpThreadAttributes
    ctypes.wintypes.BOOL,                 # bInheritHandles
    ctypes.wintypes.DWORD,                # dwCreationFlags
    ctypes.c_void_p,                      # lpEnvironment
    ctypes.wintypes.LPCWSTR,              # lpCurrentDirectory
    ctypes.POINTER(STARTUPINFOW),         # lpStartupInfo
    ctypes.POINTER(PROCESS_INFORMATION),  # lpProcessInformation
]

_TerminateProcess = _kernel32.TerminateProcess
_TerminateProcess.restype = ctypes.wintypes.BOOL
_TerminateProcess.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.UINT]

_CloseHandle = _kernel32.CloseHandle
_CloseHandle.restype = ctypes.wintypes.BOOL
_CloseHandle.argtypes = [ctypes.wintypes.HANDLE]

_GetExitCodeProcess = _kernel32.GetExitCodeProcess
_GetExitCodeProcess.restype = ctypes.wintypes.BOOL
_GetExitCodeProcess.argtypes = [
    ctypes.wintypes.HANDLE,
    ctypes.POINTER(ctypes.wintypes.DWORD),
]

# EnumDesktopWindows callback type
WNDENUMPROC = ctypes.WINFUNCTYPE(
    ctypes.wintypes.BOOL,
    ctypes.wintypes.HWND,
    ctypes.wintypes.LPARAM,
)

_EnumDesktopWindows = _user32.EnumDesktopWindows
_EnumDesktopWindows.restype = ctypes.wintypes.BOOL
_EnumDesktopWindows.argtypes = [
    ctypes.wintypes.HDESK,  # hDesktop
    WNDENUMPROC,            # lpfn
    ctypes.wintypes.LPARAM, # lParam
]

_GetWindowTextW = _user32.GetWindowTextW
_GetWindowTextW.restype = ctypes.c_int
_GetWindowTextW.argtypes = [
    ctypes.wintypes.HWND,
    ctypes.wintypes.LPWSTR,
    ctypes.c_int,
]

_GetWindowTextLengthW = _user32.GetWindowTextLengthW
_GetWindowTextLengthW.restype = ctypes.c_int
_GetWindowTextLengthW.argtypes = [ctypes.wintypes.HWND]

_IsWindowVisible = _user32.IsWindowVisible
_IsWindowVisible.restype = ctypes.wintypes.BOOL
_IsWindowVisible.argtypes = [ctypes.wintypes.HWND]


# ---------------------------------------------------------------------------
# VirtualDesktop class
# ---------------------------------------------------------------------------

# Module-level set of active instances for atexit safety-net cleanup
_active_instances: set[VirtualDesktop] = set()


def _atexit_cleanup() -> None:
    """Safety net: destroy any surviving VirtualDesktop instances on exit."""
    for vd in list(_active_instances):
        try:
            vd.destroy()
        except Exception:
            pass


atexit.register(_atexit_cleanup)


class VirtualDesktop:
    """Manages a hidden Win32 desktop for background game execution."""

    def __init__(self, name: str = "AFK_Background") -> None:
        self.name = name
        self._hdesk: ctypes.wintypes.HDESK | None = None
        self._game_pid: int | None = None
        self._game_hproc: ctypes.wintypes.HANDLE | None = None
        self._thread_handle: ctypes.wintypes.HANDLE | None = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def active(self) -> bool:
        """True when a virtual desktop handle is open."""
        return self._hdesk is not None

    @property
    def hdesk(self):
        """The raw Win32 desktop handle (HDESK), or None if not created.

        Used by DeviceAdapter to switch thread desktop for background clicks.
        """
        return self._hdesk

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def create(self) -> None:
        """Create the virtual desktop. Idempotent — safe to call twice."""
        if self._hdesk is not None:
            return

        hdesk = _CreateDesktopW(
            self.name,  # desktop name
            None,       # device (NULL)
            None,       # devmode (NULL)
            0,          # flags
            GENERIC_ALL,
            None,       # security attributes (NULL)
        )
        if not hdesk:
            raise OSError(
                f"CreateDesktopW failed (error {ctypes.GetLastError()})"
            )
        self._hdesk = hdesk
        _active_instances.add(self)
        logger.info(
            "Virtual desktop created: name={name}", name=self.name,
        )

    def launch(self, exe_path: str) -> int:
        """Launch a process on the virtual desktop.

        Args:
            exe_path: Full path to the executable.

        Returns:
            Process ID (PID) of the launched process.

        Raises:
            RuntimeError: If the desktop hasn't been created or launch fails.
        """
        if self._hdesk is None:
            raise RuntimeError("Virtual desktop not created — call create() first")

        si = STARTUPINFOW()
        si.cb = ctypes.sizeof(STARTUPINFOW)
        si.lpDesktop = self.name  # target desktop by NAME

        pi = PROCESS_INFORMATION()

        ok = _CreateProcessW(
            exe_path,                          # lpApplicationName
            None,                              # lpCommandLine
            None,                              # lpProcessAttributes
            None,                              # lpThreadAttributes
            False,                             # bInheritHandles
            NORMAL_PRIORITY_CLASS,             # dwCreationFlags
            None,                              # lpEnvironment
            None,                              # lpCurrentDirectory
            ctypes.byref(si),
            ctypes.byref(pi),
        )
        if not ok:
            raise RuntimeError(
                f"CreateProcessW failed for {exe_path!r} "
                f"(error {ctypes.GetLastError()})"
            )

        self._game_pid = pi.dwProcessId
        self._game_hproc = pi.hProcess
        self._thread_handle = pi.hThread

        # Close the thread handle — we only need the process handle
        if self._thread_handle:
            _CloseHandle(self._thread_handle)
            self._thread_handle = None

        logger.info(
            "Game launched on virtual desktop: exe={exe} pid={pid}",
            exe=exe_path, pid=self._game_pid,
        )
        return self._game_pid

    def find_window(self, title: str, timeout: float = 120) -> int:
        """Poll for a window with the given title on this desktop.

        Uses ``EnumDesktopWindows`` which searches the target desktop,
        not the caller's desktop.

        Args:
            title: Exact window title to search for.
            timeout: Maximum seconds to wait.

        Returns:
            Window handle (HWND) as an integer.

        Raises:
            RuntimeError: Desktop not created.
            TimeoutError: Window not found within timeout.
        """
        if self._hdesk is None:
            raise RuntimeError("Virtual desktop not created — call create() first")

        deadline = time.monotonic() + timeout
        poll_interval = 1.0

        while time.monotonic() < deadline:
            found_hwnd = self._enum_windows(title)
            if found_hwnd:
                logger.info(
                    "Found window on virtual desktop: title={title!r} hwnd={hwnd}",
                    title=title, hwnd=found_hwnd,
                )
                return found_hwnd
            time.sleep(poll_interval)

        raise TimeoutError(
            f"Window {title!r} not found on desktop {self.name!r} "
            f"after {timeout}s"
        )

    def _enum_windows(self, title: str) -> int | None:
        """Enumerate windows on this desktop, return HWND matching title."""
        result: list[int] = []

        @WNDENUMPROC
        def _callback(hwnd: ctypes.wintypes.HWND, lparam: ctypes.wintypes.LPARAM) -> bool:
            length = _GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                _GetWindowTextW(hwnd, buf, length + 1)
                if buf.value == title:
                    result.append(int(hwnd))  # type: ignore[arg-type]
                    return False  # stop enumeration
            return True  # continue

        _EnumDesktopWindows(self._hdesk, _callback, 0)
        return result[0] if result else None

    def _is_game_alive(self) -> bool:
        """Check if the game process is still running."""
        if self._game_hproc is None:
            return False
        exit_code = ctypes.wintypes.DWORD()
        _GetExitCodeProcess(self._game_hproc, ctypes.byref(exit_code))
        return exit_code.value == STILL_ACTIVE

    def terminate_game(self) -> None:
        """Terminate the game process if still alive."""
        if self._game_hproc is None:
            return

        if self._is_game_alive():
            _TerminateProcess(self._game_hproc, 1)
            logger.info(
                "Game process terminated: pid={pid}", pid=self._game_pid,
            )

        _CloseHandle(self._game_hproc)
        self._game_hproc = None
        self._game_pid = None

    def destroy(self) -> None:
        """Terminate game and close the virtual desktop. Safe to call multiple times."""
        self.terminate_game()

        if self._hdesk is not None:
            _CloseDesktop(self._hdesk)
            logger.info(
                "Virtual desktop closed: name={name}", name=self.name,
            )
            self._hdesk = None

        _active_instances.discard(self)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> VirtualDesktop:
        self.create()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        self.destroy()

    # ------------------------------------------------------------------
    # Static cleanup
    # ------------------------------------------------------------------

    @staticmethod
    def cleanup_all() -> None:
        """Destroy all active VirtualDesktop instances.

        Call from the parent process after killing a worker subprocess
        to ensure no orphaned game processes or desktops remain.
        """
        for vd in list(_active_instances):
            try:
                vd.destroy()
            except Exception:
                pass
