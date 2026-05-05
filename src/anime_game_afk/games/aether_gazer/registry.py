"""Shared ProcessRegistry builder for AetherGazer.

Single source of truth for which processes are available.
Used by: worker.py, launcher.py CLI mode, TaskManager.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.orchestrator.pipeline import ProcessRegistry
from anime_game_afk.games.aether_gazer.processes.daily_routine import DailyRoutine
from anime_game_afk.games.aether_gazer.processes.duowei_process import DuoweiProcess
from anime_game_afk.games.aether_gazer.processes.lizhan_process import LizhanProcess


def build_registry() -> ProcessRegistry:
    """Create a ProcessRegistry with all AetherGazer processes registered."""
    registry = ProcessRegistry()
    registry.register("daily_routine", DailyRoutine)
    registry.register("duowei_challenge", DuoweiProcess)
    registry.register("lizhan_loop", LizhanProcess)
    return registry
