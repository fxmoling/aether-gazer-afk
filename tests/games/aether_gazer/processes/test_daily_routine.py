"""Tests for processes.daily_routine — DailyRoutine."""
import asyncio
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, patch

import numpy as np

from anime_game_afk.games.aether_gazer.processes.base import ProcessContext
from anime_game_afk.games.aether_gazer.processes.daily_routine import DailyRoutine
from anime_game_afk.games.aether_gazer.tasks_v2.base import TaskResult


@dataclass
class MockDevice:
    key_log: list = field(default_factory=list)
    click_log: list = field(default_factory=list)

    def screenshot(self) -> np.ndarray:
        return np.zeros((900, 1600, 3), dtype=np.uint8)
    def click(self, x: int, y: int) -> None:
        self.click_log.append((x, y))
    def press_key(self, vk_code: int) -> None:
        self.key_log.append(vk_code)
    def hold_key(self, vk_code: int, duration_s: float) -> None:
        pass


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _task_success():
    return AsyncMock(return_value=TaskResult(status="success"))


def _task_failed():
    return AsyncMock(return_value=TaskResult(status="failed", message="err"))


# --- DailyRoutine ---

def test_daily_routine_name_and_description():
    proc = DailyRoutine()
    assert proc.name == "daily_routine"
    assert len(proc.description) > 0


def test_daily_routine_completes_all_tasks():
    """Happy path: both mail and stamina complete successfully."""
    device = MockDevice()
    ctx = ProcessContext(device=device)

    with patch(
        "anime_game_afk.games.aether_gazer.processes.daily_routine"
        ".ReturnToHub.execute",
        _task_success(),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.daily_routine"
        ".CollectAllMail.execute",
        _task_success(),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.daily_routine"
        ".CollectAllMail.can_run",
        AsyncMock(return_value=True),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.daily_routine"
        ".ClaimFreeStamina.execute",
        _task_success(),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.daily_routine"
        ".ClaimFreeStamina.can_run",
        AsyncMock(return_value=True),
    ):
        result = _run(DailyRoutine().execute(ctx))

    assert result.status == "success"
    assert "mail" in result.data["completed"]
    assert "free_stamina" in result.data["completed"]


def test_daily_routine_skips_failed_mail():
    """If mail fails, it's not in completed list but routine continues."""
    device = MockDevice()
    ctx = ProcessContext(device=device)

    with patch(
        "anime_game_afk.games.aether_gazer.processes.daily_routine"
        ".ReturnToHub.execute",
        _task_success(),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.daily_routine"
        ".CollectAllMail.execute",
        _task_failed(),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.daily_routine"
        ".CollectAllMail.can_run",
        AsyncMock(return_value=True),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.daily_routine"
        ".ClaimFreeStamina.execute",
        _task_success(),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.daily_routine"
        ".ClaimFreeStamina.can_run",
        AsyncMock(return_value=True),
    ):
        result = _run(DailyRoutine().execute(ctx))

    assert result.status == "success"
    assert "mail" not in result.data["completed"]
    assert "free_stamina" in result.data["completed"]


def test_daily_routine_skips_stamina_if_cannot_run():
    """If stamina task can_run returns False, it's not executed."""
    device = MockDevice()
    ctx = ProcessContext(device=device)

    with patch(
        "anime_game_afk.games.aether_gazer.processes.daily_routine"
        ".ReturnToHub.execute",
        _task_success(),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.daily_routine"
        ".CollectAllMail.execute",
        _task_success(),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.daily_routine"
        ".CollectAllMail.can_run",
        AsyncMock(return_value=True),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.daily_routine"
        ".ClaimFreeStamina.can_run",
        AsyncMock(return_value=False),
    ):
        result = _run(DailyRoutine().execute(ctx))

    assert result.status == "success"
    assert "free_stamina" not in result.data["completed"]
    assert "mail" in result.data["completed"]


def test_daily_routine_returns_empty_if_all_fail():
    """If all tasks fail, completed list is empty but process still succeeds."""
    device = MockDevice()
    ctx = ProcessContext(device=device)

    with patch(
        "anime_game_afk.games.aether_gazer.processes.daily_routine"
        ".ReturnToHub.execute",
        _task_success(),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.daily_routine"
        ".CollectAllMail.execute",
        _task_failed(),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.daily_routine"
        ".CollectAllMail.can_run",
        AsyncMock(return_value=True),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.daily_routine"
        ".ClaimFreeStamina.execute",
        _task_failed(),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.daily_routine"
        ".ClaimFreeStamina.can_run",
        AsyncMock(return_value=True),
    ):
        result = _run(DailyRoutine().execute(ctx))

    assert result.status == "success"
    assert result.data["completed"] == []
