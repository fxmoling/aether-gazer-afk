"""Tests for ops.primitives module — 6 primitive Op wrappers."""
import asyncio
from dataclasses import dataclass

import numpy as np

from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.games.aether_gazer.ops.primitives import (
    ClickOp,
    HoldKeyOp,
    PressKeyOp,
    ScreenshotOp,
    SleepOp,
    SwipeOp,
)


@dataclass
class MockDevice:
    """Minimal device mock for testing."""
    click_log: list = None
    key_log: list = None
    swipe_log: list = None

    def __post_init__(self):
        self.click_log = self.click_log or []
        self.key_log = self.key_log or []
        self.swipe_log = self.swipe_log or []

    def screenshot(self) -> np.ndarray:
        return np.zeros((900, 1600, 3), dtype=np.uint8)

    def click(self, x: int, y: int) -> None:
        self.click_log.append((x, y))

    def press_key(self, vk_code: int) -> None:
        self.key_log.append(vk_code)

    def hold_key(self, vk_code: int, duration_s: float) -> None:
        self.key_log.append((vk_code, duration_s))

    def swipe(
        self, x1: int, y1: int, x2: int, y2: int, duration: int = 300,
    ) -> None:
        self.swipe_log.append((x1, y1, x2, y2, duration))


def _run(coro):
    """Helper: run a coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_ctx(device=None) -> OpContext:
    return OpContext(device=device or MockDevice())


# ── ClickOp ──


def test_click_op():
    device = MockDevice()
    ctx = _make_ctx(device)
    result = _run(ClickOp(x=100, y=200, wait=0).run(ctx))
    assert result.success
    assert result.data == {"x": 100, "y": 200}
    assert device.click_log == [(100, 200)]


def test_click_op_failure():
    device = MockDevice()
    device.click = lambda x, y: (_ for _ in ()).throw(
        RuntimeError("click failed")
    )
    ctx = _make_ctx(device)
    result = _run(ClickOp(x=50, y=60, wait=0).run(ctx))
    assert not result.success
    assert "click failed" in result.error


# ── PressKeyOp ──


def test_press_key_op():
    device = MockDevice()
    ctx = _make_ctx(device)
    result = _run(PressKeyOp(key=0x0D, wait=0).run(ctx))
    assert result.success
    assert result.data == {"key": 0x0D}
    assert device.key_log == [0x0D]


def test_press_key_op_failure():
    device = MockDevice()
    device.press_key = lambda vk: (_ for _ in ()).throw(
        RuntimeError("key failed")
    )
    ctx = _make_ctx(device)
    result = _run(PressKeyOp(key=0x1B, wait=0).run(ctx))
    assert not result.success
    assert "key failed" in result.error


# ── HoldKeyOp ──


def test_hold_key_op():
    device = MockDevice()
    ctx = _make_ctx(device)
    result = _run(HoldKeyOp(key=0x57, duration=2.0, wait=0).run(ctx))
    assert result.success
    assert result.data == {"key": 0x57, "duration": 2.0}
    assert device.key_log == [(0x57, 2.0)]


def test_hold_key_op_failure():
    device = MockDevice()
    device.hold_key = lambda vk, dur: (_ for _ in ()).throw(
        RuntimeError("hold failed")
    )
    ctx = _make_ctx(device)
    result = _run(HoldKeyOp(key=0x57, duration=1.0, wait=0).run(ctx))
    assert not result.success
    assert "hold failed" in result.error


# ── SwipeOp ──


def test_swipe_op():
    device = MockDevice()
    ctx = _make_ctx(device)
    result = _run(SwipeOp(x1=100, y1=200, x2=300, y2=400,
                          duration=500, wait=0).run(ctx))
    assert result.success
    assert result.data == {"from": (100, 200), "to": (300, 400)}
    assert device.swipe_log == [(100, 200, 300, 400, 500)]


def test_swipe_op_failure():
    device = MockDevice()
    device.swipe = lambda *a, **kw: (_ for _ in ()).throw(
        RuntimeError("swipe failed")
    )
    ctx = _make_ctx(device)
    result = _run(SwipeOp(x1=0, y1=0, x2=100, y2=100, wait=0).run(ctx))
    assert not result.success
    assert "swipe failed" in result.error


# ── SleepOp ──


def test_sleep_op():
    ctx = _make_ctx()
    result = _run(SleepOp(seconds=1.5).run(ctx))
    assert result.success
    assert result.data == {"seconds": 1.5}


# ── ScreenshotOp ──


def test_screenshot_op():
    ctx = _make_ctx()
    result = _run(ScreenshotOp().run(ctx))
    assert result.success
    assert isinstance(result.data, np.ndarray)
    assert result.data.shape == (900, 1600, 3)


def test_screenshot_op_failure():
    device = MockDevice()
    device.screenshot = lambda: (_ for _ in ()).throw(
        RuntimeError("screenshot failed")
    )
    ctx = _make_ctx(device)
    result = _run(ScreenshotOp().run(ctx))
    assert not result.success
    assert "screenshot failed" in result.error
