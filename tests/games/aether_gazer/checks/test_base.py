"""Tests for checks.base module."""
import asyncio
from dataclasses import dataclass

import numpy as np

from anime_game_afk.games.aether_gazer.checks.base import Check, CheckResult
from anime_game_afk.games.aether_gazer.ops.base import OpContext


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


class TrivialCheck:
    """Check that always passes."""
    async def evaluate(self, ctx: OpContext) -> CheckResult:
        return CheckResult(passed=True, data="ok", message="trivial")


def test_check_result_passed():
    r = CheckResult(passed=True, data=42, message="found it")
    assert r.passed
    assert r.data == 42
    assert r.message == "found it"


def test_check_result_failed():
    r = CheckResult(passed=False, message="not found")
    assert not r.passed
    assert r.data is None
    assert r.message == "not found"


def test_check_protocol():
    check = TrivialCheck()
    assert isinstance(check, Check)


def test_trivial_check_evaluate():
    device = MockDevice()
    ctx = OpContext(device=device)
    result = asyncio.get_event_loop().run_until_complete(
        TrivialCheck().evaluate(ctx)
    )
    assert result.passed
    assert result.data == "ok"
