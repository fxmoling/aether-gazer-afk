"""Tests for tasks.stamina_tasks — CheckAndRefillStamina."""
import asyncio
from dataclasses import dataclass, field

import numpy as np

from anime_game_afk.games.aether_gazer.knowledge.constants import STAMINA_CAP
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext
from anime_game_afk.games.aether_gazer.tasks.stamina_tasks import (
    CheckAndRefillStamina,
)


@dataclass
class MockDevice:
    def screenshot(self) -> np.ndarray:
        return np.zeros((900, 1600, 3), dtype=np.uint8)
    def click(self, x: int, y: int) -> None: ...
    def press_key(self, vk_code: int) -> None: ...
    def hold_key(self, vk_code: int, duration_s: float) -> None: ...


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_check_and_refill_skips_when_sufficient():
    """If stamina >= threshold, task should be skipped."""
    device = MockDevice()
    ctx = TaskContext(device=device, state={"stamina": 100})
    result = _run(CheckAndRefillStamina(threshold=60).execute(ctx))
    assert result.status == "skipped"
    assert result.data["stamina"] == 100


def test_check_and_refill_skips_at_cap():
    """Stamina at cap should be skipped."""
    device = MockDevice()
    ctx = TaskContext(device=device, state={"stamina": STAMINA_CAP})
    result = _run(CheckAndRefillStamina().execute(ctx))
    assert result.status == "skipped"


def test_check_and_refill_acts_when_low():
    """If stamina < threshold, task should attempt refill (success or queued)."""
    device = MockDevice()
    ctx = TaskContext(device=device, state={"stamina": 30})
    result = _run(CheckAndRefillStamina(threshold=60).execute(ctx))
    assert result.status == "success"
    assert result.data["stamina_before"] == 30


def test_check_and_refill_default_stamina():
    """When stamina not set in state, defaults to STAMINA_CAP (skips)."""
    device = MockDevice()
    ctx = TaskContext(device=device)  # no stamina in state
    result = _run(CheckAndRefillStamina().execute(ctx))
    # Default is STAMINA_CAP which is >= threshold, so skipped
    assert result.status == "skipped"


def test_check_and_refill_threshold_boundary():
    """Stamina exactly at threshold should be skipped (>= check)."""
    device = MockDevice()
    ctx = TaskContext(device=device, state={"stamina": 60})
    result = _run(CheckAndRefillStamina(threshold=60).execute(ctx))
    assert result.status == "skipped"


def test_check_and_refill_can_run():
    device = MockDevice()
    ctx = TaskContext(device=device)
    assert _run(CheckAndRefillStamina().can_run(ctx)) is True


def test_check_and_refill_name():
    assert CheckAndRefillStamina.name == "check_and_refill_stamina"
