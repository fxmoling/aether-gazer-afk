"""Tests for perception.detect_game_state module."""
import asyncio
from dataclasses import dataclass

import numpy as np

from anime_game_afk.games.aether_gazer.ops.base import GameState, OpContext
from anime_game_afk.games.aether_gazer.ops.perception.detect_game_state import (
    DetectGameStateOp,
    detect_state,
)


@dataclass
class MockDevice:
    _image: np.ndarray | None = None
    def screenshot(self) -> np.ndarray:
        if self._image is not None:
            return self._image
        return np.zeros((900, 1600, 3), dtype=np.uint8)
    def click(self, x: int, y: int) -> None: ...
    def press_key(self, vk_code: int) -> None: ...
    def hold_key(self, vk_code: int, duration_s: float) -> None: ...


def test_black_screen_is_loading():
    """Fully black image should be detected as LOADING."""
    black = np.zeros((900, 1600, 3), dtype=np.uint8)
    state, conf = detect_state(black)
    assert state == GameState.LOADING
    assert conf > 0.9


def test_bright_screen_not_loading():
    """Non-black image should not be LOADING (without templates)."""
    bright = np.full((900, 1600, 3), 128, dtype=np.uint8)
    state, conf = detect_state(bright)
    # Without templates, non-black = UNKNOWN
    assert state == GameState.UNKNOWN


def test_op_returns_result():
    ctx = OpContext(device=MockDevice())
    op = DetectGameStateOp()
    result = asyncio.get_event_loop().run_until_complete(op.run(ctx))
    assert result.success
    assert "state" in result.data
    assert isinstance(result.data["state"], GameState)
