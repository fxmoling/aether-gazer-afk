"""Main entry point for the GUI application.

Creates the pywebview window and starts the event loop.

Usage:
    python -m anime_game_afk.ui.app
"""
from __future__ import annotations

import sys
from pathlib import Path

import webview  # type: ignore[import-untyped]

from anime_game_afk.ui.api import Api
from anime_game_afk.ui.bridge import LogForwarder
from anime_game_afk.ui.task_manager import TaskManager

# Resolve path to web/ directory (sibling to this file)
_WEB_DIR = Path(__file__).parent / "web"


_EDGE_DOWNLOAD = "https://www.microsoft.com/edge"


def _is_webview2_installed() -> bool:
    """Check if Microsoft Edge WebView2 Runtime is installed."""
    import winreg
    for key_path in (
        r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
        r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
    ):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                ver, _ = winreg.QueryValueEx(key, "pv")
                if ver and ver != "0.0.0.0":
                    return True
        except OSError:
            continue
    return False


def _ensure_webview2(log) -> None:
    """Prompt user to install Edge browser if WebView2 is missing, then exit."""
    if sys.platform != "win32":
        return
    try:
        if _is_webview2_installed():
            return
    except Exception:
        return

    log.warning("WebView2 Runtime not detected")

    import webbrowser
    title = "AetherGazer AFK - 需要安装 Edge 浏览器"
    message = (
        "本程序需要 Microsoft Edge 浏览器才能正常显示界面。\n\n"
        "您的系统似乎未安装 Edge（Windows 11 自带，Windows 10 可能需要手动安装）。\n\n"
        "点击「是」打开 Edge 下载页面，安装后重新启动程序即可。"
    )
    user_said_yes = False
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        user_said_yes = messagebox.askyesno(title, message)
        root.destroy()
    except Exception:
        try:
            import ctypes
            result = ctypes.windll.user32.MessageBoxW(0, message, title, 4 | 48)
            user_said_yes = (result == 6)
        except Exception:
            pass

    if user_said_yes:
        webbrowser.open(_EDGE_DOWNLOAD)

    sys.exit(1)


def main() -> None:
    """Launch the GUI application."""
    # 0. Set up file logging for frozen builds (no console)
    from loguru import logger as _log
    if getattr(sys, "frozen", False):
        app_dir = Path(sys.executable).resolve().parent
        log_file = app_dir / "logs" / "gui.log"
        log_file.parent.mkdir(exist_ok=True)
        _log.add(str(log_file), rotation="5 MB", level="DEBUG",
                 format="{time:HH:mm:ss} | {level:<7} | {message}",
                 enqueue=True)  # thread-safe queued writes

    _log.info("=" * 60)
    _log.info("AetherGazer AFK GUI starting")
    _log.info("Python: {} | Frozen: {} | Exe: {}",
              sys.version_info[:3], getattr(sys, "frozen", False), sys.executable)
    if getattr(sys, "frozen", False):
        app_dir = Path(sys.executable).resolve().parent
        _log.info("App dir: {}", app_dir)
    _log.info("Web dir: {} (exists={})", _WEB_DIR, _WEB_DIR.exists())
    _log.info("=" * 60)

    # 1. Set up log forwarding
    log_forwarder = LogForwarder(maxlen=500)
    log_forwarder.install()

    # 2. Create task manager
    task_manager = TaskManager()

    # 3. Create API
    api = Api(task_manager=task_manager, log_forwarder=log_forwarder)

    # 4. Check WebView2 availability — required for Vue 3 rendering
    _ensure_webview2(_log)

    # 5. Create pywebview window
    window = webview.create_window(
        title="AetherGazer AFK",
        url=str(_WEB_DIR / "index.html"),
        js_api=api,
        width=900,
        height=600,
        min_size=(750, 500),
    )

    # 6. Bind window for evaluate_js push
    task_manager.bind_window(window)
    log_forwarder.bind_window(window)

    # 7. Start pywebview (blocks until window closes)
    #    In scheduled mode, auto-start the daily pipeline after window loads
    import builtins
    is_scheduled = getattr(builtins, '_SCHEDULED_MODE', False)

    def _on_loaded():
        """Called when the webview window finishes loading."""
        if is_scheduled:
            import threading
            import time
            def _auto_start():
                time.sleep(2)  # Wait for frontend JS to initialize
                _log.info("[scheduled] Auto-starting pipeline: daily_routine")
                result = task_manager.start("daily_routine")
                _log.info("[scheduled] start result: {}", result)
            threading.Thread(target=_auto_start, daemon=True).start()

    window.events.loaded += _on_loaded

    webview.start(debug="--debug" in sys.argv)

    # 7. Cleanup
    log_forwarder.uninstall()
    task_manager.disconnect()


if __name__ == "__main__":
    main()
