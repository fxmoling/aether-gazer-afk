"""多维变量 (Multidimensional Variable) — standalone E2E test runner.

Wraps the DuoweiCombat task / DuoweiProcess for direct command-line testing.

Usage:
    python scripts/duowei_runner.py           # Full run from hub (single cycle)
    python scripts/duowei_runner.py --loop     # Infinite loop (Process mode)
    python scripts/duowei_runner.py --resume  # Resume mid-run (already in arena)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
from anime_game_afk.core.device import DeviceAdapter
from anime_game_afk.games.aether_gazer.tasks.duowei_tasks import DuoweiCombat
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext


class _PrintLogger:
    """Simple print-based logger for standalone testing."""
    def _log(self, level: str, msg: str, **ctx) -> None:
        import time
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] {level:7s} | {msg}")

    def info(self, msg, **ctx): self._log("INFO", msg, **ctx)
    def debug(self, msg, **ctx): self._log("DEBUG", msg, **ctx)
    def warning(self, msg, **ctx): self._log("WARNING", msg, **ctx)
    def error(self, msg, **ctx): self._log("ERROR", msg, **ctx)


async def main():
    parser = argparse.ArgumentParser(description="多维变量 E2E test runner")
    parser.add_argument("--resume", action="store_true",
                        help="Resume mid-run (skip navigation)")
    parser.add_argument("--loop", action="store_true",
                        help="Infinite loop mode (Process)")
    args = parser.parse_args()

    device = DeviceAdapter(AETHER_GAZER_CONFIG.to_device_config())
    device.connect()

    try:
        if args.loop:
            from anime_game_afk.games.aether_gazer.processes.base import (
                ProcessContext,
            )
            from anime_game_afk.games.aether_gazer.processes.duowei_process import (
                DuoweiProcess,
            )

            class _NoopListener:
                def on_task_status(self, *a, **kw): pass

            ctx = ProcessContext(
                device=device, logger=_PrintLogger(), listener=_NoopListener(),
            )
            process = DuoweiProcess()
            result = await process.execute(ctx)
            print(f"\nResult: {result.status} — {result.message}")
        else:
            ctx = TaskContext(device=device, logger=_PrintLogger())
            task = DuoweiCombat()

            if args.resume:
                print("Resume mode: skipping navigation")
                from anime_game_afk.games.aether_gazer.ops.primitives import SleepOp
                await task._handle_treasure(ctx)
                await SleepOp(2.0).run(ctx)
                if not await task._walk_to_portal(ctx):
                    print("Portal not found, exiting")
                    await task._exit_and_settle(ctx)
                    return
                await SleepOp(5.0).run(ctx)
                await task._dismiss_dialogs(ctx)
                await task._handle_treasure(ctx)
                result = await task._fight_battle(ctx)
                print(f"Battle result: {result}")
                await SleepOp(2.0).run(ctx)
                await task._handle_reward(ctx)
                await task._exit_and_settle(ctx)
            else:
                result = await task.execute(ctx)
                print(f"\nResult: {result.status} — {result.message}")
    finally:
        device.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
