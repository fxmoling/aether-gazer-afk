"""历战轮回 (Battle Recurrence) process.

Standalone process (NOT part of daily routine) that repeats 历战轮回
indefinitely until the user stops the process.

Each cycle: verify page → start battle → J-spam → detect node-10 → restart.
"""
from __future__ import annotations

import time

from anime_game_afk.games.aether_gazer.processes.base import (
    ProcessContext,
    ProcessResult,
)
from anime_game_afk.games.aether_gazer.tasks.lizhan_tasks import LizhanCombat


class LizhanProcess:
    """Repeatedly run 历战轮回 for proficiency/affection grinding.

    Each cycle runs LizhanCombat (verify → fight → restart).
    Loops indefinitely until user stops or 3 consecutive failures.
    """

    name = "历战轮回"
    description = "自动无限刷历战轮回，用于刷熟练度或好感度（需手动导航到作战准备页面）"

    _MAX_CONSECUTIVE_FAILURES = 3

    async def execute(self, ctx: ProcessContext) -> ProcessResult:
        task = LizhanCombat()
        completed = 0
        failed = 0
        consecutive_failures = 0

        ctx.logger.info("=== LizhanProcess: starting ===")

        process_t0 = time.monotonic()
        cycle = 0
        stop_reason = "user_stop"
        while True:
            cycle += 1
            ctx.logger.info(
                f"=== LizhanProcess: cycle {cycle} "
                f"(done={completed}, fail={failed}, "
                f"consec_fail={consecutive_failures}) ==="
            )
            ctx.notify_task(
                "lizhan_combat",
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
                    "lizhan_combat",
                    "success",
                    f"Cycle {cycle}: {result.message}",
                )
                ctx.logger.info(
                    f"[lizhan-process] Cycle {cycle} success: "
                    f"{result.message} ({cycle_elapsed:.1f}s)"
                )
            else:
                failed += 1
                consecutive_failures += 1
                ctx.notify_task(
                    "lizhan_combat",
                    "failed",
                    f"Cycle {cycle}: {result.message}",
                )
                ctx.logger.warning(
                    f"[lizhan-process] Cycle {cycle} failed: "
                    f"{result.message} ({cycle_elapsed:.1f}s) "
                    f"[consecutive_failures={consecutive_failures}/"
                    f"{self._MAX_CONSECUTIVE_FAILURES}]"
                )

                if consecutive_failures >= self._MAX_CONSECUTIVE_FAILURES:
                    stop_reason = (
                        f"{self._MAX_CONSECUTIVE_FAILURES} consecutive failures"
                    )
                    ctx.logger.error(
                        f"[lizhan-process] Stopping: {stop_reason}"
                    )
                    break

        total_elapsed = time.monotonic() - process_t0
        ctx.logger.info(
            f"=== LizhanProcess: stopped — reason={stop_reason} "
            f"(completed={completed}, failed={failed}) "
            f"total_time={total_elapsed:.1f}s ==="
        )
        return ProcessResult(
            status="success" if completed > 0 else "failed",
            message=f"Completed {completed} cycles, {failed} failures",
            data={"completed": completed, "failed": failed},
        )
