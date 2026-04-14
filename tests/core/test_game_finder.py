"""Tests for core.game_finder — GameFinder auto-detection."""
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

from anime_game_afk.core.game_finder import GameFinder, find_aether_gazer


class TestGameFinderRunningProcess:
    """Test Strategy 1: detect game from running process."""

    def test_finds_running_process(self):
        """When wmic returns the exe path, it's returned."""
        finder = GameFinder()
        wmic_output = "Node,ExecutablePath\nHOSTNAME,E:\\game\\AetherGazer.exe\n"

        mock_result = MagicMock()
        mock_result.stdout = wmic_output

        with patch("subprocess.run", return_value=mock_result):
            with patch.object(Path, "exists", return_value=True):
                result = finder._find_from_running_process("AetherGazer.exe")

        assert result == "E:\\game\\AetherGazer.exe"

    def test_returns_none_when_not_running(self):
        """When wmic returns empty output, returns None."""
        finder = GameFinder()
        mock_result = MagicMock()
        mock_result.stdout = "Node,ExecutablePath\n"

        with patch("subprocess.run", return_value=mock_result):
            result = finder._find_from_running_process("AetherGazer.exe")

        assert result is None

    def test_handles_timeout(self):
        """When wmic times out, returns None gracefully."""
        finder = GameFinder()

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("wmic", 10)):
            result = finder._find_from_running_process("AetherGazer.exe")

        assert result is None


class TestGameFinderDesktopShortcuts:
    """Test Strategy 2: detect game from desktop shortcuts."""

    def test_finds_from_shortcut(self, tmp_path):
        """When shortcut points to game dir, finds the exe."""
        finder = GameFinder()

        # Create fake shortcut file
        lnk = tmp_path / "AetherGazer.lnk"
        lnk.write_bytes(b"fake")

        # Create fake game directory with launcher and exe
        game_dir = tmp_path / "AetherGazer"
        game_dir.mkdir()
        fake_launcher = game_dir / "some_launcher.exe"
        fake_launcher.write_bytes(b"launcher")
        (game_dir / "AetherGazer.exe").write_bytes(b"exe")

        with patch(
            "anime_game_afk.core.game_finder._DESKTOP", tmp_path
        ):
            with patch.object(
                finder, "_read_shortcut_target",
                return_value=str(fake_launcher),
            ):
                with patch.object(
                    finder, "_search_directory_for_exe",
                    return_value=str(game_dir / "AetherGazer.exe"),
                ):
                    result = finder._find_from_desktop_shortcuts(
                        "AetherGazer.exe",
                        ["AetherGazer", "深空之眼"],
                    )

        assert result is not None
        assert "AetherGazer.exe" in result

    def test_returns_none_no_matching_shortcuts(self, tmp_path):
        """When no shortcuts match names, returns None."""
        finder = GameFinder()
        (tmp_path / "Unrelated.lnk").write_bytes(b"fake")

        with patch("anime_game_afk.core.game_finder._DESKTOP", tmp_path):
            result = finder._find_from_desktop_shortcuts(
                "AetherGazer.exe",
                ["AetherGazer", "深空之眼"],
            )

        assert result is None


class TestGameFinderFilesystem:
    """Test Strategy 3: detect game from filesystem search."""

    def test_search_directory_for_exe(self, tmp_path):
        """_search_directory_for_exe finds exe within tree."""
        # Create nested structure
        sub = tmp_path / "AetherGazerLauncher" / "AetherGazer"
        sub.mkdir(parents=True)
        (sub / "AetherGazer.exe").write_bytes(b"exe")

        result = GameFinder._search_directory_for_exe(
            tmp_path, "AetherGazer.exe", max_depth=4
        )

        assert result is not None
        assert "AetherGazer.exe" in result

    def test_search_directory_for_exe_not_found(self, tmp_path):
        """Returns None when exe doesn't exist."""
        (tmp_path / "empty_dir").mkdir()

        result = GameFinder._search_directory_for_exe(
            tmp_path, "AetherGazer.exe", max_depth=4
        )

        assert result is None

    def test_search_directory_respects_max_depth(self, tmp_path):
        """Doesn't find exe beyond max_depth."""
        deep = tmp_path / "a" / "b" / "c" / "d" / "e"
        deep.mkdir(parents=True)
        (deep / "AetherGazer.exe").write_bytes(b"exe")

        result = GameFinder._search_directory_for_exe(
            tmp_path, "AetherGazer.exe", max_depth=2
        )

        assert result is None

    def test_find_game_exe_uses_all_strategies(self):
        """find_game_exe tries all strategies in order."""
        finder = GameFinder()

        with patch.object(finder, "_find_from_running_process", return_value=None):
            with patch.object(finder, "_find_from_desktop_shortcuts", return_value=None):
                with patch.object(finder, "_find_from_filesystem", return_value="/found.exe"):
                    result = finder.find_game_exe(
                        "Game.exe",
                        keywords=["game"],
                        shortcut_names=["Game"],
                        search_drives=["C:"],
                    )

        assert result == "/found.exe"

    def test_find_game_exe_returns_first_hit(self):
        """find_game_exe stops at the first successful strategy."""
        finder = GameFinder()

        with patch.object(
            finder, "_find_from_running_process",
            return_value="/running.exe"
        ):
            result = finder.find_game_exe(
                "Game.exe",
                keywords=["game"],
                shortcut_names=["Game"],
                search_drives=["C:"],
            )

        assert result == "/running.exe"

    def test_find_game_exe_returns_none_when_all_fail(self):
        """Returns None when no strategy finds the game."""
        finder = GameFinder()

        with patch.object(finder, "_find_from_running_process", return_value=None):
            with patch.object(finder, "_find_from_desktop_shortcuts", return_value=None):
                with patch.object(finder, "_find_from_filesystem", return_value=None):
                    result = finder.find_game_exe(
                        "Game.exe",
                        keywords=["game"],
                        shortcut_names=["Game"],
                        search_drives=["C:"],
                    )

        assert result is None


class TestFindAetherGazer:
    """Test convenience function find_aether_gazer."""

    def test_returns_dict_with_keys(self):
        """find_aether_gazer returns dict with game_exe and launcher."""
        with patch.object(
            GameFinder, "find_game_exe", return_value=None
        ):
            result = find_aether_gazer(search_drives=["Z:"])

        assert "game_exe" in result
        assert "launcher" in result

    def test_finds_launcher_near_game(self, tmp_path):
        """When game exe is found, looks for launcher nearby."""
        # Create directory structure like the real installation
        launcher_dir = tmp_path / "AetherGazerLauncher"
        launcher_dir.mkdir()
        (launcher_dir / "AetherGazerLauncher.exe").write_bytes(b"exe")
        game_dir = launcher_dir / "AetherGazer"
        game_dir.mkdir()
        game_exe = game_dir / "AetherGazer.exe"
        game_exe.write_bytes(b"exe")

        with patch.object(
            GameFinder, "find_game_exe",
            return_value=str(game_exe),
        ):
            result = find_aether_gazer()

        assert result["game_exe"] == str(game_exe)
        assert result["launcher"] is not None
        assert "AetherGazerLauncher.exe" in result["launcher"]
