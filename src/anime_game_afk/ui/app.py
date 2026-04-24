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


def main() -> None:
    """Launch the GUI application."""
    # 0. Set up file logging for frozen builds (no console)
    from loguru import logger as _log
    if getattr(sys, "frozen", False):
        app_dir = Path(sys.executable).resolve().parent
        log_file = app_dir / "logs" / "gui.log"
        log_file.parent.mkdir(exist_ok=True)
        _log.add(str(log_file), rotation="5 MB", level="DEBUG",
                 format="{time:HH:mm:ss} | {level:<7} | {message}")

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

    # 4. Create pywebview window
    window = webview.create_window(
        title="AetherGazer AFK",
        url=str(_WEB_DIR / "index.html"),
        js_api=api,
        width=900,
        height=600,
        min_size=(750, 500),
    )

    # 5. Bind window for evaluate_js push
    task_manager.bind_window(window)
    log_forwarder.bind_window(window)

    # 6. Start pywebview (blocks until window closes)
    webview.start(debug="--debug" in sys.argv)

    # 7. Cleanup
    log_forwarder.uninstall()
    task_manager.disconnect()


if __name__ == "__main__":
    main()
