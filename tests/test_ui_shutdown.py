"""Tests for GUI shutdown safety helpers."""
from __future__ import annotations

import threading

from anime_game_afk.ui.task_manager import PipelineDef, TaskState
from anime_game_afk.ui.task_manager import TaskManager


class _DummyJob:
    def __init__(self) -> None:
        self.close_count = 0

    def close(self) -> None:
        self.close_count += 1


class _DummyProc:
    def __init__(self) -> None:
        self.kill_count = 0
        self.wait_count = 0
        self._killed = False
        self.returncode: int | None = None
        self.stdout = []
        self.stderr = None

    def poll(self) -> int | None:
        return -9 if self._killed else None

    def kill(self) -> None:
        self.kill_count += 1
        self._killed = True
        self.returncode = -9

    def wait(self, timeout: float | None = None) -> int | None:
        self.wait_count += 1
        return self.returncode


class _DummyService:
    def __init__(self) -> None:
        self.stop_count = 0

    def stop(self) -> None:
        self.stop_count += 1


class _DummyRecorder:
    def __init__(self) -> None:
        self.stop_count = 0

    def stop(self) -> None:
        self.stop_count += 1


class _DummyWindow:
    def evaluate_js(self, _js_code: str) -> None:
        raise AssertionError("evaluate_js must not be called while exiting")


class _DummyLogger:
    def __getattr__(self, _name: str):
        def _log(*_args, **_kwargs) -> None:
            return None

        return _log


def _make_manager() -> TaskManager:
    tm = TaskManager.__new__(TaskManager)
    tm._exit_lock = threading.Lock()
    tm._exiting = False
    tm._window = _DummyWindow()
    tm._running = True
    tm._game_verified = True
    tm._resolution = "1280x720"
    tm._auto_battle_enabled = True
    tm._auto_battle_service = _DummyService()
    tm._combo_recorder = _DummyRecorder()
    tm._kill_job = _DummyJob()
    tm._process = _DummyProc()
    tm._logger = _DummyLogger()
    tm._lock = threading.Lock()
    tm._stop_requested = False
    tm._pipelines = [
        PipelineDef(
            id="daily_routine",
            name="Daily",
            description="",
            tasks=[
                TaskState(id="startup", name="Startup", description="", status="running"),
                TaskState(id="mail", name="Mail", description="", status="pending"),
            ],
        )
    ]
    return tm


def test_begin_exit_is_non_blocking_and_idempotent() -> None:
    tm = _make_manager()
    service = tm._auto_battle_service
    recorder = tm._combo_recorder
    job = tm._kill_job
    proc = tm._process

    tm.begin_exit()
    tm.begin_exit()

    assert tm._exiting is True
    assert tm._window is None
    assert tm._running is False
    assert tm._game_verified is False
    assert tm._resolution is None
    assert tm._auto_battle_enabled is False
    assert tm._auto_battle_service is None
    assert service.stop_count == 1
    assert recorder.stop_count == 1
    assert job.close_count == 1
    assert proc.kill_count == 1


def test_push_js_is_disabled_after_begin_exit() -> None:
    tm = _make_manager()

    tm.begin_exit()
    tm._push_js("window.someCallback && window.someCallback()")


def test_stop_returns_immediately_and_marks_running_tasks_stopped() -> None:
    tm = _make_manager()
    proc = tm._process

    result = tm.stop()

    assert result == {"ok": True}
    assert tm._stop_requested is True
    assert tm._running is False
    assert proc.kill_count == 1
    assert proc.wait_count == 0
    assert tm._pipelines[0].tasks[0].status == "stopped"
    assert tm._pipelines[0].tasks[1].status == "pending"


def test_reader_skips_post_actions_after_manual_stop() -> None:
    tm = _make_manager()
    tm._window = None
    tm._stop_requested = True
    tm._process.returncode = -9
    calls: list[str] = []

    tm._auto_recover_input = lambda: True
    tm._handle_scheduled_post_action = lambda _proc: calls.append("scheduled")
    tm._handle_manual_post_action = lambda: calls.append("manual")

    tm._read_worker_output()

    assert calls == []
    assert tm._stop_requested is False
