"""Tests for tasks.navigation_tasks — ReturnToHub."""
import asyncio
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, patch

import numpy as np

from anime_game_afk.games.aether_gazer.ops.base import OpResult
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext
from anime_game_afk.games.aether_gazer.tasks.navigation_tasks import (
    ReturnToHub,
)


@dataclass
class MockDevice:
    click_log: list = field(default_factory=list)
    key_log: list = field(default_factory=list)

    def screenshot(self) -> np.ndarray:
        return np.zeros((900, 1600, 3), dtype=np.uint8)
    def click(self, x: int, y: int) -> None:
        self.click_log.append((x, y))
    def press_key(self, vk_code: int) -> None:
        self.key_log.append(vk_code)
    def hold_key(self, vk_code: int, duration_s: float) -> None:
        pass


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# --- ReturnToHub ---

def test_return_to_hub_success():
    """ReturnToHub succeeds when op returns success."""
    device = MockDevice()
    ctx = TaskContext(device=device)

    with patch(
        "anime_game_afk.games.aether_gazer.tasks.navigation_tasks"
        ".ReturnToHubAction.run",
        AsyncMock(return_value=OpResult(success=True)),
    ):
        result = _run(ReturnToHub().execute(ctx))

    assert result.status == "success"


def test_return_to_hub_failure():
    """ReturnToHub fails when op returns failure."""
    device = MockDevice()
    ctx = TaskContext(device=device)

    with patch(
        "anime_game_afk.games.aether_gazer.tasks.navigation_tasks"
        ".ReturnToHubAction.run",
        AsyncMock(return_value=OpResult(success=False, error="no hub")),
    ):
        result = _run(ReturnToHub().execute(ctx))

    assert result.status == "failed"
    assert "hub" in result.message.lower()


def test_return_to_hub_can_run():
    device = MockDevice()
    ctx = TaskContext(device=device)
    assert _run(ReturnToHub().can_run(ctx)) is True
