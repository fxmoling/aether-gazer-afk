"""Game installation finder.

Auto-detect game executable locations using multiple strategies:
1. Running process — if the game is open, get its path directly
2. Desktop shortcuts — parse .lnk files for target paths
3. Filesystem search — scan drives for known directory/file patterns

All strategies are game-agnostic. Game-specific keywords and patterns
are passed in from config or knowledge layers.

No cv2, no maa, no vision imports. Pure system utilities.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from anime_game_afk.runtime.logger import get_logger

logger = get_logger("core.game_finder")

# Desktop paths — user desktop + public desktop (game installers often put shortcuts in Public)
_USER_DESKTOP = Path(os.path.expanduser("~/Desktop"))
_PUBLIC_DESKTOP = Path("C:/Users/Public/Desktop")
_DESKTOPS = [_USER_DESKTOP, _PUBLIC_DESKTOP]


class GameFinder:
    """Locate game installations on the local system.

    Usage::

        finder = GameFinder()
        path = finder.find_game_exe(
            exe_name="AetherGazer.exe",
            keywords=["shenkongzhiyan", "AetherGazer", "深空之眼"],
            shortcut_names=["深空之眼", "AetherGazer", "StarSavior"],
            search_drives=["C:", "D:", "E:"],
        )
        if path:
            print(f"Found: {path}")
    """

    def find_game_exe(
        self,
        exe_name: str,
        keywords: list[str] | None = None,
        shortcut_names: list[str] | None = None,
        search_drives: list[str] | None = None,
    ) -> str | None:
        """Find a game executable using all available strategies.

        Tries strategies in priority order (fastest/most reliable first):
        1. Running process
        2. Desktop shortcuts
        3. Filesystem search

        Args:
            exe_name: Name of the game executable (e.g. "AetherGazer.exe").
            keywords: Directory name keywords for filesystem search.
            shortcut_names: Possible names for desktop shortcuts (.lnk).
            search_drives: Drive letters to search (e.g. ["C:", "D:"]).

        Returns:
            Full path to the executable, or None if not found.
        """
        # Strategy 1: Check running processes
        logger.info("Strategy 1: Checking running processes for {exe}", exe=exe_name)
        path = self._find_from_running_process(exe_name)
        if path:
            logger.info("Found via running process: {path}", path=path)
            return path

        # Strategy 2: Check desktop shortcuts
        if shortcut_names:
            logger.info("Strategy 2: Checking desktop shortcuts")
            path = self._find_from_desktop_shortcuts(
                exe_name, shortcut_names
            )
            if path:
                logger.info("Found via desktop shortcut: {path}", path=path)
                return path

        # Strategy 3: Filesystem search
        if keywords and search_drives:
            logger.info("Strategy 3: Searching filesystem")
            path = self._find_from_filesystem(
                exe_name, keywords, search_drives
            )
            if path:
                logger.info("Found via filesystem search: {path}", path=path)
                return path

        logger.warning("Could not find {exe} via any strategy", exe=exe_name)
        return None

    # ------------------------------------------------------------------
    # Strategy 1: Running process
    # ------------------------------------------------------------------

    def _find_from_running_process(self, exe_name: str) -> str | None:
        """Get the executable path from a running process.

        Uses ``wmic`` to query process paths — works without psutil.
        Falls back to ``tasklist`` for existence check only.
        """
        # Try wmic first (returns full path)
        try:
            result = subprocess.run(
                [
                    "wmic", "process", "where",
                    f"name='{exe_name}'",
                    "get", "ExecutablePath",
                    "/format:csv",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if not line or line.startswith("Node"):
                    continue
                # CSV format: Node,ExecutablePath
                parts = line.split(",", 1)
                if len(parts) >= 2:
                    path = parts[1].strip()
                    if path and Path(path).exists():
                        return path
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.debug("wmic failed: {exc}", exc=str(exc))

        return None

    # ------------------------------------------------------------------
    # Strategy 2: Desktop shortcuts
    # ------------------------------------------------------------------

    def _find_from_desktop_shortcuts(
        self,
        exe_name: str,
        shortcut_names: list[str],
    ) -> str | None:
        """Parse .lnk files on user and public desktops to find the game.

        Uses PowerShell WScript.Shell COM to extract shortcut targets.

        If a shortcut target points to a directory or a different exe,
        we look for *exe_name* within that directory tree.
        """
        # Collect all .lnk files from both desktops
        candidate_lnks: list[Path] = []
        for desktop in _DESKTOPS:
            if not desktop.exists():
                continue
            try:
                for f in desktop.iterdir():
                    if not f.suffix.lower() == ".lnk":
                        continue
                    stem_lower = f.stem.lower()
                    for name in shortcut_names:
                        if name.lower() in stem_lower:
                            candidate_lnks.append(f)
                            break
            except OSError:
                continue

        if not candidate_lnks:
            logger.debug("No matching desktop shortcuts found")
            return None

        # Parse each shortcut via PowerShell
        for lnk_path in candidate_lnks:
            target = self._read_shortcut_target(lnk_path)
            if not target:
                continue

            logger.debug(
                "Shortcut {lnk} -> {target}",
                lnk=lnk_path.name,
                target=target,
            )

            # If target IS the exe we want, done
            target_path = Path(target)
            if target_path.name.lower() == exe_name.lower() and target_path.exists():
                return str(target_path)

            # If target is an exe in a related directory, search nearby
            if target_path.exists():
                search_root = (
                    target_path.parent
                    if target_path.is_file()
                    else target_path
                )
                found = self._search_directory_for_exe(
                    search_root, exe_name, max_depth=3
                )
                if found:
                    return found

        return None

    def _read_shortcut_target(self, lnk_path: Path) -> str | None:
        """Read the target path from a .lnk shortcut file.

        Uses PowerShell + WScript.Shell COM object.
        """
        try:
            # Use a PowerShell script file to avoid escaping nightmares
            ps_cmd = (
                "$sh = New-Object -ComObject WScript.Shell; "
                f"$link = $sh.CreateShortcut('{lnk_path}'); "
                "$link.TargetPath"
            )
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            target = result.stdout.strip()
            if target and not target.startswith("http"):
                return target
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.debug(
                "Failed to read shortcut {lnk}: {exc}",
                lnk=lnk_path.name,
                exc=str(exc),
            )
        return None

    # ------------------------------------------------------------------
    # Strategy 3: Filesystem search
    # ------------------------------------------------------------------

    def _find_from_filesystem(
        self,
        exe_name: str,
        keywords: list[str],
        search_drives: list[str],
    ) -> str | None:
        """Search drives for directories matching keywords, then find exe.

        Only scans up to 3 levels deep from the drive root to avoid
        extremely slow searches.
        """
        for drive in search_drives:
            drive_path = Path(drive + "/")
            if not drive_path.exists():
                continue

            logger.debug("Searching drive {drive}", drive=drive)
            found = self._scan_drive(drive_path, exe_name, keywords)
            if found:
                return found

        return None

    def _scan_drive(
        self,
        drive_root: Path,
        exe_name: str,
        keywords: list[str],
        max_depth: int = 3,
    ) -> str | None:
        """Scan a drive root for directories matching keywords.

        Uses os.scandir for performance. Skips system/hidden dirs.
        """
        # BFS with depth limit
        queue: list[tuple[Path, int]] = [(drive_root, 0)]
        keywords_lower = [k.lower() for k in keywords]

        while queue:
            current, depth = queue.pop(0)
            if depth > max_depth:
                continue

            try:
                with os.scandir(str(current)) as entries:
                    for entry in entries:
                        if not entry.is_dir(follow_symlinks=False):
                            continue

                        name_lower = entry.name.lower()

                        # Skip system directories
                        if name_lower in (
                            "windows", "programdata", "$recycle.bin",
                            "system volume information", "recovery",
                            ".git", "node_modules", "__pycache__",
                        ):
                            continue

                        # Check if directory name matches any keyword
                        for kw in keywords_lower:
                            if kw in name_lower:
                                # Found a matching directory — search for exe
                                found = self._search_directory_for_exe(
                                    Path(entry.path), exe_name, max_depth=4
                                )
                                if found:
                                    return found
                                break

                        # Continue BFS
                        if depth < max_depth:
                            queue.append((Path(entry.path), depth + 1))

            except (OSError, PermissionError):
                continue

        return None

    # ------------------------------------------------------------------
    # Shared helper
    # ------------------------------------------------------------------

    @staticmethod
    def _search_directory_for_exe(
        root: Path, exe_name: str, max_depth: int = 4
    ) -> str | None:
        """Search within a directory tree for a specific executable.

        Walks up to *max_depth* levels deep.

        Args:
            root: Directory to start searching from.
            exe_name: Name of the executable to find.
            max_depth: Maximum depth to recurse.

        Returns:
            Full path string if found, None otherwise.
        """
        exe_lower = exe_name.lower()
        queue: list[tuple[Path, int]] = [(root, 0)]

        while queue:
            current, depth = queue.pop(0)
            if depth > max_depth:
                continue

            try:
                with os.scandir(str(current)) as entries:
                    for entry in entries:
                        if entry.is_file() and entry.name.lower() == exe_lower:
                            return entry.path
                        if entry.is_dir(follow_symlinks=False):
                            if depth < max_depth:
                                queue.append((Path(entry.path), depth + 1))
            except (OSError, PermissionError):
                continue

        return None


def find_aether_gazer(
    search_drives: list[str] | None = None,
) -> dict[str, str | None]:
    """Convenience function to find AetherGazer installation.

    Returns dict with keys: 'game_exe', 'launcher'.
    """
    finder = GameFinder()
    drives = search_drives or ["C:", "D:", "E:"]

    game_exe = finder.find_game_exe(
        exe_name="AetherGazer.exe",
        keywords=["shenkongzhiyan", "AetherGazer", "深空之眼",
                  "AetherGazerLauncher", "AetherGazerLauncher_Bili"],
        shortcut_names=["深空之眼", "AetherGazer"],
        search_drives=drives,
    )

    # If we found the game exe, look for the launcher nearby
    launcher = None
    if game_exe:
        game_dir = Path(game_exe).parent
        # Launcher is typically one level up from the game exe
        launcher_candidate = game_dir.parent / "AetherGazerLauncher.exe"
        if launcher_candidate.exists():
            launcher = str(launcher_candidate)
        else:
            # Search nearby
            launcher = GameFinder._search_directory_for_exe(
                game_dir.parent, "AetherGazerLauncher.exe", max_depth=2
            )

    return {
        "game_exe": game_exe,
        "launcher": launcher,
    }
