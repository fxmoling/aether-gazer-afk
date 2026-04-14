"""Tests for config.user_config — UserConfig load/save/accessors."""
import os
import tempfile
from pathlib import Path

import yaml

from anime_game_afk.config.user_config import UserConfig


class TestUserConfigLoad:
    """Test UserConfig.load() factory."""

    def test_load_creates_file_if_missing(self, tmp_path):
        """When config file doesn't exist, load() creates it."""
        cfg_path = tmp_path / "user_config.yaml"
        assert not cfg_path.exists()

        cfg = UserConfig.load(cfg_path)
        assert cfg_path.exists()
        assert cfg.raw is not None

    def test_load_preserves_existing_file(self, tmp_path):
        """When config file exists, load() reads it without overwriting."""
        cfg_path = tmp_path / "user_config.yaml"
        data = {"games": {"test_game": {"game_exe_path": "/test/path.exe"}}}
        with open(cfg_path, "w") as f:
            yaml.dump(data, f)

        cfg = UserConfig.load(cfg_path)
        assert cfg.game_exe_path("test_game") == "/test/path.exe"

    def test_load_handles_empty_file(self, tmp_path):
        """Empty YAML file loads as empty dict."""
        cfg_path = tmp_path / "user_config.yaml"
        cfg_path.write_text("")

        cfg = UserConfig.load(cfg_path)
        assert cfg.raw == {}

    def test_default_data_has_aether_gazer(self):
        """Default config includes aether_gazer game entry."""
        data = UserConfig._default_data()
        assert "aether_gazer" in data["games"]
        assert data["games"]["aether_gazer"]["window_title"] == "AetherGazer"


class TestUserConfigSave:
    """Test UserConfig.save()."""

    def test_save_writes_yaml(self, tmp_path):
        """save() writes data back to YAML file."""
        cfg_path = tmp_path / "user_config.yaml"
        cfg = UserConfig.load(cfg_path)
        cfg.set_game_exe_path("aether_gazer", "E:/game/test.exe")
        cfg.save()

        # Re-load and verify
        cfg2 = UserConfig.load(cfg_path)
        assert cfg2.game_exe_path("aether_gazer") == "E:/game/test.exe"

    def test_save_creates_parent_dirs(self, tmp_path):
        """save() creates parent directories if needed."""
        cfg_path = tmp_path / "nested" / "dir" / "user_config.yaml"
        cfg = UserConfig({"test": True}, cfg_path)
        cfg.save()
        assert cfg_path.exists()


class TestGameAccessors:
    """Test per-game config accessors."""

    def test_game_exe_path_default_empty(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        # Default template has empty string
        assert cfg.game_exe_path("aether_gazer") == ""

    def test_set_game_exe_path(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        cfg.set_game_exe_path("aether_gazer", "C:/game.exe")
        assert cfg.game_exe_path("aether_gazer") == "C:/game.exe"

    def test_launcher_path_default_empty(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        assert cfg.launcher_path("aether_gazer") == ""

    def test_set_launcher_path(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        cfg.set_launcher_path("aether_gazer", "C:/launcher.exe")
        assert cfg.launcher_path("aether_gazer") == "C:/launcher.exe"

    def test_launch_method_default_direct(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        assert cfg.launch_method("aether_gazer") == "direct"

    def test_launch_timeout_default(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        assert cfg.launch_timeout("aether_gazer") == 120

    def test_popup_dismiss_max_attempts_default(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        assert cfg.popup_dismiss_max_attempts("aether_gazer") == 60

    def test_window_title_default(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        assert cfg.window_title("aether_gazer") == "AetherGazer"

    def test_search_keywords(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        kw = cfg.search_keywords("aether_gazer")
        assert "AetherGazer" in kw

    def test_desktop_shortcut_names(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        names = cfg.desktop_shortcut_names("aether_gazer")
        assert "深空之眼" in names

    def test_unknown_game_returns_defaults(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        assert cfg.game_exe_path("unknown_game") == ""
        assert cfg.launch_method("unknown_game") == "direct"
        assert cfg.launch_timeout("unknown_game") == 120


class TestSettingsAccessors:
    """Test global settings accessors."""

    def test_auto_detect_games_default_true(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        assert cfg.auto_detect_games() is True

    def test_search_drives_default(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        drives = cfg.search_drives()
        assert "C:" in drives
        assert "D:" in drives

    def test_log_level_default(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        assert cfg.log_level() == "INFO"

    def test_path_property(self, tmp_path):
        cfg_path = tmp_path / "cfg.yaml"
        cfg = UserConfig.load(cfg_path)
        assert cfg.path == cfg_path
