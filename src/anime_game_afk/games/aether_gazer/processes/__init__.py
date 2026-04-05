"""User-visible processes (Layer 7) for AetherGazer automation.

Processes are top-level features users enable. They compose Layer 6 tasks.
Processes are NOT composable by each other.
"""
from anime_game_afk.games.aether_gazer.processes.base import (
    Process,
    ProcessContext,
    ProcessResult,
)

__all__ = ["Process", "ProcessContext", "ProcessResult"]
