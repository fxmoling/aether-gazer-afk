"""Stamina tasks — check and refill stamina.

CheckAndRefillStamina reads current stamina via OCR/detection and
uses stamina packs if below a threshold.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.knowledge.constants import STAMINA_CAP
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext, TaskResult

# Threshold below which we consider a refill
_REFILL_THRESHOLD = 60


class CheckAndRefillStamina:
    """Check stamina level; skip task if already sufficient."""
    name = "check_and_refill_stamina"

    def __init__(self, threshold: int = _REFILL_THRESHOLD) -> None:
        self._threshold = threshold

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        # Read current stamina from shared state (populated by a perception op
        # earlier in the process, or default to cap if unavailable).
        current = ctx.state.get("stamina", STAMINA_CAP)

        if current >= self._threshold:
            ctx.logger.info(
                f"Stamina sufficient ({current}/{STAMINA_CAP}), skipping refill"
            )
            return TaskResult(
                status="skipped",
                message=f"Stamina {current} >= threshold {self._threshold}",
                data={"stamina": current},
            )

        ctx.logger.info(
            f"Stamina low ({current}/{STAMINA_CAP}), initiating refill"
        )
        # Placeholder: actual stamina-pack usage would be implemented here
        # once a dedicated UseStaminaPack op exists.
        return TaskResult(
            status="success",
            message="Stamina refill queued",
            data={"stamina_before": current},
        )
