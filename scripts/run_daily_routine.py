"""run_daily_routine.py — Full daily automation: launch → connect → tasks.

Complete flow:
1. Check if game process is running
   - If running: attach (connect) to the existing window
   - If not running: launch the game exe, wait for window
2. Connect DeviceAdapter to the game window
3. Check if already at hub → skip startup popups if so
4. Otherwise: skip login/loading/popups until hub is reached
5. Run all 10 daily tasks
6. Done

Usage:
    python scripts/run_daily_routine.py
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

# Add project src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from loguru import logger

from anime_game_afk.core.device import DeviceAdapter
from anime_game_afk.core.errors import WindowNotFoundError
from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
from anime_game_afk.games.aether_gazer.processes.base import ProcessContext
from anime_game_afk.games.aether_gazer.processes.daily_routine import DailyRoutine
from anime_game_afk.games.aether_gazer.tasks.startup_tasks import (
    SkipStartupPopups,
    ensure_game_running,
)
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext
from anime_game_afk.games.aether_gazer.checks.page import AtHubCheck
from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.runtime.run_log import RunLog


# Game exe path from user config
_EXE_PATH = r"E:\shenkongzhiyan\AetherGazerLauncher\AetherGazer\AetherGazer.exe"
_WINDOW_TITLE = "AetherGazer"


def _check_hub(device: DeviceAdapter) -> bool:
    """Quick check if game is already at hub page."""
    try:
        ctx = OpContext(device=device)
        result = asyncio.get_event_loop().run_until_complete(
            AtHubCheck().evaluate(ctx)
        )
        return result.passed
    except Exception:
        return False


async def run(device: DeviceAdapter, run_log: RunLog) -> None:
    """Execute the full daily automation flow."""
    t_start = time.perf_counter()

    # Build context
    ctx = ProcessContext(device=device)
    ctx.run_log = run_log  # type: ignore[attr-defined]
    ctx.logger = logger

    run_log.snap(device, "initial_state")

    # ── Phase 2: Check if already at hub ──
    if _check_hub(device):
        logger.info("✓ Already at hub — skipping startup popup dismissal")
    else:
        logger.info("Not at hub — running startup popup dismissal...")
        task_ctx = TaskContext(device=device, logger=logger)
        task_ctx.run_log = run_log  # type: ignore[attr-defined]
        skip = SkipStartupPopups(max_attempts=60)
        result = await skip.execute(task_ctx)
        if result.status != "success":
            logger.error(f"Startup failed: {result.message}")
            logger.error("Cannot reach hub, aborting.")
            return

    run_log.snap(device, "after_startup")

    # ── Phase 3: Run daily tasks ──
    logger.info("=" * 60)
    logger.info("Starting DailyRoutine — 10 tasks")
    logger.info("=" * 60)

    routine = DailyRoutine()
    result = await routine.execute(ctx)

    elapsed = time.perf_counter() - t_start

    logger.info("=" * 60)
    logger.info(f"DailyRoutine finished: status={result.status}")
    if result.data:
        completed = result.data.get("completed", [])
        failed = result.data.get("failed", [])
        logger.info(f"  Completed ({len(completed)}): {completed}")
        logger.info(f"  Failed ({len(failed)}): {failed}")
    logger.info(f"  Total time: {elapsed:.1f}s")
    logger.info("=" * 60)

    run_log.snap(device, "final_state")


def main():
    config = AETHER_GAZER_CONFIG.to_device_config()

    device = DeviceAdapter(config)
    run_log = RunLog()
    logger.info(f"[RunLog] Screenshots at: {run_log.screenshots_dir}")

    # ── Phase 1: Ensure game is running ──
    try:
        device.connect()
        logger.info("✓ Game window found — attached to existing process")
    except WindowNotFoundError:
        logger.info("Game window not found — launching game...")
        if not ensure_game_running(
            exe_path=_EXE_PATH,
            window_title=_WINDOW_TITLE,
            timeout=120,
        ):
            logger.error("Failed to launch game. Aborting.")
            return

        # Now connect to the newly launched game
        logger.info("Game launched — connecting to window...")
        try:
            device.connect()
            logger.info("✓ Connected to game window after launch")
        except WindowNotFoundError:
            logger.error("Window still not found after launch. Aborting.")
            return

    # ── Phase 2 + 3: Startup + Daily tasks ──
    try:
        asyncio.run(run(device, run_log))
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        try:
            run_log.snap(device, "error_state")
        except Exception:
            pass
    finally:
        run_log.close()
        device.disconnect()
        logger.info("Done.")


if __name__ == "__main__":
    main()
