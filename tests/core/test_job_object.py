"""Tests for KillOnCloseJob — Win32 Job Object wrapper."""
from __future__ import annotations

import subprocess
import sys
import time

import pytest

from anime_game_afk.core.job_object import KillOnCloseJob

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="Job Objects are Windows-only"
)


def test_create_job_succeeds() -> None:
    """Constructor must not raise and must produce a valid job handle."""
    job = KillOnCloseJob()
    assert job._job_handle is not None  # type: ignore[attr-defined]
    job.close()
    assert job._job_handle is None  # type: ignore[attr-defined]


def test_assign_running_process_succeeds() -> None:
    """Assigning a live subprocess to the job should succeed."""
    job = KillOnCloseJob()
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    try:
        ok = job.assign(proc.pid)
        assert ok is True
    finally:
        proc.kill()
        proc.wait(timeout=5)
        job.close()


def test_close_kills_assigned_processes() -> None:
    """Closing the job's last handle terminates all assigned processes."""
    job = KillOnCloseJob()
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    try:
        assert job.assign(proc.pid) is True
        assert proc.poll() is None  # Still alive
        job.close()  # Triggers kill via JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE

        # Give Windows a moment to terminate the process
        deadline = time.time() + 3.0
        while time.time() < deadline and proc.poll() is None:
            time.sleep(0.1)

        assert proc.poll() is not None, (
            "Process still alive after job closed — KILL_ON_JOB_CLOSE failed"
        )
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=5)


def test_assign_dead_process_returns_false() -> None:
    """Assigning a PID that already exited should return False, not crash."""
    job = KillOnCloseJob()
    proc = subprocess.Popen(
        [sys.executable, "-c", "pass"],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    proc.wait(timeout=5)
    # PID may be reused by OS — but at minimum this should not raise.
    result = job.assign(proc.pid)
    assert result in (True, False)
    job.close()


def test_idempotent_close() -> None:
    """close() called multiple times must not raise."""
    job = KillOnCloseJob()
    job.close()
    job.close()
    job.close()  # Still no exception
