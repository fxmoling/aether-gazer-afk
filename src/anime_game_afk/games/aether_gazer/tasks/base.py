"""Base types for composable tasks.

Tasks compose atomic ops (Layer 5) with control flow.
Each task does one logical thing: clear a stage, buy items, collect mail.

Every task class should define metadata attributes for dependency tracking:
- name: unique identifier
- description: human-readable summary
- category: grouping (e.g. "daily_shop", "combat", "navigation")
- requires_pages: list of page IDs the task navigates through
- requires_ocr: whether real OCR is needed (not just template matching)
- safe: False if the task spends in-game currency or resources
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
    """Protocol for composable tasks.

    Required attributes:
        name: Unique task identifier (e.g. "buy_intel_shards").
        description: Human-readable one-line summary.

    Optional metadata (set as class attributes with defaults):
        category: Task grouping for UI/logging.
        requires_pages: Page IDs this task navigates through.
        requires_ocr: True if real OCR (not just template matching) is needed.
        safe: False if this task spends currency or resources.
    """
    name: str
    description: str

    async def execute(self, ctx: TaskContext) -> TaskResult: ...

    async def can_run(self, ctx: TaskContext) -> bool: ...


# Default metadata values — concrete task classes override these.
TASK_DEFAULTS = {
    "category": "general",
    "requires_pages": (),
    "requires_ocr": False,
    "safe": True,
}


def task_info(task: Task) -> dict[str, Any]:
    """Extract metadata from a task instance for logging/registry."""
    return {
        "name": task.name,
        "description": getattr(task, "description", ""),
        "category": getattr(task, "category", "general"),
        "requires_pages": getattr(task, "requires_pages", ()),
        "requires_ocr": getattr(task, "requires_ocr", False),
        "safe": getattr(task, "safe", True),
    }
