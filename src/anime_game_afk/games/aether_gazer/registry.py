"""Shared ProcessRegistry builder for AetherGazer.

Single source of truth for which processes are available.
Used by: worker.py, launcher.py CLI mode, TaskManager.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.orchestrator.pipeline import ProcessRegistry
from anime_game_afk.games.aether_gazer.processes.daily_routine import DailyRoutine
from anime_game_afk.games.aether_gazer.processes.push_main_story import PushMainStory


def build_registry() -> ProcessRegistry:
    """Create a ProcessRegistry with all AetherGazer processes registered."""
    registry = ProcessRegistry()
    registry.register("daily_routine", DailyRoutine)
    registry.register("push_main_story", PushMainStory)
    return registry
