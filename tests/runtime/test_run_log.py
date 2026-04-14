"""Tests for runtime.run_log — RunLog with screenshots and retention."""
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

from anime_game_afk.runtime.run_log import RunLog


def _make_run_log(tmp_dir: Path, max_retained: int = 15) -> RunLog:
    """Create a RunLog that writes to a temporary directory."""
    return RunLog(logs_dir=tmp_dir, max_retained=max_retained)


def test_run_log_creates_directory():
    """RunLog creates timestamped directory on init."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        rl = _make_run_log(tmp_path)
        try:
            assert rl.run_dir.exists()
            assert rl.screenshots_dir.exists()
            assert (rl.run_dir / "run.log").exists()
        finally:
            rl.close()


def test_run_log_run_id_format():
    """run_id follows YYYYMMDD_HHMMSS format."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        rl = _make_run_log(tmp_path)
        try:
            # Should not raise
            datetime.strptime(rl.run_id, "%Y%m%d_%H%M%S")
            assert len(rl.run_id) == 15
        finally:
            rl.close()


def test_snap_saves_screenshot():
    """snap() saves a JPEG to the screenshots directory."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        rl = _make_run_log(tmp_path)
        try:
            # Mock device
            device = MagicMock()
            device.screenshot.return_value = np.zeros(
                (900, 1600, 3), dtype=np.uint8
            )

            img = rl.snap(device, "test_shot")
            assert img.shape == (900, 1600, 3)
            assert rl.snap_count == 1

            # Check file exists
            files = list(rl.screenshots_dir.glob("*.jpg"))
            assert len(files) == 1
            assert "001_test_shot.jpg" in files[0].name
        finally:
            rl.close()


def test_snap_counter_increments():
    """snap() counter increments with each call."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        rl = _make_run_log(tmp_path)
        try:
            device = MagicMock()
            device.screenshot.return_value = np.zeros(
                (900, 1600, 3), dtype=np.uint8
            )

            rl.snap(device, "first")
            rl.snap(device, "second")
            rl.snap(device, "third")
            assert rl.snap_count == 3

            files = sorted(rl.screenshots_dir.glob("*.jpg"))
            assert len(files) == 3
            assert "001_first.jpg" in files[0].name
            assert "002_second.jpg" in files[1].name
            assert "003_third.jpg" in files[2].name
        finally:
            rl.close()


def test_save_image():
    """save_image() saves an existing image (not from device)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        rl = _make_run_log(tmp_path)
        try:
            img = np.zeros((900, 1600, 3), dtype=np.uint8)
            path = rl.save_image(img, "saved_img")
            assert path.exists()
            assert "001_saved_img.jpg" in path.name
        finally:
            rl.close()


def test_retention_cleanup():
    """Old run directories are cleaned up beyond max_retained."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Create 5 fake old run directories
        for i in range(5):
            fake_dir = tmp_path / f"20260401_10000{i}"
            fake_dir.mkdir(parents=True)
            (fake_dir / "run.log").write_text("fake")

        # Create new RunLog with max_retained=3
        rl = _make_run_log(tmp_path, max_retained=3)
        try:
            # Should have kept only newest 3 + the new one = 4 total,
            # but max_retained=3 means keep 3 total (including new one)
            run_dirs = [
                d for d in tmp_path.iterdir()
                if d.is_dir() and len(d.name) == 15
            ]
            assert len(run_dirs) <= 4  # 3 retained + 1 new
        finally:
            rl.close()


def test_close_removes_sink():
    """close() does not raise even if called twice."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        rl = _make_run_log(tmp_path)
        rl.close()
        # Second close should not raise
        rl.close()
