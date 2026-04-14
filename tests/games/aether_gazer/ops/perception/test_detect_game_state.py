"""Tests for perception.detect_game_state module."""
import numpy as np

from anime_game_afk.games.aether_gazer.ops.base import GameState
from anime_game_afk.games.aether_gazer.ops.perception.detect_game_state import (
    detect_state,
)


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
