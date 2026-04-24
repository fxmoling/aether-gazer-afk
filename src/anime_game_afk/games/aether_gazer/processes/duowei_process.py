"""多维变量 (Multidimensional Variable) process.

Standalone process (NOT part of daily routine) that repeats 多维变量
dungeon runs indefinitely until the user stops the process.

Each cycle: navigate → setup (with 赏金猎人 beacon) → 1-1 treasure →
portal to 1-2 → fight → reward → ESC+H exit → repeat.
"""
from __future__ import annotations

import time

from anime_game_afk.games.aether_gazer.processes.base import (
    ProcessContext,
    ProcessResult,
)
from anime_game_afk.games.aether_gazer.tasks.duowei_tasks import DuoweiCombat


class DuoweiProcess:
    """Repeatedly run 多维变量 challenges for score accumulation.

    Each cycle runs DuoweiCombat (navigate → setup → fight → exit).
    Loops indefinitely until user stops or 3 consecutive failures.
    """

    name = "多维变量挑战"
    description = "自动重复挑战多维变量，累积积分（无限循环直到手动停止）"

    _MAX_CONSECUTIVE_FAILURES = 3

    async def execute(self, ctx: ProcessContext) -> ProcessResult:
        task = DuoweiCombat()
        completed = 0
        failed = 0
        consecutive_failures = 0

        ctx.logger.info("=== DuoweiProcess: starting ===")

        process_t0 = time.monotonic()
        # Infinite loop — each cycle handles its own navigation
        cycle = 0
        stop_reason = "user_stop"
        while True:
            cycle += 1
            ctx.logger.info(
                f"=== DuoweiProcess: cycle {cycle} "
                f"(done={completed}, fail={failed}, "
                f"consec_fail={consecutive_failures}) ==="
            )
            ctx.notify_task(
                "duowei_combat",
                "running",
                f"Cycle {cycle}",
            )

            cycle_t0 = time.monotonic()
            result = await task.execute(ctx)
            cycle_elapsed = time.monotonic() - cycle_t0

            if result.status == "success":
                completed += 1
                consecutive_failures = 0
                ctx.notify_task(
                    "duowei_combat",
                    "success",
                    f"Cycle {cycle}: {result.message}",
                )
                ctx.logger.info(
                    f"[duowei-process] Cycle {cycle} success: "
                    f"{result.message} ({cycle_elapsed:.1f}s)"
                )
            else:
                failed += 1
                consecutive_failures += 1
                ctx.notify_task(
                    "duowei_combat",
                    "failed",
                    f"Cycle {cycle}: {result.message}",
                )
                ctx.logger.warning(
                    f"[duowei-process] Cycle {cycle} failed: "
                    f"{result.message} ({cycle_elapsed:.1f}s) "
                    f"[consecutive_failures={consecutive_failures}/"
                    f"{self._MAX_CONSECUTIVE_FAILURES}]"
                )

                if consecutive_failures >= self._MAX_CONSECUTIVE_FAILURES:
                    stop_reason = (
                        f"{self._MAX_CONSECUTIVE_FAILURES} consecutive failures"
                    )
                    ctx.logger.error(
                        f"[duowei-process] Stopping: {stop_reason}"
                    )
                    break

        total_elapsed = time.monotonic() - process_t0
        ctx.logger.info(
            f"=== DuoweiProcess: stopped — reason={stop_reason} "
            f"(completed={completed}, failed={failed}) "
            f"total_time={total_elapsed:.1f}s ==="
        )
        return ProcessResult(
            status="success" if completed > 0 else "failed",
            message=f"Completed {completed} cycles, {failed} failures",
            data={"completed": completed, "failed": failed},
        )
