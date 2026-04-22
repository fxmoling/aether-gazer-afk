"""Tests for navigate ops — WakeHubUiAction."""
import asyncio
from dataclasses import dataclass, field

import numpy as np

from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.games.aether_gazer.ops.navigate.wake_hub_ui import (
    WakeHubUiAction,
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
        self.key_log.append((vk_code, duration_s))


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_wake_hub_ui_unknown_state():
    """On non-hub state, clicks back button to navigate. Never presses ESC."""
    device = MockDevice()
    ctx = OpContext(device=device)
    result = _run(WakeHubUiAction().run(ctx))
    assert result.success
    # Should click back button position (0.022, 0.039)
    assert any(abs(x - 0.022) < 0.01 and abs(y - 0.039) < 0.01 for x, y in device.click_log)
    # Must NOT press ESC (the whole point of the rewrite)
    assert len(device.key_log) == 0
