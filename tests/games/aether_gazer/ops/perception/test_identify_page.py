"""Tests for perception.identify_page module — is_on_page only."""
import numpy as np

from anime_game_afk.games.aether_gazer.ops.perception.identify_page import (
    is_on_page,
)


def test_is_on_page_black_returns_false():
    """is_on_page returns False for black screenshot (no templates match)."""
    black = np.zeros((900, 1600, 3), dtype=np.uint8)
    assert is_on_page(black, "main_hub") is False
    assert is_on_page(black, "nonexistent_page") is False
