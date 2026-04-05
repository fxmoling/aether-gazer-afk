"""Composable tasks (Layer 6) for AetherGazer automation.

Tasks compose atomic ops (Layer 5) with control flow.
Each task does one logical thing: clear a stage, buy items, collect mail.

Note: using tasks/ to avoid conflict with legacy tasks/ during migration.
"""
from anime_game_afk.games.aether_gazer.tasks.base import (
    Task,
    TaskContext,
    TaskResult,
)

__all__ = ["Task", "TaskContext", "TaskResult"]
