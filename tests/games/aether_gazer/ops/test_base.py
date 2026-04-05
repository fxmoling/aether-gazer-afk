"""Tests for ops.base module."""
import asyncio
from dataclasses import dataclass

import numpy as np

from anime_game_afk.games.aether_gazer.ops.base import (
    GameState,
    Op,
    OpContext,
    OpResult,
)


@dataclass
class MockDevice:
    """Minimal device mock for testing."""
    click_log: list = None
    key_log: list = None

    def __post_init__(self):
        self.click_log = self.click_log or []
        self.key_log = self.key_log or []

    def screenshot(self) -> np.ndarray:
        return np.zeros((900, 1600, 3), dtype=np.uint8)

    def click(self, x: int, y: int) -> None:
        self.click_log.append((x, y))

    def press_key(self, vk_code: int) -> None:
        self.key_log.append(vk_code)

    def hold_key(self, vk_code: int, duration_s: float) -> None:
        self.key_log.append((vk_code, duration_s))


class TrivialOp:
    """Op that always succeeds."""
    async def run(self, ctx: OpContext) -> OpResult:
        return OpResult(success=True, data="ok")


def test_op_result_success():
    r = OpResult(success=True, data=42)
    assert r.success
    assert r.data == 42
    assert r.error is None


def test_op_result_failure():
    r = OpResult(success=False, error="timeout")
    assert not r.success
    assert r.error == "timeout"


def test_op_protocol():
    op = TrivialOp()
    assert isinstance(op, Op)


def test_op_context_screenshot():
    device = MockDevice()
    ctx = OpContext(device=device)
    img = ctx.screenshot()
    assert img.shape == (900, 1600, 3)


def test_trivial_op_run():
    device = MockDevice()
    ctx = OpContext(device=device)
    result = asyncio.get_event_loop().run_until_complete(
        TrivialOp().run(ctx)
    )
    assert result.success
    assert result.data == "ok"


def test_game_state_enum():
    assert GameState.BATTLE.value == "battle"
    assert GameState.UNKNOWN.value == "unknown"
    assert len(GameState) == 11
