"""Layer 8: Orchestrator / Pipeline.

Executes a user-configured selection of processes.
Loads YAML plans, runs processes sequentially, handles infrastructure recovery.

Dependency rule: imports from Layers 0-7 only.
"""

from anime_game_afk.games.aether_gazer.orchestrator.pipeline import (
    Pipeline,
    ProcessRegistry,
)
from anime_game_afk.games.aether_gazer.orchestrator.types import (
    PipelineResult,
    PlanConfig,
    ProcessDef,
    load_plan,
)

__all__ = [
    "Pipeline",
    "PipelineResult",
    "PlanConfig",
    "ProcessDef",
    "ProcessRegistry",
    "load_plan",
]
