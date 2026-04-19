"""Windows toast notifications via ctypes Shell_NotifyIconW.

Zero external dependencies — uses the Win32 Shell_NotifyIcon API directly.
Balloon tips are drawn by Explorer, so they never steal focus or break
fullscreen apps.

Usage::

    from anime_game_afk.core.notifier import notify
    notify("任务完成", "所有日常任务已执行完毕")
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import threading

# ---------------------------------------------------------------------------
# Win32 constants
# ---------------------------------------------------------------------------

NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002

NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
NIF_INFO = 0x00000010

NIIF_INFO = 0x00000001

WM_USER = 0x0400
WM_DESTROY = 0x0002

WS_OVERLAPPED = 0x00000000

IDI_APPLICATION = 32512

# ---------------------------------------------------------------------------
# NOTIFYICONDATAW struct
# ---------------------------------------------------------------------------

_MAX_TIP = 128
_MAX_INFO = 256
_MAX_INFOTITLE = 64


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.DWORD),
        ("hWnd", ctypes.wintypes.HWND),
        ("uID", ctypes.wintypes.UINT),
        ("uFlags", ctypes.wintypes.UINT),
        ("uCallbackMessage", ctypes.wintypes.UINT),
        ("hIcon", ctypes.wintypes.HICON),
        ("szTip", ctypes.wintypes.WCHAR * _MAX_TIP),
        ("dwState", ctypes.wintypes.DWORD),
        ("dwStateMask", ctypes.wintypes.DWORD),
        ("szInfo", ctypes.wintypes.WCHAR * _MAX_INFO),
        ("uVersion_or_uTimeout", ctypes.wintypes.UINT),
        ("szInfoTitle", ctypes.wintypes.WCHAR * _MAX_INFOTITLE),
        ("dwInfoFlags", ctypes.wintypes.DWORD),
    ]


# ---------------------------------------------------------------------------
# Win32 API bindings
# ---------------------------------------------------------------------------

_shell32 = ctypes.windll.shell32
_user32 = ctypes.windll.user32

_Shell_NotifyIconW = _shell32.Shell_NotifyIconW
_Shell_NotifyIconW.restype = ctypes.wintypes.BOOL
_Shell_NotifyIconW.argtypes = [ctypes.wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def notify(title: str, message: str) -> None:
    """Show a Windows balloon-tip notification.

    Non-blocking — spawns a short-lived background thread.
    Falls back silently on any error (notification is non-critical).

    Args:
        title: Notification title (max 63 chars).
        message: Notification body (max 255 chars).
    """
    t = threading.Thread(target=_show_balloon, args=(title, message), daemon=True)
    t.start()


def _show_balloon(title: str, message: str) -> None:
    """Create a hidden window, show a balloon tip, then clean up."""
    try:
        # Register a minimal window class
        wc_name = "AFK_Notifier"
        wndclass = ctypes.wintypes.WNDCLASSW()  # type: ignore[attr-defined]
        wndclass.lpfnWndProc = ctypes.cast(
            _user32.DefWindowProcW, ctypes.c_void_p
        )
        wndclass.lpszClassName = wc_name
        wndclass.hInstance = _user32.GetModuleHandleW(None)

        # RegisterClass may fail if already registered — that's fine
        _user32.RegisterClassW(ctypes.byref(wndclass))

        hwnd = _user32.CreateWindowExW(
            0,              # dwExStyle
            wc_name,        # lpClassName
            "AFK Notify",   # lpWindowName
            WS_OVERLAPPED,  # dwStyle
            0, 0, 0, 0,    # x, y, width, height
            None,           # hWndParent
            None,           # hMenu
            wndclass.hInstance,
            None,           # lpParam
        )
        if not hwnd:
            return

        # Load default app icon
        hicon = _user32.LoadIconW(None, ctypes.c_void_p(IDI_APPLICATION))

        # Build NOTIFYICONDATAW
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = hwnd
        nid.uID = 1
        nid.uFlags = NIF_ICON | NIF_TIP | NIF_INFO
        nid.uCallbackMessage = WM_USER + 1
        nid.hIcon = hicon
        nid.szTip = "AetherGazer AFK"[:_MAX_TIP - 1]
        nid.szInfo = message[:_MAX_INFO - 1]
        nid.szInfoTitle = title[:_MAX_INFOTITLE - 1]
        nid.dwInfoFlags = NIIF_INFO
        nid.uVersion_or_uTimeout = 5000  # 5 seconds

        # Add the icon + balloon
        _Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))

        # Keep alive briefly so the balloon is visible, then clean up
        import time
        time.sleep(6)

        _Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
        _user32.DestroyWindow(hwnd)

    except Exception:
        # Notification is non-critical — never crash
        pass
