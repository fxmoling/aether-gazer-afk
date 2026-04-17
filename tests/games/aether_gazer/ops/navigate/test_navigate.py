"""Tests for navigate ops."""
import asyncio
from dataclasses import dataclass, field

import numpy as np

from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.games.aether_gazer.ops.navigate.go_back import GoBackAction
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


def test_wake_hub_ui_clicks_center():
    device = MockDevice()
    ctx = OpContext(device=device)
    result = _run(WakeHubUiAction().run(ctx))
    assert result.success
    assert (0.5, 0.5) in device.click_log


def test_go_back_unknown_presses_esc():
    device = MockDevice()
    ctx = OpContext(device=device)
    result = _run(GoBackAction("unknown").run(ctx))
    assert result.success
    assert 0x1B in device.key_log  # VK_ESCAPE


def test_go_back_shop_clicks_back():
    device = MockDevice()
    ctx = OpContext(device=device)
    result = _run(GoBackAction("shop").run(ctx))
    assert result.success
    # Back button coord is fractional (0.022, 0.039) from navigation.py
    assert len(device.click_log) >= 1
    fx, fy = device.click_log[0]
    assert abs(fx - 0.022) < 0.01
    assert abs(fy - 0.039) < 0.01
