"""Tests for perception.identify_page module."""
import numpy as np

from anime_game_afk.games.aether_gazer.ops.perception.identify_page import (
    identify,
    is_on_page,
)


def test_identify_returns_result():
    """identify() returns (page_id, confidence) for a black screenshot."""
    black = np.zeros((900, 1600, 3), dtype=np.uint8)
    page_id, confidence = identify(black)
    assert isinstance(page_id, str)
    assert isinstance(confidence, float)


def test_black_screen_is_unknown():
    """Black screenshot should not match any page."""
    black = np.zeros((900, 1600, 3), dtype=np.uint8)
    page_id, _ = identify(black)
    assert page_id == "unknown"


def test_is_on_page_black_returns_false():
    """is_on_page returns False for black screenshot (no templates match)."""
    black = np.zeros((900, 1600, 3), dtype=np.uint8)
    assert is_on_page(black, "main_hub") is False
    assert is_on_page(black, "nonexistent_page") is False
