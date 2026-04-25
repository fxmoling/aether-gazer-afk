"""Base types for atomic operations.

Every op implements the Op protocol: async run(ctx) -> OpResult.
Ops are the smallest executable units — each does ONE thing.
Ops do NOT call other ops. Composition belongs in Layer 6.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import numpy as np


@dataclass
class OpResult:
    """Result of an atomic operation."""
    success: bool
    data: Any = None
    error: str | None = None


@runtime_checkable
class DevicePort(Protocol):
    """What ops need from the device (Layer 1).

    Coordinates are fractional [0.0, 1.0] for click/swipe.
    """
    def screenshot(self) -> np.ndarray: ...
    def click(self, fx: float, fy: float) -> None: ...
    def press_key(self, vk_code: int) -> None: ...
    def hold_key(self, vk_code: int, duration_s: float) -> None: ...


@runtime_checkable
class LoggerPort(Protocol):
    """What ops need from the logger (Layer 3)."""
    def info(self, msg: str, **ctx: Any) -> None: ...
    def debug(self, msg: str, **ctx: Any) -> None: ...
    def warning(self, msg: str, **ctx: Any) -> None: ...
    def error(self, msg: str, **ctx: Any) -> None: ...


class _NullLogger:
    """Fallback logger that does nothing."""
    def info(self, msg: str, **ctx: Any) -> None: ...
    def debug(self, msg: str, **ctx: Any) -> None: ...
    def warning(self, msg: str, **ctx: Any) -> None: ...
    def error(self, msg: str, **ctx: Any) -> None: ...


@dataclass
class OpContext:
    """Shared context passed to all ops.

    Provides access to device I/O, logging, and shared state.
    Vision functions are imported directly by ops (stateless Layer 2).
    Knowledge is imported directly by ops (pure data Layer 4).
    """
    device: DevicePort
    logger: LoggerPort = field(default_factory=_NullLogger)
    state: dict[str, Any] = field(default_factory=dict)

    def screenshot(self) -> np.ndarray:
        """Convenience: take screenshot via device."""
        return self.device.screenshot()


@runtime_checkable
class Op(Protocol):
    """Protocol for atomic operations."""
    async def run(self, ctx: OpContext) -> OpResult: ...
