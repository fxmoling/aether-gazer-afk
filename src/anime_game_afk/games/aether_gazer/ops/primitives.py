"""Primitive (atomic) operations — direct device wrappers.

Each primitive Op wraps exactly ONE device method call. They add:
- Automatic debug logging
- Post-action wait (configurable, default 0.15s)
- Exception capture into OpResult
- Fractional coordinate support (resolution-independent)

Primitive Ops do NOT call other Ops. They are the foundation
that Actions build on.

Coordinate convention:
    All x/y coordinates are fractional values in [0.0, 1.0].
    (0.0, 0.0) = top-left, (1.0, 1.0) = bottom-right, (0.5, 0.5) = center.
    Internally converted to design-resolution pixels (1600x900) before
    passing to device.click().

    Conversion: pixel_x = int(frac_x * DESIGN_WIDTH)
                pixel_y = int(frac_y * DESIGN_HEIGHT)

    Example: center click = ClickOp(x=0.5, y=0.5)
             bottom-right = ClickOp(x=0.96, y=0.94)

Available primitives:
- ClickOp: click at fractional (x, y)
- PressKeyOp: press a virtual key
- HoldKeyOp: hold a key for duration
- SwipeOp: swipe between fractional coordinates
- SleepOp: explicit wait
- ScreenshotOp: take screenshot (returns image in data)
"""
from __future__ import annotations

import asyncio

import numpy as np

from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult

# Design resolution for fractional → pixel conversion.
# All fractional coordinates are relative to this resolution.
_DESIGN_W = 1600
_DESIGN_H = 900


def _to_px(frac_x: float, frac_y: float) -> tuple[int, int]:
    """Convert fractional [0.0, 1.0] coordinates to design-resolution pixels."""
    return int(frac_x * _DESIGN_W), int(frac_y * _DESIGN_H)


class ClickOp:
    """Click at a fractional screen coordinate.

    Args:
        x: Horizontal position as fraction [0.0, 1.0].
        y: Vertical position as fraction [0.0, 1.0].
        wait: Seconds to wait after clicking (keyword-only, default 0.15).
    """

    def __init__(self, x: float, y: float, *, wait: float = 0.15) -> None:
        self._x = x
        self._y = y
        self._wait = wait

    async def run(self, ctx: OpContext) -> OpResult:
        px, py = _to_px(self._x, self._y)
        ctx.logger.debug(f"click ({self._x:.3f}, {self._y:.3f}) -> ({px}, {py})")
        try:
            ctx.device.click(px, py)
            if self._wait > 0:
                await asyncio.sleep(self._wait)
            return OpResult(
                success=True,
                data={"x": self._x, "y": self._y, "px": px, "py": py},
            )
        except Exception as e:
            ctx.logger.error(f"click ({self._x:.3f},{self._y:.3f}) failed: {e}")
            return OpResult(success=False, error=str(e))


class PressKeyOp:
    """Press a virtual key code.

    Args:
        key: Virtual key code (e.g. VK_ENTER = 0x0D).
        wait: Seconds to wait after pressing (keyword-only, default 0.15).
    """

    def __init__(self, key: int, *, wait: float = 0.15) -> None:
        self._key = key
        self._wait = wait

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.logger.debug(f"press_key 0x{self._key:02X}")
        try:
            ctx.device.press_key(self._key)
            if self._wait > 0:
                await asyncio.sleep(self._wait)
            return OpResult(
                success=True,
                data={"key": self._key},
            )
        except Exception as e:
            ctx.logger.error(f"press_key 0x{self._key:02X} failed: {e}")
            return OpResult(success=False, error=str(e))


class HoldKeyOp:
    """Hold a virtual key for a specified duration.

    Args:
        key: Virtual key code.
        duration: How long to hold the key in seconds.
        wait: Seconds to wait after releasing (keyword-only, default 0.15).
    """

    def __init__(
        self,
        key: int,
        duration: float = 1.0,
        *,
        wait: float = 0.15,
    ) -> None:
        self._key = key
        self._duration = duration
        self._wait = wait

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.logger.debug(
            f"hold_key 0x{self._key:02X} for {self._duration}s"
        )
        try:
            ctx.device.hold_key(self._key, self._duration)
            if self._wait > 0:
                await asyncio.sleep(self._wait)
            return OpResult(
                success=True,
                data={"key": self._key, "duration": self._duration},
            )
        except Exception as e:
            ctx.logger.error(f"hold_key 0x{self._key:02X} failed: {e}")
            return OpResult(success=False, error=str(e))


class SwipeOp:
    """Swipe between two fractional coordinates.

    Args:
        x1, y1: Start position as fractions [0.0, 1.0].
        x2, y2: End position as fractions [0.0, 1.0].
        duration: Swipe duration in milliseconds.
        wait: Seconds to wait after swiping (keyword-only, default 0.15).
    """

    def __init__(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        duration: int = 300,
        *,
        wait: float = 0.15,
    ) -> None:
        self._x1 = x1
        self._y1 = y1
        self._x2 = x2
        self._y2 = y2
        self._duration = duration
        self._wait = wait

    async def run(self, ctx: OpContext) -> OpResult:
        px1, py1 = _to_px(self._x1, self._y1)
        px2, py2 = _to_px(self._x2, self._y2)
        ctx.logger.debug(
            f"swipe ({self._x1:.3f},{self._y1:.3f})->"
            f"({self._x2:.3f},{self._y2:.3f}) "
            f"[({px1},{py1})->({px2},{py2})] {self._duration}ms"
        )
        try:
            ctx.device.swipe(px1, py1, px2, py2, duration=self._duration)
            if self._wait > 0:
                await asyncio.sleep(self._wait)
            return OpResult(
                success=True,
                data={
                    "from": (self._x1, self._y1),
                    "to": (self._x2, self._y2),
                },
            )
        except Exception as e:
            ctx.logger.error(f"swipe failed: {e}")
            return OpResult(success=False, error=str(e))


class SleepOp:
    """Explicit wait — makes delays visible and serializable."""

    def __init__(self, seconds: float) -> None:
        self._seconds = seconds

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.logger.debug(f"sleep {self._seconds}s")
        await asyncio.sleep(self._seconds)
        return OpResult(success=True, data={"seconds": self._seconds})


class ScreenshotOp:
    """Take a screenshot. Returns the image in OpResult.data."""

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.logger.debug("screenshot")
        try:
            img = ctx.device.screenshot()
            return OpResult(success=True, data=img)
        except Exception as e:
            ctx.logger.error(f"screenshot failed: {e}")
            return OpResult(success=False, error=str(e))
