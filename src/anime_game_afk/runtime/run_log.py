"""Per-run log directory with screenshot capture and retention management.

Each execution run gets a timestamped directory under logs/:
    logs/
        20260405_143022/
            run.log           <- loguru text log
            screenshots/
                001_hub_check.jpg
                002_nav_shop.jpg
                ...
        20260405_150511/
            ...

Retention: only the newest MAX_RETAINED (default 15) run directories
are kept. Older ones are deleted on startup.

Usage::

    from anime_game_afk.runtime.run_log import RunLog

    run_log = RunLog()              # creates timestamped dir
    run_log.snap(device, "hub_check")   # saves screenshot
    run_log.info("Navigated to shop")   # logs with run context
"""
from __future__ import annotations

import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np
from loguru import logger as _loguru

if TYPE_CHECKING:
    from anime_game_afk.core.device import DeviceAdapter

# Project root → logs/ directory
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LOGS_DIR = _PROJECT_ROOT / "logs"

MAX_RETAINED = 15
SCREENSHOT_QUALITY = 90
THUMBNAIL_SIZE = (800, 450)


class RunLog:
    """Manages a per-run log directory with screenshots.

    Attributes:
        run_dir: Path to this run's directory (e.g. logs/20260405_143022/).
        screenshots_dir: Path to screenshots sub-directory.
        run_id: Timestamp string identifying this run.
    """

    def __init__(
        self,
        logs_dir: Path | None = None,
        max_retained: int = MAX_RETAINED,
    ) -> None:
        self._logs_dir = logs_dir or _LOGS_DIR
        self._max_retained = max_retained
        self._snap_counter = 0

        # Create timestamped run directory
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self._logs_dir / self.run_id
        self.screenshots_dir = self.run_dir / "screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        # Set up loguru file sink for this run
        self._log_path = self.run_dir / "run.log"
        self._sink_id = _loguru.add(
            str(self._log_path),
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {message}",
            level="DEBUG",
            rotation=None,  # Single file per run
            encoding="utf-8",
        )

        # Clean up old runs
        self._cleanup_old_runs()

        _loguru.info(f"[RunLog] Run started: {self.run_id}")
        _loguru.info(f"[RunLog] Log dir: {self.run_dir}")

    # ------------------------------------------------------------------
    # Screenshot capture
    # ------------------------------------------------------------------

    def snap(
        self,
        device: "DeviceAdapter",
        label: str,
        *,
        full_size: bool = False,
    ) -> np.ndarray:
        """Capture screenshot, save to run directory, return image.

        Args:
            device: Device adapter to capture from.
            label: Descriptive label (e.g. "hub_check", "popup_buy").
                   Used in filename: 001_hub_check.jpg
            full_size: If True, save at original resolution.
                       Default False saves 800x450 thumbnail.

        Returns:
            The original full-resolution screenshot (BGR numpy array).
        """
        self._snap_counter += 1
        img = device.screenshot()

        # Build filename: 001_hub_check.jpg
        filename = f"{self._snap_counter:03d}_{label}.jpg"
        filepath = self.screenshots_dir / filename

        if full_size:
            cv2.imwrite(
                str(filepath), img,
                [cv2.IMWRITE_JPEG_QUALITY, SCREENSHOT_QUALITY],
            )
        else:
            thumb = cv2.resize(img, THUMBNAIL_SIZE)
            cv2.imwrite(
                str(filepath), thumb,
                [cv2.IMWRITE_JPEG_QUALITY, SCREENSHOT_QUALITY],
            )

        _loguru.debug(f"[RunLog] snap #{self._snap_counter}: {label} -> {filename}")
        return img

    def save_image(
        self,
        img: np.ndarray,
        label: str,
        *,
        full_size: bool = False,
    ) -> Path:
        """Save an existing image (not from device) to screenshots dir.

        Args:
            img: BGR image to save.
            label: Descriptive label for filename.
            full_size: If True, save at original size.

        Returns:
            Path to saved file.
        """
        self._snap_counter += 1
        filename = f"{self._snap_counter:03d}_{label}.jpg"
        filepath = self.screenshots_dir / filename

        if full_size:
            cv2.imwrite(
                str(filepath), img,
                [cv2.IMWRITE_JPEG_QUALITY, SCREENSHOT_QUALITY],
            )
        else:
            thumb = cv2.resize(img, THUMBNAIL_SIZE)
            cv2.imwrite(
                str(filepath), thumb,
                [cv2.IMWRITE_JPEG_QUALITY, SCREENSHOT_QUALITY],
            )

        _loguru.debug(f"[RunLog] saved: {label} -> {filename}")
        return filepath

    # ------------------------------------------------------------------
    # Logging helpers (delegate to loguru with RunLog prefix)
    # ------------------------------------------------------------------

    def info(self, msg: str) -> None:
        _loguru.opt(depth=1).info(f"[RunLog] {msg}")

    def debug(self, msg: str) -> None:
        _loguru.opt(depth=1).debug(f"[RunLog] {msg}")

    def warning(self, msg: str) -> None:
        _loguru.opt(depth=1).warning(f"[RunLog] {msg}")

    def error(self, msg: str) -> None:
        _loguru.opt(depth=1).error(f"[RunLog] {msg}")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Remove the loguru sink. Call when run is complete."""
        _loguru.info(
            f"[RunLog] Run finished: {self.run_id} "
            f"({self._snap_counter} screenshots)"
        )
        try:
            _loguru.remove(self._sink_id)
        except ValueError:
            pass  # Already removed

    @property
    def snap_count(self) -> int:
        """Number of screenshots captured so far."""
        return self._snap_counter

    # ------------------------------------------------------------------
    # Retention management
    # ------------------------------------------------------------------

    def _cleanup_old_runs(self) -> None:
        """Keep only the newest max_retained run directories."""
        if not self._logs_dir.exists():
            return

        # List all directories that look like run dirs (YYYYMMDD_HHMMSS)
        run_dirs: list[Path] = []
        for d in self._logs_dir.iterdir():
            if d.is_dir() and len(d.name) == 15 and d.name[8] == "_":
                try:
                    # Validate timestamp format
                    datetime.strptime(d.name, "%Y%m%d_%H%M%S")
                    run_dirs.append(d)
                except ValueError:
                    continue

        # Sort by name (which is chronological) descending
        run_dirs.sort(key=lambda d: d.name, reverse=True)

        # Remove excess
        excess = run_dirs[self._max_retained:]
        for old_dir in excess:
            _loguru.debug(f"[RunLog] Cleaning up old run: {old_dir.name}")
            try:
                shutil.rmtree(old_dir)
            except OSError as e:
                _loguru.warning(
                    f"[RunLog] Failed to remove {old_dir.name}: {e}"
                )
