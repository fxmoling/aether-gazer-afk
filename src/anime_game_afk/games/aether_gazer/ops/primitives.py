"""Primitive (atomic) operations — direct device wrappers.

Each primitive Op wraps exactly ONE device method call. They add:
- Automatic debug logging
- Post-action wait (configurable)
- Exception capture into OpResult

Primitive Ops do NOT call other Ops. They are the foundation
that composite Ops build on.

Available primitives:
- ClickOp: click at (x, y)
- PressKeyOp: press a virtual key
- HoldKeyOp: hold a key for duration
- SwipeOp: swipe from (x1,y1) to (x2,y2)
- SleepOp: explicit wait
- ScreenshotOp: take screenshot (returns image in data)
"""
from __future__ import annotations

import asyncio

import numpy as np

from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult


class ClickOp:
    """Click at a fixed screen coordinate."""

    def __init__(self, x: int, y: int, wait: float = 0.5) -> None:
        self._x = x
        self._y = y
        self._wait = wait

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.logger.debug(f"click ({self._x}, {self._y})")
        try:
            ctx.device.click(self._x, self._y)
            if self._wait > 0:
                await asyncio.sleep(self._wait)
            return OpResult(
                success=True,
                data={"x": self._x, "y": self._y},
            )
        except Exception as e:
            ctx.logger.error(f"click ({self._x},{self._y}) failed: {e}")
            return OpResult(success=False, error=str(e))


class PressKeyOp:
    """Press a virtual key code."""

    def __init__(self, key: int, wait: float = 0.5) -> None:
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
    """Hold a virtual key for a specified duration."""

    def __init__(
        self,
        key: int,
        duration: float = 1.0,
        wait: float = 0.3,
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
    """Swipe from one coordinate to another."""

    def __init__(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration: int = 300,
        wait: float = 0.5,
    ) -> None:
        self._x1 = x1
        self._y1 = y1
        self._x2 = x2
        self._y2 = y2
        self._duration = duration
        self._wait = wait

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.logger.debug(
            f"swipe ({self._x1},{self._y1})->({self._x2},{self._y2}) "
            f"{self._duration}ms"
        )
        try:
            ctx.device.swipe(
                self._x1, self._y1,
                self._x2, self._y2,
                duration=self._duration,
            )
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
