"""Tests for runtime.config — ConfigStore YAML/dict configuration loader."""
from __future__ import annotations

from pathlib import Path

import pytest

from anime_game_afk.runtime.config import ConfigStore


# ---------------------------------------------------------------------------
# from_dict
# ---------------------------------------------------------------------------


def test_from_dict_creates_store() -> None:
    cfg = ConfigStore.from_dict({"key": "value"})
    assert isinstance(cfg, ConfigStore)


def test_from_dict_empty() -> None:
    cfg = ConfigStore.from_dict({})
    assert cfg.raw == {}


def test_empty_constructor() -> None:
    cfg = ConfigStore()
    assert cfg.raw == {}


# ---------------------------------------------------------------------------
# get — flat keys
# ---------------------------------------------------------------------------


def test_get_existing_key() -> None:
    cfg = ConfigStore.from_dict({"fps": 60})
    assert cfg.get("fps") == 60


def test_get_missing_key_returns_none_by_default() -> None:
    cfg = ConfigStore.from_dict({})
    assert cfg.get("missing") is None


def test_get_missing_key_returns_supplied_default() -> None:
    cfg = ConfigStore.from_dict({})
    assert cfg.get("missing", 42) == 42


def test_get_none_value_returns_none_not_default() -> None:
    """A key whose value is None should return None, not the default."""
    cfg = ConfigStore.from_dict({"key": None})
    assert cfg.get("key", "default") is None


# ---------------------------------------------------------------------------
# get — nested dot-path
# ---------------------------------------------------------------------------


def test_get_nested_two_levels() -> None:
    cfg = ConfigStore.from_dict({"game": {"fps": 60}})
    assert cfg.get("game.fps") == 60


def test_get_nested_three_levels() -> None:
    cfg = ConfigStore.from_dict({"game": {"resolution": {"width": 1600}}})
    assert cfg.get("game.resolution.width") == 1600


def test_get_partial_path_returns_subtree() -> None:
    """Accessing an intermediate node returns the sub-dict."""
    cfg = ConfigStore.from_dict({"game": {"fps": 60, "vsync": True}})
    subtree = cfg.get("game")
    assert subtree == {"fps": 60, "vsync": True}


def test_get_path_through_non_dict_returns_default() -> None:
    """If a mid-path node is a scalar, return default (don't crash)."""
    cfg = ConfigStore.from_dict({"a": 5})
    assert cfg.get("a.b", "fallback") == "fallback"


def test_get_deeply_missing_path_returns_default() -> None:
    cfg = ConfigStore.from_dict({"a": {"b": {}}})
    assert cfg.get("a.b.c.d", -1) == -1


# ---------------------------------------------------------------------------
# set
# ---------------------------------------------------------------------------


def test_set_flat_key() -> None:
    cfg = ConfigStore()
    cfg.set("fps", 30)
    assert cfg.get("fps") == 30


def test_set_creates_intermediate_dicts() -> None:
    cfg = ConfigStore()
    cfg.set("game.resolution.width", 1920)
    assert cfg.get("game.resolution.width") == 1920


def test_set_overwrites_existing_value() -> None:
    cfg = ConfigStore.from_dict({"fps": 30})
    cfg.set("fps", 60)
    assert cfg.get("fps") == 60


def test_set_replaces_scalar_with_dict() -> None:
    """If an intermediate key holds a scalar, set() should replace it."""
    cfg = ConfigStore.from_dict({"a": 5})
    cfg.set("a.b", 10)
    assert cfg.get("a.b") == 10


def test_set_multiple_sibling_keys() -> None:
    cfg = ConfigStore()
    cfg.set("game.width", 1600)
    cfg.set("game.height", 900)
    assert cfg.get("game.width") == 1600
    assert cfg.get("game.height") == 900


# ---------------------------------------------------------------------------
# has
# ---------------------------------------------------------------------------


def test_has_existing_key_returns_true() -> None:
    cfg = ConfigStore.from_dict({"key": "val"})
    assert cfg.has("key") is True


def test_has_missing_key_returns_false() -> None:
    cfg = ConfigStore.from_dict({})
    assert cfg.has("missing") is False


def test_has_none_value_returns_true() -> None:
    """has() must return True even when the stored value is None."""
    cfg = ConfigStore.from_dict({"key": None})
    assert cfg.has("key") is True


def test_has_nested_key() -> None:
    cfg = ConfigStore.from_dict({"a": {"b": 1}})
    assert cfg.has("a.b") is True
    assert cfg.has("a.c") is False


# ---------------------------------------------------------------------------
# from_yaml
# ---------------------------------------------------------------------------


def test_from_yaml_loads_simple_values(tmp_path: Path) -> None:
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text("fps: 60\nvsync: true\n", encoding="utf-8")
    cfg = ConfigStore.from_yaml(yaml_file)
    assert cfg.get("fps") == 60
    assert cfg.get("vsync") is True


def test_from_yaml_loads_nested_values(tmp_path: Path) -> None:
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(
        "game:\n  resolution:\n    width: 1600\n    height: 900\n",
        encoding="utf-8",
    )
    cfg = ConfigStore.from_yaml(yaml_file)
    assert cfg.get("game.resolution.width") == 1600
    assert cfg.get("game.resolution.height") == 900


def test_from_yaml_accepts_path_object(tmp_path: Path) -> None:
    p = tmp_path / "cfg.yaml"
    p.write_text("x: 1\n", encoding="utf-8")
    cfg = ConfigStore.from_yaml(p)
    assert cfg.get("x") == 1


def test_from_yaml_accepts_string_path(tmp_path: Path) -> None:
    p = tmp_path / "cfg.yaml"
    p.write_text("x: 2\n", encoding="utf-8")
    cfg = ConfigStore.from_yaml(str(p))
    assert cfg.get("x") == 2


def test_from_yaml_empty_file_gives_empty_store(tmp_path: Path) -> None:
    p = tmp_path / "empty.yaml"
    p.write_text("", encoding="utf-8")
    cfg = ConfigStore.from_yaml(p)
    assert cfg.raw == {}


def test_from_yaml_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ConfigStore.from_yaml(tmp_path / "nonexistent.yaml")


# ---------------------------------------------------------------------------
# raw property
# ---------------------------------------------------------------------------


def test_raw_returns_underlying_dict() -> None:
    data = {"a": 1}
    cfg = ConfigStore.from_dict(data)
    assert cfg.raw is data


def test_raw_reflects_set_changes() -> None:
    cfg = ConfigStore()
    cfg.set("x", 99)
    assert cfg.raw["x"] == 99
