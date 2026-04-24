"""Persistent user configuration.

Loads from ``config/user_config.yaml`` at project root.
If the file does not exist, creates one from the built-in template.
Provides typed accessors for game-specific launch settings.

Usage::

    cfg = UserConfig.load()
    path = cfg.game_exe_path("aether_gazer")
    cfg.set_game_exe_path("aether_gazer", r"E:\\game\\AetherGazer.exe")
    cfg.save()
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml

import sys

from anime_game_afk.runtime.logger import get_logger

logger = get_logger("config.user_config")

# Resolve config directory: in frozen (PyInstaller) mode, use the exe's
# parent directory; in source mode, use the project root.
if getattr(sys, "frozen", False):
    _APP_ROOT = Path(sys.executable).resolve().parent
else:
    _APP_ROOT = Path(__file__).resolve().parent.parent.parent.parent

_CONFIG_DIR = _APP_ROOT / "config"
_USER_CONFIG_PATH = _CONFIG_DIR / "user_config.yaml"


class UserConfig:
    """Persistent user configuration backed by a YAML file.

    Stores per-game launch settings (exe paths, launch method, etc.)
    and global preferences. Auto-creates from template on first use.
    """

    def __init__(self, data: dict[str, Any], path: Path) -> None:
        self._data = data
        self._path = path

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: Path | str | None = None) -> "UserConfig":
        """Load user config from YAML file.

        If no file exists at *path*, creates one from the built-in
        template. If *path* is None, uses the default project location.

        Args:
            path: Optional override path to YAML file.

        Returns:
            Loaded UserConfig instance.
        """
        config_path = Path(path) if path else _USER_CONFIG_PATH

        if not config_path.exists():
            logger.info(
                "User config not found at {path}, creating from template",
                path=str(config_path),
            )
            config_path.parent.mkdir(parents=True, exist_ok=True)
            # Write a minimal default
            default_data = cls._default_data()
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(default_data, f, default_flow_style=False,
                          allow_unicode=True, sort_keys=False)

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        logger.info("User config loaded from {path}", path=str(config_path))
        # Log key config values for debugging
        instance = cls(data, config_path)
        game_cfg = instance._data.get("games", {}).get("aether_gazer", {})
        logger.debug("Config: games.aether_gazer = {}", game_cfg)
        logger.debug("Config: settings = {}", instance._data.get("settings", {}))
        return instance

    @staticmethod
    def _default_data() -> dict[str, Any]:
        """Return default config structure."""
        return {
            "games": {
                "aether_gazer": {
                    "launcher_path": "",
                    "game_exe_path": "",
                    "launch_method": "direct",
                    "launch_timeout": 120,
                    "popup_dismiss_max_attempts": 60,
                    "window_title": "AetherGazer",
                    "desktop_shortcut_names": [
                        "深空之眼", "AetherGazer", "StarSavior",
                    ],
                    "search_keywords": [
                        "shenkongzhiyan", "AetherGazer", "深空之眼",
                    ],
                    "combat_keybinds": {
                        "attack": "J",
                        "skill1": "U",
                        "skill2": "I",
                        "skill3": "O",
                        "ultimate": "R",
                        "dodge": "Space",
                        "qte1": "1",
                        "qte2": "2",
                    },
                },
            },
            "settings": {
                "auto_detect_games": True,
                "auto_update": True,
                "search_drives": ["C:", "D:", "E:"],
                "log_level": "INFO",
                "background_mode": False,
                "notify_on_complete": True,
            },
        }

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Write current config back to YAML file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, default_flow_style=False,
                      allow_unicode=True, sort_keys=False)
        logger.info("Config saved to {path}", path=str(self._path))
        logger.debug("Config data: {}", self._data)

    # ------------------------------------------------------------------
    # Raw access
    # ------------------------------------------------------------------

    @property
    def raw(self) -> dict[str, Any]:
        """The underlying dict (not a copy)."""
        return self._data

    @property
    def path(self) -> Path:
        """Path to the config YAML file."""
        return self._path

    # ------------------------------------------------------------------
    # Game-specific accessors
    # ------------------------------------------------------------------

    def _game(self, game_id: str) -> dict[str, Any]:
        """Get or create game config section."""
        games = self._data.setdefault("games", {})
        if game_id not in games:
            logger.debug("Creating default config section for game: {}", game_id)
        return games.setdefault(game_id, {})

    def game_exe_path(self, game_id: str) -> str:
        """Return the game executable path, or empty string."""
        return self._game(game_id).get("game_exe_path", "")

    def set_game_exe_path(self, game_id: str, path: str) -> None:
        """Set the game executable path."""
        self._game(game_id)["game_exe_path"] = path
        logger.info(
            "Set game exe path: {game}={path}",
            game=game_id, path=path,
        )

    def launcher_path(self, game_id: str) -> str:
        """Return the launcher executable path, or empty string."""
        return self._game(game_id).get("launcher_path", "")

    def set_launcher_path(self, game_id: str, path: str) -> None:
        """Set the launcher executable path."""
        self._game(game_id)["launcher_path"] = path

    def launch_method(self, game_id: str) -> str:
        """Return launch method: 'direct' or 'launcher'."""
        return self._game(game_id).get("launch_method", "direct")

    def launch_timeout(self, game_id: str) -> int:
        """Return timeout in seconds for waiting for game window."""
        return int(self._game(game_id).get("launch_timeout", 120))

    def popup_dismiss_max_attempts(self, game_id: str) -> int:
        """Return max attempts for dismissing startup popups."""
        return int(self._game(game_id).get("popup_dismiss_max_attempts", 60))

    def window_title(self, game_id: str) -> str:
        """Return the window title used to detect the game window."""
        return self._game(game_id).get("window_title", "")

    def search_keywords(self, game_id: str) -> list[str]:
        """Return filesystem search keywords for game detection."""
        return self._game(game_id).get("search_keywords", [])

    def desktop_shortcut_names(self, game_id: str) -> list[str]:
        """Return desktop shortcut names to search for."""
        return self._game(game_id).get("desktop_shortcut_names", [])

    # ------------------------------------------------------------------
    # Settings accessors
    # ------------------------------------------------------------------

    def _settings(self) -> dict[str, Any]:
        """Get or create settings section."""
        return self._data.setdefault("settings", {})

    def auto_detect_games(self) -> bool:
        """Whether to auto-detect game paths on first run."""
        return bool(self._settings().get("auto_detect_games", True))

    def search_drives(self) -> list[str]:
        """Drives to search for game installations."""
        return self._settings().get("search_drives", ["C:", "D:", "E:"])

    def log_level(self) -> str:
        """Return configured log level."""
        return self._settings().get("log_level", "INFO")

    def auto_update(self) -> bool:
        """Whether to check for updates on startup."""
        return bool(self._settings().get("auto_update", True))

    def set_auto_update(self, enabled: bool) -> None:
        """Enable or disable automatic update checks."""
        self._settings()["auto_update"] = enabled

    def background_mode(self) -> bool:
        """Whether to run the game on a hidden virtual desktop."""
        return bool(self._settings().get("background_mode", False))

    def notify_on_complete(self) -> bool:
        """Whether to show a toast notification when tasks finish."""
        return bool(self._settings().get("notify_on_complete", True))

    def set_notify_on_complete(self, enabled: bool) -> None:
        """Enable or disable completion notifications."""
        self._settings()["notify_on_complete"] = enabled

    # ------------------------------------------------------------------
    # Combat keybinds
    # ------------------------------------------------------------------

    _DEFAULT_KEYBINDS = {
        "attack": "J", "skill1": "U", "skill2": "I",
        "skill3": "O", "ultimate": "R", "dodge": "Space",
        "qte1": "1", "qte2": "2",
    }

    def combat_keybinds(self, game_id: str = "aether_gazer") -> dict[str, str]:
        """Return combat keybind mapping {role: key_letter}."""
        game = self._game(game_id)
        saved = game.get("combat_keybinds", {})
        # Merge with defaults for any missing keys
        return {**self._DEFAULT_KEYBINDS, **saved}

    def set_combat_keybinds(
        self, binds: dict[str, str], game_id: str = "aether_gazer",
    ) -> None:
        """Save combat keybind mapping."""
        self._game(game_id)["combat_keybinds"] = binds
