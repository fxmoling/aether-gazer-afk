"""Configuration store.

Load from dict or YAML file. Typed access with dot-separated key paths
and optional defaults.

Example::

    cfg = ConfigStore.from_yaml("config/settings.yaml")
    width = cfg.get("game.resolution.width", 1600)
    cfg.set("game.resolution.width", 1920)
    assert cfg.has("game.resolution.width")
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


# Sentinel used internally so callers can store None as a valid value.
_SENTINEL = object()


class ConfigStore:
    """Hierarchical configuration with dot-path access.

    Keys are dot-separated strings that map to a nested dict tree.
    Any level of nesting is supported; intermediate dicts are created
    automatically when ``set()`` is called.
    """

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data: dict[str, Any] = data or {}

    # ------------------------------------------------------------------
    # Factory class methods
    # ------------------------------------------------------------------

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ConfigStore":
        """Load configuration from a YAML file.

        Args:
            path: Path to the YAML file (str or Path).

        Returns:
            A new ConfigStore populated with the file's contents.

        Raises:
            FileNotFoundError: If *path* does not exist.
            yaml.YAMLError: If the file contains invalid YAML.
        """
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConfigStore":
        """Create a ConfigStore from a plain dictionary.

        The dict is used directly (not deep-copied), so mutations via
        ``set()`` will be reflected in the original dict.
        """
        return cls(data)

    # ------------------------------------------------------------------
    # Access methods
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value at *key*, or *default* if the path is absent.

        Args:
            key: Dot-separated key path, e.g. ``"game.resolution.width"``.
            default: Value to return when the path does not exist.

        Example::

            cfg = ConfigStore.from_dict({"game": {"fps": 60}})
            cfg.get("game.fps")           # 60
            cfg.get("game.vsync", False)  # False  (missing → default)
        """
        parts = key.split(".")
        current: Any = self._data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

    def set(self, key: str, value: Any) -> None:
        """Set the value at *key*, creating intermediate dicts as needed.

        Args:
            key: Dot-separated key path, e.g. ``"game.resolution.width"``.
            value: Value to store.

        Example::

            cfg = ConfigStore({})
            cfg.set("game.resolution.width", 1920)
            # cfg._data == {"game": {"resolution": {"width": 1920}}}
        """
        parts = key.split(".")
        current: Any = self._data
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def has(self, key: str) -> bool:
        """Return True if *key* exists (even when its value is None).

        Example::

            cfg = ConfigStore.from_dict({"a": {"b": None}})
            cfg.has("a.b")  # True
            cfg.has("a.c")  # False
        """
        return self.get(key, _SENTINEL) is not _SENTINEL

    # ------------------------------------------------------------------
    # Raw access
    # ------------------------------------------------------------------

    @property
    def raw(self) -> dict[str, Any]:
        """The underlying dict (not a copy — modify with care)."""
        return self._data
