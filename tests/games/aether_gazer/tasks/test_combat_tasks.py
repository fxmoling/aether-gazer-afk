"""Tests for tasks.combat_tasks -- CombatStateMachine, ClearSingleStage.

Updated to match the Op/Check refactoring: CombatStateMachine now uses
DetectGameStateCheck (with .evaluate() returning CheckResult) instead of
DetectGameStateOp (with .run() returning OpResult).

Mock strategy: patch machine._detect.evaluate to return CheckResult
with the desired GameState.
"""
import asyncio
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np

from anime_game_afk.games.aether_gazer.checks.base import CheckResult
from anime_game_afk.games.aether_gazer.ops.base import GameState, OpResult
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext, TaskResult
from anime_game_afk.games.aether_gazer.tasks.combat_tasks import (
    ClearSingleStage,
    CombatStateMachine,
)
from anime_game_afk.games.aether_gazer.knowledge.keys import (
    VK_ENTER,
    VK_ESCAPE,
    VK_SPACE,
)


@dataclass
class MockDevice:
    click_log: list = field(default_factory=list)
    key_log: list = field(default_factory=list)
    hold_log: list = field(default_factory=list)

    def screenshot(self) -> np.ndarray:
        return np.zeros((900, 1600, 3), dtype=np.uint8)
    def click(self, x: int, y: int) -> None:
        self.click_log.append((x, y))
    def press_key(self, vk_code: int) -> None:
        self.key_log.append(vk_code)
    def hold_key(self, vk_code: int, duration_s: float) -> None:
        self.hold_log.append((vk_code, duration_s))


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_detect_mock(states: list[GameState]):
    """Create an AsyncMock that returns successive GameState values as CheckResults.

    DetectGameStateCheck.evaluate() returns CheckResult with
    data={"state": GameState, "confidence": float}.
    """
    results = [
        CheckResult(
            passed=(s != GameState.UNKNOWN),
            data={"state": s, "confidence": 0.9},
            message=f"state={s.value}",
        )
        for s in states
    ]
    mock = AsyncMock(side_effect=results)
    return mock


# --- CombatStateMachine ---

def test_combat_state_machine_exits_on_stage_map():
    """STAGE_MAP state causes immediate success return."""
    device = MockDevice()
    ctx = TaskContext(device=device)
    machine = CombatStateMachine()

    with patch.object(
        machine._detect, "evaluate",
        _make_detect_mock([GameState.STAGE_MAP])
    ):
        result = _run(machine.execute(ctx))

    assert result.status == "success"


def test_combat_state_machine_exits_on_mission_failed():
    """MISSION_FAILED state causes immediate failure return."""
    device = MockDevice()
    ctx = TaskContext(device=device)
    machine = CombatStateMachine()

    with patch.object(
        machine._detect, "evaluate",
        _make_detect_mock([GameState.MISSION_FAILED])
    ):
        result = _run(machine.execute(ctx))

    assert result.status == "failed"
    assert "Mission failed" in result.message


def test_combat_state_machine_battle_then_stage_map():
    """Handles BATTLE state then exits on STAGE_MAP."""
    device = MockDevice()
    ctx = TaskContext(device=device)
    machine = CombatStateMachine()

    with patch.object(
        machine._detect, "evaluate",
        _make_detect_mock([GameState.BATTLE, GameState.STAGE_MAP])
    ), patch.object(machine._attack, "run", AsyncMock(
        return_value=OpResult(success=True)
    )):
        result = _run(machine.execute(ctx))

    assert result.status == "success"


def test_combat_state_machine_revive_then_stage_map():
    """Handles REVIVE_PROMPT state then exits on STAGE_MAP."""
    device = MockDevice()
    ctx = TaskContext(device=device)
    machine = CombatStateMachine()

    with patch.object(
        machine._detect, "evaluate",
        _make_detect_mock([GameState.REVIVE_PROMPT, GameState.STAGE_MAP])
    ), patch.object(machine._revive, "run", AsyncMock(
        return_value=OpResult(success=True)
    )):
        result = _run(machine.execute(ctx))

    assert result.status == "success"


def test_combat_state_machine_cutscene_then_stage_map():
    """Handles CUTSCENE state then exits on STAGE_MAP."""
    device = MockDevice()
    ctx = TaskContext(device=device)
    machine = CombatStateMachine()

    with patch.object(
        machine._detect, "evaluate",
        _make_detect_mock([GameState.CUTSCENE, GameState.STAGE_MAP])
    ), patch.object(machine._skip, "run", AsyncMock(
        return_value=OpResult(success=True)
    )):
        result = _run(machine.execute(ctx))

    assert result.status == "success"


def test_combat_state_machine_dialogue_then_stage_map():
    """Handles DIALOGUE state then exits on STAGE_MAP."""
    device = MockDevice()
    ctx = TaskContext(device=device)
    machine = CombatStateMachine()

    with patch.object(
        machine._detect, "evaluate",
        _make_detect_mock([GameState.DIALOGUE, GameState.STAGE_MAP])
    ), patch.object(machine._dialogue, "run", AsyncMock(
        return_value=OpResult(success=True)
    )):
        result = _run(machine.execute(ctx))

    assert result.status == "success"


def test_combat_state_machine_skip_story_confirm_presses_enter():
    """SKIP_STORY_CONFIRM: should press Enter, then complete on STAGE_MAP."""
    device = MockDevice()
    ctx = TaskContext(device=device)
    machine = CombatStateMachine()

    with patch.object(
        machine._detect, "evaluate",
        _make_detect_mock([GameState.SKIP_STORY_CONFIRM, GameState.STAGE_MAP])
    ):
        result = _run(machine.execute(ctx))

    assert result.status == "success"
    assert VK_ENTER in device.key_log


def test_combat_state_machine_continuous_battle_presses_enter():
    """CONTINUOUS_BATTLE: should press Enter to continue."""
    device = MockDevice()
    ctx = TaskContext(device=device)
    machine = CombatStateMachine()

    with patch.object(
        machine._detect, "evaluate",
        _make_detect_mock([GameState.CONTINUOUS_BATTLE, GameState.STAGE_MAP])
    ):
        result = _run(machine.execute(ctx))

    assert result.status == "success"
    assert VK_ENTER in device.key_log


def test_combat_state_machine_unknown_presses_space():
    """First UNKNOWN state: should press Space (phase 1 of rotation)."""
    device = MockDevice()
    ctx = TaskContext(device=device)
    machine = CombatStateMachine()

    with patch.object(
        machine._detect, "evaluate",
        _make_detect_mock([GameState.UNKNOWN, GameState.STAGE_MAP])
    ):
        result = _run(machine.execute(ctx))

    assert result.status == "success"
    assert VK_SPACE in device.key_log


def test_combat_state_machine_can_run():
    device = MockDevice()
    ctx = TaskContext(device=device)
    assert _run(CombatStateMachine().can_run(ctx)) is True


# --- ClearSingleStage ---

def test_clear_single_stage_presses_enter_first():
    """ClearSingleStage presses Enter to start battle from prep screen."""
    device = MockDevice()
    ctx = TaskContext(device=device)
    stage = ClearSingleStage()

    # Mock the inner CombatStateMachine by patching its execute
    with patch(
        "anime_game_afk.games.aether_gazer.tasks.combat_tasks"
        ".CombatStateMachine.execute",
        AsyncMock(return_value=TaskResult(status="success")),
    ):
        result = _run(stage.execute(ctx))

    assert result.status == "success"
    assert VK_ENTER in device.key_log


def test_clear_single_stage_propagates_failure():
    """ClearSingleStage propagates combat failure."""
    device = MockDevice()
    ctx = TaskContext(device=device)
    stage = ClearSingleStage()

    with patch(
        "anime_game_afk.games.aether_gazer.tasks.combat_tasks"
        ".CombatStateMachine.execute",
        AsyncMock(
            return_value=TaskResult(status="failed", message="Mission failed")
        ),
    ):
        result = _run(stage.execute(ctx))

    assert result.status == "failed"


def test_clear_single_stage_can_run():
    device = MockDevice()
    ctx = TaskContext(device=device)
    assert _run(ClearSingleStage().can_run(ctx)) is True
