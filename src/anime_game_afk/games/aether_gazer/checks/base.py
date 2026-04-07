"""Base types for checks.

Every check implements the Check protocol: async evaluate(ctx) -> CheckResult.
Checks are pure observers — they take screenshots and analyze them, but
NEVER modify game state (no clicks, no key presses, no swipes).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from anime_game_afk.games.aether_gazer.ops.base import OpContext


@dataclass
class CheckResult:
    """Result of a check evaluation."""

    passed: bool
    data: Any = None
    message: str = ""


@runtime_checkable
class Check(Protocol):
    """Protocol for checks — observe without modifying state."""

    async def evaluate(self, ctx: OpContext) -> CheckResult: ...
