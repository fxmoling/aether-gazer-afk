"""Base types for processes (complete user-visible features).

Processes are the top-level units users see and enable.
They compose Layer 6 tasks and are NOT composable by each other.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

from anime_game_afk.games.aether_gazer.orchestrator.listener import (
    PipelineListener,
)
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext


@dataclass
class ProcessResult:
    """Result of a complete process."""
    status: Literal["success", "failed", "skipped"]
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessContext(TaskContext):
    """Extended context for processes. Adds process-level config and listener."""
    config: dict[str, Any] = field(default_factory=dict)
    listener: PipelineListener | None = None

    def notify_task(self, task_id: str, status: str, message: str = "") -> None:
        """Fire a task status event if a listener is attached."""
        if self.listener is not None:
            self.listener.on_task_status(task_id, status, message)


@runtime_checkable
class Process(Protocol):
    """Protocol for user-visible processes."""
    name: str
    description: str

    async def execute(self, ctx: ProcessContext) -> ProcessResult: ...
