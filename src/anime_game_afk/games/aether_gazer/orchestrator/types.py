"""Orchestrator data types and plan loading."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from anime_game_afk.runtime.logger import get_logger

logger = get_logger("orchestrator.types")


@dataclass
class ProcessDef:
    """One process entry in a user plan.

    Attributes:
        name: Process identifier matching a registered process class.
        enabled: Whether this process should run. Defaults to True.
        config: Process-specific configuration passed to ProcessContext.
    """
    name: str
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanConfig:
    """Complete user plan loaded from YAML.

    Attributes:
        game: Game identifier (e.g. "aether_gazer").
        processes: Ordered list of process definitions.
    """
    game: str
    processes: list[ProcessDef] = field(default_factory=list)

    @property
    def enabled_processes(self) -> list[ProcessDef]:
        """Return only processes with enabled=True, preserving order."""
        return [p for p in self.processes if p.enabled]


@dataclass
class PipelineResult:
    """Summary of a full pipeline execution.

    Attributes:
        total: Number of processes attempted.
        succeeded: Number that completed successfully.
        failed: Number that failed.
        skipped: Number skipped (disabled in plan).
        aborted: True if pipeline stopped early due to unrecoverable error.
        details: Per-process result summaries.
        elapsed_s: Total wall-clock time in seconds.
    """
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    aborted: bool = False
    details: list[dict[str, Any]] = field(default_factory=list)
    elapsed_s: float = 0.0

    @property
    def success_rate(self) -> float:
        """Fraction of attempted processes that succeeded."""
        if self.total == 0:
            return 0.0
        return self.succeeded / self.total


def _parse_process_def(raw: dict[str, Any]) -> ProcessDef:
    """Parse a single process definition from a YAML dict.

    Args:
        raw: Dict with keys 'name' (required), 'enabled' (optional),
             'config' (optional).

    Returns:
        A validated ProcessDef.

    Raises:
        ValueError: If 'name' key is missing.
    """
    if "name" not in raw:
        raise ValueError(f"Process definition missing 'name': {raw}")

    return ProcessDef(
        name=raw["name"],
        enabled=raw.get("enabled", True),
        config=raw.get("config", {}),
    )


def load_plan(source: "str | Path | dict[str, Any]") -> PlanConfig:
    """Load a pipeline plan from a YAML file path or a pre-parsed dict.

    Args:
        source: Either a file path (str/Path) to a YAML file,
                or a dict already parsed from YAML.

    Returns:
        A validated PlanConfig.

    Raises:
        FileNotFoundError: If source is a path and file does not exist.
        ValueError: If plan structure is invalid.
    """
    if isinstance(source, dict):
        data = source
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Plan file not found: {path}")
        logger.info("Loading plan from {path}", path=str(path))
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Plan must be a YAML mapping, got {type(data).__name__}")

    game = data.get("game")
    if not game:
        raise ValueError("Plan missing required 'game' field")

    raw_processes = data.get("processes", [])
    if not isinstance(raw_processes, list):
        raise ValueError(
            f"'processes' must be a list, got {type(raw_processes).__name__}"
        )

    processes = [_parse_process_def(p) for p in raw_processes]
    logger.info(
        "Plan loaded: game={game}, {total} processes ({enabled} enabled)",
        game=game,
        total=len(processes),
        enabled=sum(1 for p in processes if p.enabled),
    )

    return PlanConfig(game=game, processes=processes)
