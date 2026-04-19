"""Virtual Desktop Proof-of-Concept.

Creates a separate Windows desktop, launches the game there,
connects MaaFw, and runs a click test. The user's cursor on the
default desktop should be completely unaffected.

Usage:
    python scripts/test_virtual_desktop.py
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from anime_game_afk.config.user_config import UserConfig
from anime_game_afk.core.device import DeviceAdapter
from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
from anime_game_afk.runtime.logger import get_logger

logger = get_logger("vdesktop_poc")

# ── Win32 API ──────────────────────────────────────────────

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
advapi32 = ctypes.windll.advapi32

GENERIC_ALL = 0x10000000
DESKTOP_CREATEWINDOW = 0x0002
DESKTOP_WRITEOBJECTS = 0x0080
DESKTOP_SWITCHDESKTOP = 0x0100

STARTF_USESHOWWINDOW = 0x00000001
SW_SHOWNORMAL = 1
CREATE_NEW_PROCESS_GROUP = 0x00000200


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


def create_desktop(name: str) -> ctypes.wintypes.HANDLE:
    """Create a new Windows desktop."""
    access = GENERIC_ALL
    hdesk = user32.CreateDesktopW(name, None, None, 0, access, None)
    if not hdesk:
        raise OSError(f"CreateDesktopW failed: error {ctypes.get_last_error()}")
    logger.info("Created desktop: {}", name)
    return hdesk


def launch_on_desktop(exe_path: str, desktop_name: str) -> tuple[int, int]:
    """Launch a process on the specified desktop.

    Returns (process_handle, pid).
    """
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(STARTUPINFOW)
    si.lpDesktop = desktop_name
    si.dwFlags = STARTF_USESHOWWINDOW
    si.wShowWindow = SW_SHOWNORMAL

    pi = PROCESS_INFORMATION()

    ok = kernel32.CreateProcessW(
        exe_path,       # lpApplicationName
        None,           # lpCommandLine
        None,           # lpProcessAttributes
        None,           # lpThreadAttributes
        False,          # bInheritHandles
        CREATE_NEW_PROCESS_GROUP,  # dwCreationFlags
        None,           # lpEnvironment
        str(Path(exe_path).parent),  # lpCurrentDirectory
        ctypes.byref(si),
        ctypes.byref(pi),
    )
    if not ok:
        raise OSError(f"CreateProcessW failed: error {ctypes.get_last_error()}")

    logger.info("Launched PID {} on desktop {!r}", pi.dwProcessId, desktop_name)
    return pi.hProcess, pi.dwProcessId


def close_desktop(hdesk) -> None:
    """Close a desktop handle."""
    user32.CloseDesktop(hdesk)
    logger.info("Desktop handle closed")


# ── Main PoC ──────────────────────────────────────────────

def main() -> int:
    DESKTOP_NAME = "AFK_GameDesktop"

    # 1. Find game exe
    cfg = UserConfig.load()
    game_exe = cfg.game_exe_path("aether_gazer")
    if not game_exe or not Path(game_exe).exists():
        logger.error("Game exe not found: {}", game_exe)
        return 1

    logger.info("Game exe: {}", game_exe)

    # 2. Create virtual desktop
    hdesk = create_desktop(DESKTOP_NAME)

    try:
        # 3. Launch game on virtual desktop
        hproc, pid = launch_on_desktop(game_exe, DESKTOP_NAME)
        logger.info("Game launched (PID {}), waiting for window...", pid)

        # 4. Wait for game window to appear (poll for up to 60s)
        device_config = AETHER_GAZER_CONFIG.to_device_config()
        device = DeviceAdapter(device_config)

        window_found = False
        for attempt in range(60):
            time.sleep(2)
            try:
                device.connect()
                window_found = True
                logger.info("Connected! Resolution: {}", device.actual_resolution)
                break
            except Exception as e:
                if attempt % 5 == 0:
                    logger.info("Waiting for window... ({}s)", (attempt + 1) * 2)

        if not window_found:
            logger.error("Game window not found after 120s")
            kernel32.TerminateProcess(hproc, 1)
            return 1

        # 5. Test clicks — user's cursor should NOT move
        logger.info("=" * 50)
        logger.info("VIRTUAL DESKTOP TEST — your cursor should NOT move")
        logger.info("=" * 50)

        # Click center a few times
        for i in range(5):
            logger.info("Click {} — center of screen", i + 1)
            device.click(0.5, 0.5)
            time.sleep(1)

        # Click various positions
        positions = [
            (0.1, 0.1, "top-left"),
            (0.9, 0.1, "top-right"),
            (0.5, 0.5, "center"),
            (0.1, 0.9, "bottom-left"),
            (0.9, 0.9, "bottom-right"),
        ]
        for fx, fy, label in positions:
            logger.info("Click {} at ({}, {})", label, fx, fy)
            device.click(fx, fy)
            time.sleep(0.5)

        logger.info("=" * 50)
        logger.info("Test complete! Did your cursor stay still?")
        logger.info("=" * 50)

        # Take a screenshot to verify game is alive
        try:
            img = device.screenshot()
            logger.info("Screenshot captured: {}x{}", img.shape[1], img.shape[0])
        except Exception as e:
            logger.warning("Screenshot failed: {}", e)

        device.disconnect()

        # 6. Optionally keep game running for further testing
        input("\nPress Enter to terminate game and clean up...")

        # Terminate game
        kernel32.TerminateProcess(hproc, 0)
        kernel32.CloseHandle(hproc)
        logger.info("Game terminated")

    finally:
        close_desktop(hdesk)

    return 0


if __name__ == "__main__":
    sys.exit(main())
