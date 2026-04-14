"""Game process launcher.

Start a game executable and wait for its window to appear.
Handles process lifecycle: check if running, launch, wait for window.

No cv2, no maa, no vision imports. Pure system utilities.
Uses subprocess + tasklist/wmic — no psutil dependency.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from anime_game_afk.core.errors import GameNotRunningError
from anime_game_afk.runtime.logger import get_logger

logger = get_logger("core.game_launcher")


class GameLauncher:
    """Launch a game process and wait for it to be ready.

    Usage::

        launcher = GameLauncher(
            exe_path=r"E:\\game\\AetherGazer.exe",
            window_title="AetherGazer",
        )

        if not launcher.is_running():
            launcher.launch()
            launcher.wait_for_window(timeout=120)
    """

    def __init__(
        self,
        exe_path: str,
        window_title: str = "",
        process_name: str = "",
    ) -> None:
        """Initialize the launcher.

        Args:
            exe_path: Full path to the game executable.
            window_title: Window title to look for (for wait_for_window).
            process_name: Process name to check (default: derived from exe_path).
        """
        self._exe_path = Path(exe_path)
        self._window_title = window_title
        self._process_name = process_name or self._exe_path.name

    @property
    def exe_path(self) -> Path:
        """Path to the game executable."""
        return self._exe_path

    @property
    def process_name(self) -> str:
        """Process name for tasklist checks."""
        return self._process_name

    # ------------------------------------------------------------------
    # Process detection
    # ------------------------------------------------------------------

    def is_running(self) -> bool:
        """Check if the game process is currently running.

        Uses ``tasklist`` with a process name filter.
        """
        try:
            result = subprocess.run(
                [
                    "tasklist", "/FI",
                    f"IMAGENAME eq {self._process_name}",
                    "/FO", "CSV", "/NH",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            # tasklist returns CSV lines like "name","pid","session","num","mem"
            # If no match, it outputs "INFO: No tasks are running..."
            output = result.stdout.strip()
            return (
                self._process_name.lower() in output.lower()
                and "INFO:" not in output
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.warning(
                "Failed to check process status: {exc}", exc=str(exc)
            )
            return False

    def get_pid(self) -> int | None:
        """Return the PID of the running game process, or None."""
        try:
            result = subprocess.run(
                [
                    "tasklist", "/FI",
                    f"IMAGENAME eq {self._process_name}",
                    "/FO", "CSV", "/NH",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if not line or "INFO:" in line:
                    continue
                # Parse CSV: "name","pid","session","num","mem"
                parts = line.replace('"', "").split(",")
                if len(parts) >= 2 and parts[0].lower() == self._process_name.lower():
                    try:
                        return int(parts[1])
                    except ValueError:
                        continue
        except (subprocess.TimeoutExpired, OSError):
            pass
        return None

    # ------------------------------------------------------------------
    # Launch
    # ------------------------------------------------------------------

    def launch(self) -> subprocess.Popen:
        """Start the game process.

        Returns:
            The Popen object for the launched process.

        Raises:
            FileNotFoundError: If the exe does not exist.
            OSError: If the process could not be started.
        """
        if not self._exe_path.exists():
            raise FileNotFoundError(
                f"Game executable not found: {self._exe_path}"
            )

        logger.info(
            "Launching game: {exe}", exe=str(self._exe_path)
        )

        # Launch as a detached process so it survives our script ending
        proc = subprocess.Popen(
            [str(self._exe_path)],
            cwd=str(self._exe_path.parent),
            creationflags=(
                subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.DETACHED_PROCESS
            ),
            close_fds=True,
        )

        logger.info(
            "Game process started: pid={pid}", pid=proc.pid
        )
        return proc

    # ------------------------------------------------------------------
    # Wait
    # ------------------------------------------------------------------

    def wait_for_process(
        self,
        timeout: float = 60,
        poll_interval: float = 2.0,
    ) -> bool:
        """Wait for the game process to appear in the task list.

        Args:
            timeout: Maximum wait time in seconds.
            poll_interval: Seconds between checks.

        Returns:
            True if the process appeared before timeout, False otherwise.
        """
        logger.info(
            "Waiting for process {name} (timeout={timeout}s)",
            name=self._process_name,
            timeout=timeout,
        )

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.is_running():
                logger.info(
                    "Process {name} is now running",
                    name=self._process_name,
                )
                return True
            time.sleep(poll_interval)

        logger.warning(
            "Process {name} did not appear within {timeout}s",
            name=self._process_name,
            timeout=timeout,
        )
        return False

    def wait_for_window(
        self,
        timeout: float = 120,
        poll_interval: float = 3.0,
    ) -> bool:
        """Wait for the game window to appear.

        Uses MaaFramework's Toolkit.find_desktop_windows() to detect
        the window by title. This is more reliable than tasklist because
        it waits for the window to actually be created (not just the process).

        Args:
            timeout: Maximum wait time in seconds.
            poll_interval: Seconds between checks.

        Returns:
            True if window appeared, False if timed out.
        """
        logger.info(
            "Waiting for window '{title}' (timeout={timeout}s)",
            title=self._window_title,
            timeout=timeout,
        )

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._find_window():
                elapsed = timeout - (deadline - time.monotonic())
                logger.info(
                    "Window '{title}' found after {elapsed:.1f}s",
                    title=self._window_title,
                    elapsed=elapsed,
                )
                return True
            time.sleep(poll_interval)

        logger.warning(
            "Window '{title}' did not appear within {timeout}s",
            title=self._window_title,
            timeout=timeout,
        )
        return False

    def _find_window(self) -> bool:
        """Check if the game window exists using MaaFramework Toolkit.

        Uses exact match or Unity window class to avoid false positives
        from our own tool windows containing similar title substrings.
        """
        try:
            from maa.toolkit import Toolkit
            windows = Toolkit.find_desktop_windows()
            # Exact match first
            for w in windows:
                if w.window_name == self._window_title:
                    return True
            # Substring match but only Unity windows
            for w in windows:
                if (self._window_title in w.window_name
                        and w.class_name == "UnityWndClass"):
                    return True
        except Exception:
            # Fallback: check if process is running (weaker signal)
            return self.is_running()
        return False

    # ------------------------------------------------------------------
    # Convenience: ensure running
    # ------------------------------------------------------------------

    def ensure_running(
        self,
        timeout: float = 120,
    ) -> bool:
        """Ensure the game is running. Launch if needed, wait for window.

        Args:
            timeout: Maximum time to wait for the game to be ready.

        Returns:
            True if game is running and window is available.
        """
        if self.is_running():
            logger.info(
                "Game already running: {name}", name=self._process_name
            )
            return True

        logger.info("Game not running, launching...")
        try:
            self.launch()
        except (FileNotFoundError, OSError) as exc:
            logger.error("Failed to launch game: {exc}", exc=str(exc))
            return False

        # Wait for process first, then window
        if not self.wait_for_process(timeout=30):
            logger.error("Game process did not start")
            return False

        if self._window_title:
            return self.wait_for_window(timeout=timeout)

        return True
