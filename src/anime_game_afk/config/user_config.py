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
    # Theme
    # ------------------------------------------------------------------

    def theme(self) -> str:
        """Return the currently selected UI theme ID."""
        return self._settings().get("theme", "cosmic-purple")

    def set_theme(self, theme_id: str) -> None:
        """Set the UI theme."""
        self._settings()["theme"] = theme_id

    # ------------------------------------------------------------------
    # Post-run action (manual mode)
    # ------------------------------------------------------------------

    def post_run_action(self) -> str:
        """What to do after manual run completes."""
        return self._settings().get("post_run_action", "nothing")

    def set_post_run_action(self, action: str) -> None:
        """Set post-run action."""
        self._settings()["post_run_action"] = action

    def auto_run_on_startup(self) -> bool:
        """Whether to auto-run the daily routine when the GUI starts."""
        return bool(self._settings().get("auto_run_on_startup", False))

    def set_auto_run_on_startup(self, enabled: bool) -> None:
        """Toggle auto-run of daily routine on GUI startup."""
        self._settings()["auto_run_on_startup"] = bool(enabled)

    # ------------------------------------------------------------------
    # Global hotkeys (game foreground scoped)
    # ------------------------------------------------------------------

    _DEFAULT_HOTKEYS = {
        "toggle_auto_battle": "Alt+1",
        "stop_all": "Alt+2",
    }

    def hotkeys(self) -> dict[str, str]:
        """Return current hotkey bindings, falling back to defaults."""
        raw = self._settings().get("hotkeys") or {}
        merged = dict(self._DEFAULT_HOTKEYS)
        for k, v in raw.items():
            if isinstance(v, str):
                merged[k] = v
        return merged

    def set_hotkey(self, action: str, combo: str) -> None:
        """Set a single hotkey binding (use empty string to disable)."""
        binds = dict(self._settings().get("hotkeys") or {})
        binds[action] = combo or ""
        self._settings()["hotkeys"] = binds

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

    # ------------------------------------------------------------------
    # Duowei (多维变量) settings
    # ------------------------------------------------------------------

    def duowei_swipe_multiplier(self, game_id: str = "aether_gazer") -> float:
        """Camera rotation multiplier for duowei 1-1 portal navigation (0.1–2.0)."""
        val = self._game(game_id).get("duowei_swipe_multiplier", 1.0)
        return max(0.1, min(2.0, float(val)))

    def set_duowei_swipe_multiplier(
        self, value: float, game_id: str = "aether_gazer",
    ) -> None:
        """Set camera rotation multiplier (clamped to 0.1–2.0)."""
        self._game(game_id)["duowei_swipe_multiplier"] = max(0.1, min(2.0, float(value)))

    # ── Force-select character on duowei character page ──
    #
    # The default character chosen by the game may be too weak to clear
    # 1-2.  We force-select 真红 (a character every player owns and that
    # matches the 真樱 + 物理 tag combination) by opening the bottom-left
    # filter, applying the configured tags, then iterating the avatar
    # grid until OCR confirms the target name in the right-side preview.
    #
    # An empty string in ``duowei_force_character`` disables the whole
    # flow and falls back to the previous "just click 下一步" behavior.

    def duowei_force_character(self, game_id: str = "aether_gazer") -> str:
        """Character name to force-select on duowei character page.

        Default: ``真红`` — owned by every account and matches the default
        ``真樱`` + ``物理`` tag filter.  Empty string disables the feature.
        """
        val = self._game(game_id).get("duowei_force_character", "真红")
        return str(val).strip() if val is not None else ""

    def set_duowei_force_character(
        self, name: str, game_id: str = "aether_gazer",
    ) -> None:
        """Set the force-selected character name (empty string disables)."""
        self._game(game_id)["duowei_force_character"] = (name or "").strip()

    def duowei_filter_tags(self, game_id: str = "aether_gazer") -> list[str]:
        """Tags to apply in the character filter dialog.

        Default: ``["真樱", "物理"]`` — narrows the roster down to a small
        set that always contains 真红.
        """
        raw = self._game(game_id).get("duowei_filter_tags", ["真樱", "物理"])
        if not isinstance(raw, list):
            return ["真樱", "物理"]
        return [str(t).strip() for t in raw if str(t).strip()]

    def set_duowei_filter_tags(
        self, tags: list[str], game_id: str = "aether_gazer",
    ) -> None:
        """Set the character filter tag list."""
        self._game(game_id)["duowei_filter_tags"] = [
            str(t).strip() for t in tags if str(t).strip()
        ]

    _DUOWEI_AVATAR_GRID_DEFAULT: dict[str, Any] = {
        # Measured 2026-05-11 from a real character page screenshot:
        # 等级80 label was at (167, 302) px on a 1600x900 capture, and
        # the avatar icon sits ~80px above the label center (≈(202, 222)).
        "x1": 0.126,       # First avatar (top-left, default-selected) center fx
        "y1": 0.247,       # First avatar center fy (label_y - 80px) / 900
        # Column spacing measured from secondary OCR landmark at (418, 302):
        "offset_x": 0.157, # (418 - 167) / 1600 ≈ 0.157
        # Row spacing measured between adjacent 等级80 labels (302 → 474):
        "offset_y": 0.191, # (474 - 302) / 900 ≈ 0.191
        "cols": 2,         # Avatars per row
        "rows": 4,         # Maximum rows to probe (must avoid 下一步 button area)
    }

    def duowei_avatar_grid(self, game_id: str = "aether_gazer") -> dict[str, Any]:
        """Avatar grid layout for force-character iteration.

        All coordinates are fractional [0.0, 1.0].  Returned dict is a
        merge of the built-in defaults and any user overrides, so missing
        keys fall back gracefully.
        """
        raw = self._game(game_id).get("duowei_avatar_grid", {})
        if not isinstance(raw, dict):
            raw = {}
        return {**self._DUOWEI_AVATAR_GRID_DEFAULT, **raw}

    def set_duowei_avatar_grid(
        self, grid: dict[str, Any], game_id: str = "aether_gazer",
    ) -> None:
        """Set the avatar grid layout (merged with defaults at read time)."""
        self._game(game_id)["duowei_avatar_grid"] = dict(grid)

    def duowei_filter_button_fallback(
        self, game_id: str = "aether_gazer",
    ) -> tuple[float, float]:
        """Fractional coord to click when OCR cannot locate the 筛选 button.

        Default: ``(0.040, 0.931)`` — bottom-left funnel icon on the
        AetherGazer duowei character selection screen.  Measured by
        E2E test 2026-05-11: this exact coord opens the filter dialog.
        Note: the funnel is an icon-only button (no text), so OCR will
        never find ``筛选`` and the fallback is the primary code path.
        """
        raw = self._game(game_id).get("duowei_filter_button_fallback", [0.040, 0.931])
        try:
            fx = float(raw[0])
            fy = float(raw[1])
        except (TypeError, ValueError, IndexError):
            fx, fy = 0.040, 0.931
        return (max(0.0, min(1.0, fx)), max(0.0, min(1.0, fy)))

    def set_duowei_filter_button_fallback(
        self, fx: float, fy: float, game_id: str = "aether_gazer",
    ) -> None:
        """Set the fallback coord for the filter button."""
        self._game(game_id)["duowei_filter_button_fallback"] = [
            max(0.0, min(1.0, float(fx))),
            max(0.0, min(1.0, float(fy))),
        ]

    # ------------------------------------------------------------------
    # Lizhan (历战轮回) settings
    # ------------------------------------------------------------------

    def lizhan_next_key(self, game_id: str = "aether_gazer") -> str:
        """Key for '挑战下一关' in 历战轮回 (default: 'J')."""
        return self._game(game_id).get("lizhan_next_key", "J")

    def set_lizhan_next_key(
        self, key: str, game_id: str = "aether_gazer",
    ) -> None:
        """Set the next-challenge key for 历战轮回."""
        self._game(game_id)["lizhan_next_key"] = key.strip().upper()

    # ------------------------------------------------------------------
    # Combat script selection
    # ------------------------------------------------------------------

    def combat_script(self, game_id: str = "aether_gazer") -> str:
        """Return the selected combat script name (default: 'default')."""
        return self._game(game_id).get("combat_script", "default")

    def set_combat_script(
        self, name: str, game_id: str = "aether_gazer",
    ) -> None:
        """Set the active combat script by name."""
        self._game(game_id)["combat_script"] = name
