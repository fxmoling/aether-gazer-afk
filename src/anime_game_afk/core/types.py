"""Shared type definitions for the automation framework."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    """A 2D integer coordinate."""

    x: int
    y: int


@dataclass(frozen=True)
class Rect:
    """An axis-aligned rectangle defined by its top-left corner, width, and height."""

    x: int
    y: int
    w: int
    h: int

    @property
    def x2(self) -> int:
        """Right edge (exclusive)."""
        return self.x + self.w

    @property
    def y2(self) -> int:
        """Bottom edge (exclusive)."""
        return self.y + self.h

    def contains(self, p: Point) -> bool:
        """Return True if point p lies inside this rectangle (inclusive left/top, exclusive right/bottom)."""
        return self.x <= p.x < self.x2 and self.y <= p.y < self.y2


@dataclass(frozen=True)
class Resolution:
    """Screen or window resolution."""

    width: int
    height: int


@dataclass(frozen=True)
class DeviceConfig:
    """Configuration for DeviceAdapter — lives in core to avoid layer violations.

    All fields are required except ``game_exe_path`` and ``background``.
    Higher-level ``GameConfig`` provides a ``.to_device_config()``
    convenience method for the conversion.

    When ``background`` is True, DeviceAdapter automatically:
    - Creates a hidden virtual desktop
    - Launches the game there (requires ``game_exe_path``)
    - Uses PrintWindow for screencap (only method that works cross-desktop)
    - Uses SendMessageWithCursorPos for input (moves virtual desktop cursor only)
    - Cleans up desktop + game process on disconnect()

    Game-layer code (ops, tasks, checks) is completely unaware of this —
    ``device.click()`` and ``device.screenshot()`` behave identically.
    """

    window_title: str
    screencap_method: int
    mouse_method: int
    keyboard_method: int
    game_exe_path: str = ""
    background: bool = False
