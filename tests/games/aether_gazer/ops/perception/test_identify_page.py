"""Tests for perception.identify_page module."""
import asyncio
from dataclasses import dataclass

import numpy as np

from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.perception.identify_page import (
    IdentifyPageOp,
)


@dataclass
class MockDevice:
    def screenshot(self) -> np.ndarray:
        return np.zeros((900, 1600, 3), dtype=np.uint8)
    def click(self, x: int, y: int) -> None: ...
    def press_key(self, vk_code: int) -> None: ...
    def hold_key(self, vk_code: int, duration_s: float) -> None: ...


def test_identify_returns_result():
    """Op returns OpResult with page_id and confidence keys."""
    ctx = OpContext(device=MockDevice())
    op = IdentifyPageOp()
    result = asyncio.get_event_loop().run_until_complete(op.run(ctx))
    assert isinstance(result, OpResult)
    assert "page_id" in result.data
    assert "confidence" in result.data


def test_black_screen_is_unknown():
    """Black screenshot should not match any page."""
    ctx = OpContext(device=MockDevice())
    op = IdentifyPageOp()
    result = asyncio.get_event_loop().run_until_complete(op.run(ctx))
    # With no templates loaded (test env), expect unknown
    assert result.data["page_id"] == "unknown"
