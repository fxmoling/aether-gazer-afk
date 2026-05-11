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


class TestDuoweiForceCharacter:
    """Test the duowei force-character config accessors."""

    def test_force_character_default_zhenhong(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        assert cfg.duowei_force_character() == "真红"

    def test_set_force_character_strips_whitespace(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        cfg.set_duowei_force_character("  钦努克  ")
        assert cfg.duowei_force_character() == "钦努克"

    def test_set_force_character_empty_disables(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        cfg.set_duowei_force_character("")
        assert cfg.duowei_force_character() == ""

    def test_filter_tags_default(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        assert cfg.duowei_filter_tags() == ["真樱", "物理"]

    def test_set_filter_tags(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        cfg.set_duowei_filter_tags(["朱雀", "雷电"])
        assert cfg.duowei_filter_tags() == ["朱雀", "雷电"]

    def test_set_filter_tags_strips_empty_entries(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        cfg.set_duowei_filter_tags(["真樱", "  ", "物理", ""])
        assert cfg.duowei_filter_tags() == ["真樱", "物理"]

    def test_filter_tags_invalid_type_returns_default(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        cfg._game("aether_gazer")["duowei_filter_tags"] = "not a list"
        assert cfg.duowei_filter_tags() == ["真樱", "物理"]

    def test_avatar_grid_defaults(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        grid = cfg.duowei_avatar_grid()
        assert grid["cols"] == 2
        assert grid["rows"] == 4
        # Measured E2E values (2026-05-11):
        assert grid["x1"] == 0.126
        assert grid["y1"] == 0.247
        assert grid["offset_x"] == 0.157
        assert grid["offset_y"] == 0.191

    def test_avatar_grid_user_overrides_merge_with_defaults(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        cfg.set_duowei_avatar_grid({"x1": 0.20, "rows": 3})
        grid = cfg.duowei_avatar_grid()
        assert grid["x1"] == 0.20
        assert grid["rows"] == 3
        # Other fields fall back to (measured) defaults
        assert grid["cols"] == 2
        assert grid["offset_x"] == 0.157

    def test_avatar_grid_invalid_type_returns_defaults(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        cfg._game("aether_gazer")["duowei_avatar_grid"] = "garbage"
        grid = cfg.duowei_avatar_grid()
        assert grid["cols"] == 2
        assert grid["rows"] == 4

    def test_filter_button_fallback_default(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        fx, fy = cfg.duowei_filter_button_fallback()
        # Measured E2E (2026-05-11): exact funnel-button center
        assert fx == 0.040
        assert fy == 0.931

    def test_set_filter_button_fallback_clamps(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        cfg.set_duowei_filter_button_fallback(1.5, -0.3)
        fx, fy = cfg.duowei_filter_button_fallback()
        assert fx == 1.0
        assert fy == 0.0

    def test_filter_button_fallback_invalid_returns_default(self, tmp_path):
        cfg = UserConfig.load(tmp_path / "cfg.yaml")
        cfg._game("aether_gazer")["duowei_filter_button_fallback"] = "broken"
        fx, fy = cfg.duowei_filter_button_fallback()
        assert fx == 0.040
        assert fy == 0.931

    def test_force_character_round_trip_through_yaml(self, tmp_path):
        cfg_path = tmp_path / "cfg.yaml"
        cfg = UserConfig.load(cfg_path)
        cfg.set_duowei_force_character("曙光")
        cfg.set_duowei_filter_tags(["公会", "光明"])
        cfg.set_duowei_avatar_grid({"x1": 0.15, "rows": 5})
        cfg.set_duowei_filter_button_fallback(0.07, 0.88)
        cfg.save()

        cfg2 = UserConfig.load(cfg_path)
        assert cfg2.duowei_force_character() == "曙光"
        assert cfg2.duowei_filter_tags() == ["公会", "光明"]
        grid = cfg2.duowei_avatar_grid()
        assert grid["x1"] == 0.15
        assert grid["rows"] == 5
        fx, fy = cfg2.duowei_filter_button_fallback()
        assert fx == 0.07
        assert fy == 0.88
