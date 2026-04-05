"""Persistent state store backed by JSON.

Saves/loads key-value pairs to a JSON file. Survives restarts.

Example::

    store = StateStore("data/state.json")
    store.set("last_run", "2026-04-05")
    store.get("last_run")          # "2026-04-05"
    store.has("last_run")          # True
    store.delete("last_run")
    store.clear()
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StateStore:
    """Simple persistent key-value store backed by a JSON file.

    All mutating operations (``set``, ``delete``, ``clear``) immediately
    flush data to disk so state survives process restarts.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._data: dict[str, Any] = {}
        if self._path.exists():
            self._load()

    # ------------------------------------------------------------------
    # Read access
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value stored at *key*, or *default* if absent."""
        return self._data.get(key, default)

    def has(self, key: str) -> bool:
        """Return True if *key* exists (even when its value is None)."""
        return key in self._data

    @property
    def keys(self) -> list[str]:
        """Return a snapshot list of all stored keys."""
        return list(self._data.keys())

    # ------------------------------------------------------------------
    # Write access
    # ------------------------------------------------------------------

    def set(self, key: str, value: Any) -> None:
        """Store *value* under *key* and persist to disk."""
        self._data[key] = value
        self._save()

    def delete(self, key: str) -> None:
        """Remove *key* if it exists, then persist."""
        self._data.pop(key, None)
        self._save()

    def clear(self) -> None:
        """Remove all entries and persist an empty store."""
        self._data.clear()
        self._save()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        with open(self._path, encoding="utf-8") as f:
            self._data = json.load(f)

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
