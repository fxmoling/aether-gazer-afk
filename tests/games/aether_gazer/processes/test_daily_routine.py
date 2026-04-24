"""Tests for processes.daily_routine — DailyRoutine.

DailyRoutine now runs 10 tasks. All must be mocked.
"""
import asyncio
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, patch

import numpy as np

from anime_game_afk.games.aether_gazer.processes.base import ProcessContext
from anime_game_afk.games.aether_gazer.processes.daily_routine import (
    DailyRoutine,
    _DAILY_TASKS,
)
from anime_game_afk.games.aether_gazer.tasks.base import TaskResult


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


def _task_success(**data):
    return AsyncMock(return_value=TaskResult(status="success", data=data))


def _task_failed():
    return AsyncMock(return_value=TaskResult(status="failed", message="err"))


_MOD = "anime_game_afk.games.aether_gazer.processes.daily_routine"

# All task class names that need mocking (derived from _DAILY_TASKS)
_TASK_CLASSES = [
    "SkipStartupPopups",
    "CollectAllMail",
    "BuyIntelShards",
    "ClaimDailyStaminaPacks",
    "ClaimFreeStamina",
    "MimiStationCollect",
    "GuildSupplyClaim",
    "AmusementStreetDaily",
    "JointDefenseSweep",
    "MediumSeizureCombat",
    "DailyWeeklyMissionClaim",
    "TacticsTaskClaim",
]


def _patch_all(execute_mock=None, can_run_val=True):
    """Create patches for ReturnToHub + all 7 task classes."""
    patches = [
        patch(f"{_MOD}.ReturnToHub.execute", _task_success()),
    ]
    for cls_name in _TASK_CLASSES:
        ex_mock = execute_mock or _task_success()
        patches.append(patch(f"{_MOD}.{cls_name}.execute", ex_mock))
        patches.append(
            patch(f"{_MOD}.{cls_name}.can_run", AsyncMock(return_value=can_run_val))
        )
    return patches


def _start_patches(patches):
    for p in patches:
        p.start()


def _stop_patches(patches):
    for p in patches:
        p.stop()


# --- Tests ---

def test_daily_routine_name_and_description():
    proc = DailyRoutine()
    assert proc.name == "每日任务"
    assert len(proc.description) > 0


def test_daily_routine_task_count():
    """DailyRoutine has 12 tasks (startup + 11 daily)."""
    assert len(_DAILY_TASKS) == 12


def test_daily_routine_completes_all_tasks():
    """Happy path: all 12 tasks succeed (game freshly launched)."""
    device = MockDevice()
    ctx = ProcessContext(device=device, config={"game_was_launched": True})

    patches = _patch_all()
    _start_patches(patches)
    try:
        result = _run(DailyRoutine().execute(ctx))
    finally:
        _stop_patches(patches)

    assert result.status == "success"
    assert len(result.data["completed"]) == 12
    assert len(result.data["failed"]) == 0


def test_daily_routine_handles_failures():
    """If all tasks fail, completed is empty but process still succeeds."""
    device = MockDevice()
    ctx = ProcessContext(device=device, config={"game_was_launched": True})

    patches = [
        patch(f"{_MOD}.ReturnToHub.execute", _task_success()),
    ]
    for cls_name in _TASK_CLASSES:
        patches.append(patch(f"{_MOD}.{cls_name}.execute", _task_failed()))
        patches.append(
            patch(f"{_MOD}.{cls_name}.can_run", AsyncMock(return_value=True))
        )

    _start_patches(patches)
    try:
        result = _run(DailyRoutine().execute(ctx))
    finally:
        _stop_patches(patches)

    assert result.status == "success"
    assert result.data["completed"] == []
    assert len(result.data["failed"]) == 12


def test_daily_routine_skips_if_cannot_run():
    """Tasks with can_run=False are skipped."""
    device = MockDevice()
    ctx = ProcessContext(device=device)

    patches = _patch_all(can_run_val=False)
    _start_patches(patches)
    try:
        result = _run(DailyRoutine().execute(ctx))
    finally:
        _stop_patches(patches)

    assert result.status == "success"
    # No tasks executed, no failures
    assert result.data["completed"] == []
    assert result.data["failed"] == []
