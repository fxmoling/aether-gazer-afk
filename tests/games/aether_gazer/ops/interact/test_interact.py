"""Tests for interact ops."""
import asyncio
from dataclasses import dataclass, field

import numpy as np

from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.games.aether_gazer.ops.interact.advance_dialogue import (
    AdvanceDialogueAction,
)
from anime_game_afk.games.aether_gazer.ops.interact.click_element import (
    ClickElementAction,
)
from anime_game_afk.games.aether_gazer.ops.interact.confirm_popup import (
    ConfirmPopupAction,
)
from anime_game_afk.games.aether_gazer.ops.interact.skip_cutscene import (
    SkipCutsceneAction,
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


def test_click_element_success():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = ClickElementAction("main_hub", "Shop", wait_after=0.0)
    result = _run(op.run(ctx))
    assert result.success
    assert (910, 850) in device.click_log


def test_click_element_not_found():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = ClickElementAction("main_hub", "Nonexistent", wait_after=0.0)
    result = _run(op.run(ctx))
    assert not result.success
    assert "not found" in result.error


def test_click_element_unsafe_blocked():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = ClickElementAction("main_hub", "Gacha", wait_after=0.0)
    result = _run(op.run(ctx))
    assert not result.success
    assert "unsafe" in result.error


def test_click_element_unsafe_forced():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = ClickElementAction(
        "main_hub", "Gacha", wait_after=0.0, force_unsafe=True
    )
    result = _run(op.run(ctx))
    assert result.success


def test_skip_cutscene():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = SkipCutsceneAction(confirm_wait=0.0)
    result = _run(op.run(ctx))
    assert result.success
    assert 0x1B in device.key_log  # ESC
    assert 0x0D in device.key_log  # Enter


def test_advance_dialogue():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = AdvanceDialogueAction(wait_after=0.0)
    result = _run(op.run(ctx))
    assert result.success
    assert 0x20 in device.key_log  # Space


def test_confirm_popup_confirm():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = ConfirmPopupAction(confirm=True, wait_after=0.0)
    result = _run(op.run(ctx))
    assert result.success
    assert result.data["confirmed"] is True
    assert 0x0D in device.key_log


def test_confirm_popup_dismiss():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = ConfirmPopupAction(confirm=False, wait_after=0.0)
    result = _run(op.run(ctx))
    assert result.success
    assert result.data["confirmed"] is False
    assert 0x1B in device.key_log
