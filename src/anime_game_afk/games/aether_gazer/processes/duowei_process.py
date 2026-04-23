"""多维变量 (Multidimensional Variable) process.

Standalone process (NOT part of daily routine) that repeats 多维变量
dungeon runs indefinitely until the user stops the process.

Each cycle: navigate → setup (with 赏金猎人 beacon) → 1-1 treasure →
portal to 1-2 → fight → reward → ESC+H exit → repeat.
"""
from __future__ import annotations

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

        # Infinite loop — each cycle handles its own navigation
        cycle = 0
        while True:
            cycle += 1
            ctx.logger.info(
                f"=== DuoweiProcess: cycle {cycle} "
                f"(done={completed}, fail={failed}) ==="
            )
            ctx.notify_task(
                "duowei_combat",
                "running",
                f"Cycle {cycle}",
            )

            result = await task.execute(ctx)

            if result.status == "success":
                completed += 1
                consecutive_failures = 0
                ctx.notify_task(
                    "duowei_combat",
                    "success",
                    f"Cycle {cycle}: {result.message}",
                )
                ctx.logger.info(
                    f"[duowei-process] Cycle {cycle} success: {result.message}"
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
                    f"[duowei-process] Cycle {cycle} failed: {result.message}"
                )

                if consecutive_failures >= self._MAX_CONSECUTIVE_FAILURES:
                    ctx.logger.error(
                        f"[duowei-process] {self._MAX_CONSECUTIVE_FAILURES} "
                        "consecutive failures, stopping"
                    )
                    break

        ctx.logger.info(
            f"=== DuoweiProcess: stopped "
            f"(completed={completed}, failed={failed}) ==="
        )
        return ProcessResult(
            status="success" if completed > 0 else "failed",
            message=f"Completed {completed} cycles, {failed} failures",
            data={"completed": completed, "failed": failed},
        )
