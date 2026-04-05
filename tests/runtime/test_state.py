"""Tests for runtime.state — StateStore persistent JSON key-value store."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from anime_game_afk.runtime.state import StateStore


# ---------------------------------------------------------------------------
# Basic CRUD
# ---------------------------------------------------------------------------


def test_set_and_get(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    store.set("name", "tester")
    assert store.get("name") == "tester"


def test_get_missing_key_returns_none_by_default(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    assert store.get("missing") is None


def test_get_missing_key_returns_supplied_default(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    assert store.get("missing", 42) == 42


def test_get_none_value_returns_none_not_default(tmp_path: Path) -> None:
    """A key whose value is explicitly None should return None, not the default."""
    store = StateStore(tmp_path / "state.json")
    store.set("nul", None)
    assert store.get("nul", "fallback") is None


def test_set_overwrites_existing_value(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    store.set("count", 1)
    store.set("count", 2)
    assert store.get("count") == 2


# ---------------------------------------------------------------------------
# has
# ---------------------------------------------------------------------------


def test_has_existing_key_returns_true(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    store.set("x", 10)
    assert store.has("x") is True


def test_has_missing_key_returns_false(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    assert store.has("missing") is False


def test_has_none_value_returns_true(tmp_path: Path) -> None:
    """has() must return True even when the stored value is None."""
    store = StateStore(tmp_path / "state.json")
    store.set("nullable", None)
    assert store.has("nullable") is True


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_delete_removes_key(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    store.set("to_remove", "bye")
    store.delete("to_remove")
    assert store.has("to_remove") is False


def test_delete_missing_key_is_noop(tmp_path: Path) -> None:
    """Deleting a non-existent key must not raise."""
    store = StateStore(tmp_path / "state.json")
    store.delete("ghost")  # should not raise


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


def test_clear_removes_all_entries(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    store.set("a", 1)
    store.set("b", 2)
    store.clear()
    assert store.keys == []


def test_clear_persists_empty_state(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = StateStore(path)
    store.set("k", "v")
    store.clear()

    reloaded = StateStore(path)
    assert reloaded.keys == []


# ---------------------------------------------------------------------------
# keys
# ---------------------------------------------------------------------------


def test_keys_returns_all_stored_keys(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    store.set("a", 1)
    store.set("b", 2)
    assert sorted(store.keys) == ["a", "b"]


def test_keys_empty_when_no_entries(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    assert store.keys == []


# ---------------------------------------------------------------------------
# Persistence across restarts
# ---------------------------------------------------------------------------


def test_value_persists_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    s1 = StateStore(path)
    s1.set("session", "abc123")

    s2 = StateStore(path)
    assert s2.get("session") == "abc123"


def test_multiple_values_persist(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    s1 = StateStore(path)
    s1.set("level", 5)
    s1.set("gold", 200)
    s1.set("name", "hero")

    s2 = StateStore(path)
    assert s2.get("level") == 5
    assert s2.get("gold") == 200
    assert s2.get("name") == "hero"


def test_nested_structures_persist(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    s1 = StateStore(path)
    s1.set("config", {"fps": 60, "vsync": True})

    s2 = StateStore(path)
    assert s2.get("config") == {"fps": 60, "vsync": True}


# ---------------------------------------------------------------------------
# Missing file — start empty
# ---------------------------------------------------------------------------


def test_missing_file_starts_empty(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "nonexistent.json")
    assert store.keys == []
    assert store.get("anything") is None


# ---------------------------------------------------------------------------
# Parent directory is created automatically
# ---------------------------------------------------------------------------


def test_creates_parent_directory(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "deep" / "state.json"
    store = StateStore(path)
    store.set("key", "value")
    assert path.exists()


# ---------------------------------------------------------------------------
# JSON file content sanity check
# ---------------------------------------------------------------------------


def test_file_contains_valid_json(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = StateStore(path)
    store.set("answer", 42)

    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["answer"] == 42
