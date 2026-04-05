"""Base types for composable tasks.

Tasks compose atomic ops (Layer 5) with control flow.
Each task does one logical thing: clear a stage, buy items, collect mail.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

from anime_game_afk.games.aether_gazer.ops.base import OpContext


@dataclass
class TaskResult:
    """Result of a composable task."""
    status: Literal["success", "failed", "skipped"]
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class TaskContext(OpContext):
    """Extended context for tasks. Inherits device/logger from OpContext.

    Tasks may add task-level state (e.g. stages_cleared counter).
    """
    pass


@runtime_checkable
class Task(Protocol):
    """Protocol for composable tasks."""
    name: str

    async def execute(self, ctx: TaskContext) -> TaskResult: ...

    async def can_run(self, ctx: TaskContext) -> bool: ...
