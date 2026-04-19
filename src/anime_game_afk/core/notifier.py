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
    """Show a balloon tip using the foreground window as anchor."""
    try:
        hwnd = _user32.GetDesktopWindow()
        hicon = _user32.LoadIconW(None, ctypes.c_void_p(IDI_APPLICATION))

        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = hwnd
        nid.uID = 7749  # unique ID to avoid conflicts
        nid.uFlags = NIF_ICON | NIF_TIP | NIF_INFO
        nid.uCallbackMessage = WM_USER + 1
        nid.hIcon = hicon
        nid.szTip = "AetherGazer AFK"[:_MAX_TIP - 1]
        nid.szInfo = message[:_MAX_INFO - 1]
        nid.szInfoTitle = title[:_MAX_INFOTITLE - 1]
        nid.dwInfoFlags = NIIF_INFO
        nid.uVersion_or_uTimeout = 5000

        _Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))

        import time
        time.sleep(6)

        _Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))

    except Exception:
        pass
