"""Tests for ops.primitives module — 6 primitive Op wrappers.

Updated for fractional coordinate API:
- ClickOp/SwipeOp take fractional [0.0, 1.0] coordinates
- wait is keyword-only with default 0.15
- ClickOp.result.data includes both fractional and pixel coords
- SwipeOp.result.data uses fractional coords for "from"/"to"
"""
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


# -- ClickOp --


def test_click_op():
    device = MockDevice()
    ctx = _make_ctx(device)
    result = _run(ClickOp(x=0.5, y=0.5, wait=0).run(ctx))
    assert result.success
    assert result.data == {"x": 0.5, "y": 0.5, "px": 800, "py": 450}
    assert device.click_log == [(800, 450)]


def test_click_op_corner():
    """ClickOp at (0.0, 0.0) should click pixel (0, 0)."""
    device = MockDevice()
    ctx = _make_ctx(device)
    result = _run(ClickOp(x=0.0, y=0.0, wait=0).run(ctx))
    assert result.success
    assert device.click_log == [(0, 0)]


def test_click_op_bottom_right():
    """ClickOp at (1.0, 1.0) should click pixel (1600, 900)."""
    device = MockDevice()
    ctx = _make_ctx(device)
    result = _run(ClickOp(x=1.0, y=1.0, wait=0).run(ctx))
    assert result.success
    assert device.click_log == [(1600, 900)]


def test_click_op_failure():
    device = MockDevice()
    device.click = lambda x, y: (_ for _ in ()).throw(
        RuntimeError("click failed")
    )
    ctx = _make_ctx(device)
    result = _run(ClickOp(x=0.5, y=0.5, wait=0).run(ctx))
    assert not result.success
    assert "click failed" in result.error


# -- PressKeyOp --


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


# -- HoldKeyOp --


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


# -- SwipeOp --


def test_swipe_op():
    device = MockDevice()
    ctx = _make_ctx(device)
    result = _run(SwipeOp(x1=0.0, y1=0.0, x2=1.0, y2=1.0,
                          duration=500, wait=0).run(ctx))
    assert result.success
    assert result.data == {"from": (0.0, 0.0), "to": (1.0, 1.0)}
    assert device.swipe_log == [(0, 0, 1600, 900, 500)]


def test_swipe_op_center_to_corner():
    """SwipeOp from center to bottom-right quarter."""
    device = MockDevice()
    ctx = _make_ctx(device)
    result = _run(SwipeOp(x1=0.5, y1=0.5, x2=0.75, y2=0.75, wait=0).run(ctx))
    assert result.success
    assert device.swipe_log == [(800, 450, 1200, 675, 300)]


def test_swipe_op_failure():
    device = MockDevice()
    device.swipe = lambda *a, **kw: (_ for _ in ()).throw(
        RuntimeError("swipe failed")
    )
    ctx = _make_ctx(device)
    result = _run(SwipeOp(x1=0.0, y1=0.0, x2=0.5, y2=0.5, wait=0).run(ctx))
    assert not result.success
    assert "swipe failed" in result.error


# -- SleepOp --


def test_sleep_op():
    ctx = _make_ctx()
    result = _run(SleepOp(seconds=1.5).run(ctx))
    assert result.success
    assert result.data == {"seconds": 1.5}


# -- ScreenshotOp --


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
