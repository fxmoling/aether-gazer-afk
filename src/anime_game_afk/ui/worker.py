"""Subprocess worker entry point for pipeline execution.

Runs as a child process so the parent GUI can ``process.kill()`` it for
reliable stop.  Communicates with the parent via a JSON-line protocol on
stdout; all log output goes to stderr only.

Usage::

    python -m anime_game_afk.ui.worker --pipeline daily_routine \\
        --tasks mail,intel_shards,stamina_packs
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import traceback
from typing import Any


# ---------------------------------------------------------------------------
# JSON-line helpers
# ---------------------------------------------------------------------------

def _emit(obj: dict[str, Any]) -> None:
    """Write a single JSON object as one line to stdout and flush."""
    print(json.dumps(obj, ensure_ascii=False), flush=True)


# ---------------------------------------------------------------------------
# JsonLineListener — translates PipelineListener events to JSON lines
# ---------------------------------------------------------------------------

class JsonLineListener:
    """Implements PipelineListener by emitting JSON lines to stdout."""

    def on_task_status(
        self, task_id: str, status: str, message: str = "",
    ) -> None:
        _emit({"type": "task_status", "id": task_id, "status": status,
               "message": message})

    def on_process_status(
        self, name: str, status: str, message: str = "",
    ) -> None:
        _emit({"type": "process_status", "name": name, "status": status,
               "message": message})

    def on_connected(self, resolution: str) -> None:
        _emit({"type": "connected", "resolution": resolution})

    def on_done(
        self, completed: int, failed: int, elapsed_s: float,
    ) -> None:
        _emit({"type": "done", "completed": completed, "failed": failed,
               "elapsed_s": elapsed_s})


# ---------------------------------------------------------------------------
# Notification helper
# ---------------------------------------------------------------------------

def _try_notify(title: str, message: str) -> None:
    """Send a toast notification, swallowing any errors."""
    try:
        from anime_game_afk.core.notifier import notify
        notify(title, message)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Async main loop
# ---------------------------------------------------------------------------

async def _run(pipeline_id: str, enabled_ids: set[str]) -> int:
    """Execute the requested pipeline and stream status to stdout.

    Returns:
        Exit code — 0 for success, 1 for fatal error.
    """
    # Late imports so the module can be parsed even if deps aren't installed.
    from anime_game_afk.config.user_config import UserConfig
    from anime_game_afk.core.device import DeviceAdapter
    from anime_game_afk.core.errors import WindowNotFoundError
    from anime_game_afk.core.game_finder import find_aether_gazer
    from anime_game_afk.core.game_launcher import GameLauncher
    from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
    from anime_game_afk.games.aether_gazer.orchestrator.pipeline import Pipeline
    from anime_game_afk.games.aether_gazer.orchestrator.types import (
        PlanConfig,
        ProcessDef,
    )
    from anime_game_afk.games.aether_gazer.processes.base import ProcessContext
    from anime_game_afk.games.aether_gazer.registry import build_registry
    from anime_game_afk.runtime.logger import get_logger

    listener = JsonLineListener()
    logger = get_logger("worker")
    logger.info("Worker started: pipeline={}, tasks={}", pipeline_id, enabled_ids)

    import platform
    import time as _time
    _worker_start = _time.monotonic()
    logger.info(
        "Environment: Python {} | {} | frozen={}",
        sys.version_info[:3], platform.platform(),
        getattr(sys, "frozen", False),
    )

    user_cfg = UserConfig.load()
    notify_on_complete = user_cfg.notify_on_complete()

    # ---- Resolve game exe path (needed for both modes) --------------------
    game_id = "aether_gazer"
    window_title = user_cfg.window_title(game_id) or "AetherGazer"
    exe_path = user_cfg.game_exe_path(game_id)

    if not exe_path or not __import__("pathlib").Path(exe_path).exists():
        result = find_aether_gazer(search_drives=user_cfg.search_drives())
        if result["game_exe"]:
            user_cfg.set_game_exe_path(game_id, result["game_exe"])
            if result.get("launcher"):
                user_cfg.set_launcher_path(game_id, result["launcher"])
            user_cfg.save()
            exe_path = result["game_exe"]

    # ---- Ensure game is running ---------------------------------------------
    game_process_running = False
    _emit({"type": "status", "msg": "正在查找游戏窗口..."})
    try:
        import subprocess as _sp
        r = _sp.run(["tasklist", "/FI", "IMAGENAME eq AetherGazer.exe", "/NH"],
                     capture_output=True, text=True, timeout=5)
        game_process_running = "AetherGazer.exe" in r.stdout
    except Exception:
        pass

    if not game_process_running:
        _emit({"type": "status", "msg": "游戏未运行，正在启动..."})
        if not exe_path:
            _emit({"type": "error", "msg": "找不到游戏，请在设置中指定游戏路径"})
            return 1

        launcher = GameLauncher(
            exe_path=exe_path,
            window_title=window_title,
            process_name=__import__("pathlib").Path(exe_path).name,
        )
        timeout = user_cfg.launch_timeout(game_id)
        if not launcher.ensure_running(timeout=timeout):
            _emit({"type": "error", "msg": f"启动游戏超时 ({timeout}s)"})
            return 1

    # Connect to game window
    _emit({"type": "status", "msg": "正在连接游戏..."})

    try:
        device_config = AETHER_GAZER_CONFIG.to_device_config(
            game_exe_path=exe_path or "",
        )
        device = DeviceAdapter(config=device_config)
        device.connect()
    except Exception as exc:
        _emit({"type": "error", "msg": f"连接失败: {exc}"})
        return 1

    if not device.connected:
        _emit({"type": "error", "msg": "无法连接到游戏窗口"})
        return 1

    # Best-effort cleanup hooks: any "soft" interpreter shutdown (atexit,
    # SIGTERM, SIGINT) tries to release stuck keys before exit.  This does
    # NOT cover ``proc.kill()`` (TerminateProcess) — the parent runs its
    # own recovery in that case via ``_auto_recover_input``.
    import atexit
    import signal

    def _cleanup_input() -> None:
        try:
            if device.connected:
                device.release_all_held_keys()
        except Exception:
            pass

    atexit.register(_cleanup_input)
    try:
        signal.signal(signal.SIGTERM, lambda *_: (_cleanup_input(), sys.exit(1)))
        signal.signal(signal.SIGINT, lambda *_: (_cleanup_input(), sys.exit(1)))
    except (ValueError, OSError):
        # signal handlers can't be installed on non-main threads or
        # certain platforms; atexit alone still gives best-effort coverage.
        pass

    res = device.actual_resolution
    listener.on_connected(f"{res.width}x{res.height}")

    # ---- Build pipeline ---------------------------------------------------
    registry = build_registry()

    def context_factory(proc_def: ProcessDef) -> ProcessContext:
        return ProcessContext(
            device=device,
            config=proc_def.config,
            listener=listener,
            logger=get_logger(f"worker.{proc_def.name}"),
        )

    pipeline = Pipeline(
        registry=registry,
        device=device,
        context_factory=context_factory,
    )

    # ---- Build plan from CLI args -----------------------------------------
    plan = PlanConfig(
        game="aether_gazer",
        processes=[ProcessDef(
            name=pipeline_id,
            config={
                "enabled_tasks": sorted(enabled_ids),
                "game_was_launched": not game_process_running,
            },
        )],
    )

    # ---- Execute ----------------------------------------------------------
    try:
        result = await pipeline.run(plan)
    except Exception as exc:
        _emit({"type": "error", "msg": f"Pipeline error: {exc}"})
        if notify_on_complete:
            _try_notify("❌ 任务失败", f"Pipeline error: {exc}")
        device.disconnect()
        return 1

    listener.on_done(result.succeeded, result.failed, result.elapsed_s)
    device.disconnect()

    if notify_on_complete:
        if result.failed == 0 and not result.aborted:
            _try_notify(
                "✅ 任务完成",
                f"已完成 {result.succeeded} 个任务 ({result.elapsed_s:.0f}s)",
            )
        else:
            _try_notify(
                "⚠️ 任务结束",
                f"完成 {result.succeeded}，失败 {result.failed}",
            )

    _elapsed = _time.monotonic() - _worker_start
    logger.info("Worker finished: succeeded={}, failed={}, elapsed={:.1f}s",
                result.succeeded, result.failed, _elapsed)

    return 0 if not result.aborted and result.failed == 0 else 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Parse CLI arguments, configure logging, and run the async loop."""
    # Ensure MaaFw DLLs are findable in frozen mode (supplement the rthook)
    if getattr(sys, "frozen", False):
        import os
        from pathlib import Path
        maa_bin = Path(sys._MEIPASS) / "maa" / "bin"  # type: ignore[attr-defined]
        if maa_bin.exists():
            maa_bin_str = str(maa_bin)
            internal_str = str(Path(sys._MEIPASS))  # type: ignore[attr-defined]
            os.environ["MAAFW_BINARY_PATH"] = maa_bin_str
            os.environ["PATH"] = (
                maa_bin_str + os.pathsep + internal_str + os.pathsep
                + os.environ.get("PATH", "")
            )
            try:
                os.add_dll_directory(maa_bin_str)
                os.add_dll_directory(internal_str)
            except (OSError, AttributeError):
                pass
            # Preload MaaFw DLLs in dependency order so ctypes finds them
            import ctypes
            for dll_name in ("MaaUtils.dll", "MaaFramework.dll",
                             "MaaToolkit.dll", "MaaWin32ControlUnit.dll"):
                dll_path = maa_bin / dll_name
                if dll_path.exists():
                    try:
                        ctypes.WinDLL(str(dll_path))
                    except OSError:
                        pass

    # Line-buffered stdout for real-time JSON streaming
    if sys.stdout is not None:
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]

    # Redirect loguru to stderr only (stdout is the JSON protocol channel)
    from loguru import logger

    logger.remove()
    logger.add(
        sys.stderr,
        format="{time:HH:mm:ss} | {level:<7} | {message}",
        level="DEBUG",
    )

    parser = argparse.ArgumentParser(
        description="Subprocess worker for pipeline execution",
    )
    parser.add_argument(
        "--pipeline",
        required=True,
        help="Pipeline ID to execute (e.g. daily_routine)",
    )
    parser.add_argument(
        "--tasks",
        required=True,
        help="Comma-separated list of enabled task IDs",
    )
    args = parser.parse_args()

    enabled_ids = {t.strip() for t in args.tasks.split(",") if t.strip()}

    try:
        exit_code = asyncio.run(_run(args.pipeline, enabled_ids))
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        _emit({"type": "error", "msg": f"Fatal: {exc}"})
        sys.exit(1)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
