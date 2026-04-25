"""Headless runner for scheduled (unattended) task execution.

Invoked when the app is launched with ``--scheduled``.
Runs the configured pipeline without any GUI, writes results to
``config/schedule_log.json``, then exits.

Exit codes:
    0 — All tasks succeeded.
    1 — One or more tasks failed (after optional retry).
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

from anime_game_afk.runtime.logger import get_logger
from anime_game_afk.runtime.scheduler import (
    ScheduleConfig,
    append_schedule_log,
    load_schedule_config,
)

logger = get_logger("headless")


def _kill_game() -> None:
    """Kill the AetherGazer game process."""
    try:
        result = subprocess.run(
            ["taskkill", "/F", "/IM", "AetherGazer.exe"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            logger.info("Game process killed")
        else:
            logger.warning("taskkill result: {}", result.stderr.strip())
    except Exception as e:
        logger.warning("Failed to kill game: {}", e)


async def _execute_pipeline(config: ScheduleConfig) -> tuple[bool, str, float]:
    """Run the daily pipeline. Returns (success, message, elapsed_seconds)."""
    from anime_game_afk.config.user_config import UserConfig
    from anime_game_afk.core.device import DeviceAdapter
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

    start_time = time.monotonic()
    user_cfg = UserConfig.load()

    # --- Resolve game exe ---
    game_id = "aether_gazer"
    window_title = user_cfg.window_title(game_id) or "AetherGazer"
    exe_path = user_cfg.game_exe_path(game_id)

    if not exe_path or not Path(exe_path).exists():
        result = find_aether_gazer(search_drives=user_cfg.search_drives())
        if result.get("game_exe"):
            user_cfg.set_game_exe_path(game_id, result["game_exe"])
            if result.get("launcher"):
                user_cfg.set_launcher_path(game_id, result["launcher"])
            user_cfg.save()
            exe_path = result["game_exe"]

    # --- Ensure game is running ---
    game_was_launched = False
    game_running = False
    try:
        r = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq AetherGazer.exe", "/NH"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        game_running = "AetherGazer.exe" in r.stdout
    except Exception:
        pass

    if not game_running:
        if not exe_path:
            return False, "找不到游戏路径", time.monotonic() - start_time
        logger.info("Game not running, launching: {}", exe_path)
        launcher = GameLauncher(
            exe_path=exe_path,
            window_title=window_title,
            process_name=Path(exe_path).name,
        )
        timeout = user_cfg.launch_timeout(game_id)
        if not launcher.ensure_running(timeout=timeout):
            return False, f"启动游戏超时 ({timeout}s)", time.monotonic() - start_time
        game_was_launched = True

    # --- Connect ---
    logger.info("Connecting to game...")
    device_config = AETHER_GAZER_CONFIG.to_device_config(game_exe_path=exe_path or "")
    device = DeviceAdapter(config=device_config)
    try:
        device.connect()
    except Exception as exc:
        return False, f"连接失败: {exc}", time.monotonic() - start_time

    if not device.connected:
        return False, "无法连接到游戏窗口", time.monotonic() - start_time

    res = device.actual_resolution
    logger.info("Connected. Resolution: {}x{}", res.width, res.height)

    # --- Navigate to hub if game was just launched ---
    if game_was_launched:
        try:
            from anime_game_afk.games.aether_gazer.tasks.base import TaskContext
            from anime_game_afk.games.aether_gazer.tasks.startup_tasks import (
                LaunchAndReachHub,
            )
            ctx = TaskContext(device=device, logger=logger)
            launch_task = LaunchAndReachHub(
                max_popup_attempts=user_cfg.popup_dismiss_max_attempts(game_id),
            )
            launch_result = await launch_task.execute(ctx)
            if launch_result.status != "success":
                device.disconnect()
                return False, f"无法到达主界面: {launch_result.message}", time.monotonic() - start_time
        except Exception as exc:
            device.disconnect()
            return False, f"启动导航失败: {exc}", time.monotonic() - start_time

    # --- Execute pipeline ---
    registry = build_registry()

    def context_factory(proc_def: ProcessDef) -> ProcessContext:
        return ProcessContext(
            device=device,
            config=proc_def.config,
            logger=get_logger(f"headless.{proc_def.name}"),
        )

    pipeline = Pipeline(
        registry=registry,
        device=device,
        context_factory=context_factory,
    )

    plan = PlanConfig(
        game="aether_gazer",
        processes=[ProcessDef(
            name=config.pipeline_id,
            config={"game_was_launched": game_was_launched},
        )],
    )

    try:
        result = await pipeline.run(plan)
    except Exception as exc:
        device.disconnect()
        return False, f"Pipeline 异常: {exc}", time.monotonic() - start_time

    device.disconnect()
    elapsed = time.monotonic() - start_time

    if result.failed == 0 and not result.aborted:
        msg = f"完成 {result.succeeded} 个任务 ({elapsed:.0f}s)"
        return True, msg, elapsed
    else:
        msg = f"完成 {result.succeeded}, 失败 {result.failed} ({elapsed:.0f}s)"
        return False, msg, elapsed


class HeadlessRunner:
    """Orchestrates scheduled execution with retry and post-action."""

    def __init__(self, config: ScheduleConfig | None = None) -> None:
        self.config = config or load_schedule_config()

    def run(self) -> int:
        """Execute the scheduled pipeline. Returns exit code (0=success)."""
        logger.info("=== Headless scheduled run starting ===")
        logger.info("Config: time={}, days={}, pipeline={}, retry={}, post_action={}",
                     self.config.time, self.config.days, self.config.pipeline_id,
                     self.config.retry_on_failure, self.config.post_action)

        success, message, elapsed = asyncio.run(
            _execute_pipeline(self.config)
        )

        # Retry once if enabled and first attempt failed
        retried = False
        if not success and self.config.retry_on_failure:
            logger.info("First attempt failed, retrying in 30s...")
            time.sleep(30)
            retried = True
            success, message, elapsed2 = asyncio.run(
                _execute_pipeline(self.config)
            )
            elapsed += elapsed2
            if success:
                message = f"[重试成功] {message}"

        # Log result
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "pipeline": self.config.pipeline_id,
            "result": "success" if success else "failed",
            "message": message,
            "duration_s": round(elapsed, 1),
            "retried": retried,
            "post_action": self.config.post_action,
        }
        try:
            append_schedule_log(log_entry)
        except Exception as e:
            logger.error("Failed to write schedule log: {}", e)

        logger.info("Result: {} | {}", "SUCCESS" if success else "FAILED", message)

        # Post-action
        if self.config.post_action == "kill_game":
            logger.info("Post-action: killing game process")
            _kill_game()

        # Notification
        try:
            from anime_game_afk.core.notifier import notify
            icon = "✅" if success else "❌"
            notify(f"{icon} 定时任务{'完成' if success else '失败'}", message)
        except Exception:
            pass

        logger.info("=== Headless run finished (exit_code={}) ===",
                     0 if success else 1)
        return 0 if success else 1
