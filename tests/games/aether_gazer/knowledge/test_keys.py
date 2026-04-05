"""Tests for knowledge.keys module."""
from anime_game_afk.games.aether_gazer.knowledge.keys import (
    ATTACK_CYCLE_KEYS,
    KEY_NAMES,
    MOVE_KEYS,
    SKILL_KEYS,
    VK_ENTER,
    VK_ESCAPE,
    VK_J,
    VK_SPACE,
    VK_W,
    key_name,
)


def test_attack_cycle_length():
    """Attack cycle has 10 keys: J J U J I J O R 1 2."""
    assert len(ATTACK_CYCLE_KEYS) == 10


def test_attack_cycle_starts_with_j():
    assert ATTACK_CYCLE_KEYS[0] == VK_J
    assert ATTACK_CYCLE_KEYS[1] == VK_J


def test_skill_keys_count():
    assert len(SKILL_KEYS) == 3


def test_move_keys_count():
    assert len(MOVE_KEYS) == 4
    assert VK_W in MOVE_KEYS


def test_key_name_known():
    assert key_name(VK_ESCAPE) == "ESC"
    assert key_name(VK_ENTER) == "Enter"
    assert key_name(VK_SPACE) == "Space"
    assert key_name(VK_J) == "J"


def test_key_name_unknown():
    assert key_name(0xFF) == "0xFF"


def test_all_attack_keys_have_names():
    for vk in ATTACK_CYCLE_KEYS:
        assert vk in KEY_NAMES
