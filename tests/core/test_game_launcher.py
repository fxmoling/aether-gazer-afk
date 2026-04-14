"""Tests for core.game_launcher — GameLauncher process management."""
import subprocess
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from anime_game_afk.core.game_launcher import GameLauncher


class TestGameLauncherIsRunning:
    """Test process detection."""

    def test_detects_running_process(self):
        """is_running returns True when tasklist finds the process."""
        launcher = GameLauncher(
            exe_path="C:/game/AetherGazer.exe",
            window_title="AetherGazer",
        )

        mock_result = MagicMock()
        mock_result.stdout = '"AetherGazer.exe","4864","Console","1","2,412,224 K"\n'

        with patch("subprocess.run", return_value=mock_result):
            assert launcher.is_running() is True

    def test_returns_false_when_not_running(self):
        """is_running returns False when process not found."""
        launcher = GameLauncher(
            exe_path="C:/game/AetherGazer.exe",
            window_title="AetherGazer",
        )

        mock_result = MagicMock()
        mock_result.stdout = 'INFO: No tasks are running which match the specified criteria.\n'

        with patch("subprocess.run", return_value=mock_result):
            assert launcher.is_running() is False

    def test_handles_timeout_gracefully(self):
        """is_running returns False on timeout."""
        launcher = GameLauncher(
            exe_path="C:/game/AetherGazer.exe",
            window_title="AetherGazer",
        )

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("tasklist", 10)):
            assert launcher.is_running() is False


class TestGameLauncherGetPid:
    """Test PID extraction."""

    def test_extracts_pid(self):
        """get_pid extracts PID from tasklist CSV output."""
        launcher = GameLauncher(
            exe_path="C:/game/AetherGazer.exe",
        )

        mock_result = MagicMock()
        mock_result.stdout = '"AetherGazer.exe","4864","Console","1","2,412,224 K"\n'

        with patch("subprocess.run", return_value=mock_result):
            pid = launcher.get_pid()

        assert pid == 4864

    def test_returns_none_when_not_running(self):
        """get_pid returns None when process not found."""
        launcher = GameLauncher(
            exe_path="C:/game/AetherGazer.exe",
        )

        mock_result = MagicMock()
        mock_result.stdout = 'INFO: No tasks are running which match the specified criteria.\n'

        with patch("subprocess.run", return_value=mock_result):
            assert launcher.get_pid() is None


class TestGameLauncherLaunch:
    """Test game launching."""

    def test_launch_calls_popen(self, tmp_path):
        """launch() calls Popen with the correct path."""
        exe = tmp_path / "AetherGazer.exe"
        exe.write_bytes(b"fake_exe")

        launcher = GameLauncher(
            exe_path=str(exe),
            window_title="AetherGazer",
        )

        mock_proc = MagicMock()
        mock_proc.pid = 12345

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            result = launcher.launch()

        assert result.pid == 12345
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args
        # Check the exe path is in the first positional argument (the command list)
        cmd_list = call_args[0][0]  # args[0] is the positional args tuple, [0] is the list
        assert str(exe) in cmd_list[0]

    def test_launch_raises_on_missing_exe(self):
        """launch() raises FileNotFoundError for nonexistent exe."""
        launcher = GameLauncher(
            exe_path="C:/nonexistent/game.exe",
        )

        try:
            launcher.launch()
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            pass


class TestGameLauncherWaitForProcess:
    """Test process waiting."""

    def test_wait_returns_true_when_found(self):
        """wait_for_process returns True when process appears."""
        launcher = GameLauncher(
            exe_path="C:/game/AetherGazer.exe",
        )

        call_count = 0
        def mock_is_running():
            nonlocal call_count
            call_count += 1
            return call_count >= 2  # Found on second check

        with patch.object(launcher, "is_running", side_effect=mock_is_running):
            with patch("time.sleep"):
                result = launcher.wait_for_process(timeout=10, poll_interval=0.01)

        assert result is True

    def test_wait_returns_false_on_timeout(self):
        """wait_for_process returns False when timeout exceeded."""
        launcher = GameLauncher(
            exe_path="C:/game/AetherGazer.exe",
        )

        # Make time.monotonic() simulate elapsed time
        start = time.monotonic()
        times = iter([start, start + 1, start + 2, start + 100])

        with patch.object(launcher, "is_running", return_value=False):
            with patch("time.sleep"):
                with patch("time.monotonic", side_effect=times):
                    result = launcher.wait_for_process(timeout=5, poll_interval=0.01)

        assert result is False


class TestGameLauncherEnsureRunning:
    """Test the convenience ensure_running method."""

    def test_returns_true_if_already_running(self):
        """ensure_running returns True immediately if process exists."""
        launcher = GameLauncher(
            exe_path="C:/game/AetherGazer.exe",
            window_title="AetherGazer",
        )

        with patch.object(launcher, "is_running", return_value=True):
            result = launcher.ensure_running(timeout=5)

        assert result is True

    def test_launches_and_waits_if_not_running(self, tmp_path):
        """ensure_running launches and waits when not running."""
        exe = tmp_path / "AetherGazer.exe"
        exe.write_bytes(b"fake")

        launcher = GameLauncher(
            exe_path=str(exe),
            window_title="AetherGazer",
        )

        with patch.object(launcher, "is_running", return_value=False):
            with patch.object(launcher, "launch", return_value=MagicMock(pid=123)):
                with patch.object(launcher, "wait_for_process", return_value=True):
                    with patch.object(launcher, "wait_for_window", return_value=True):
                        result = launcher.ensure_running(timeout=5)

        assert result is True

    def test_process_name_derived_from_path(self):
        """Process name defaults to the exe filename."""
        launcher = GameLauncher(
            exe_path="E:/shenkongzhiyan/AetherGazer/AetherGazer.exe",
        )
        assert launcher.process_name == "AetherGazer.exe"

    def test_properties(self):
        """Properties return correct values."""
        launcher = GameLauncher(
            exe_path="C:/game/test.exe",
            window_title="TestWindow",
            process_name="test.exe",
        )
        assert launcher.exe_path == Path("C:/game/test.exe")
        assert launcher.process_name == "test.exe"
