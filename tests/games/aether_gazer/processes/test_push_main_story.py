"""Tests for processes.push_main_story — PushMainStory."""
import asyncio
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, patch

import numpy as np

from anime_game_afk.games.aether_gazer.processes.base import ProcessContext
from anime_game_afk.games.aether_gazer.processes.push_main_story import (
    PushMainStory,
)
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


# Helper: patch a task's execute to return a fixed TaskResult
def _task_success():
    return AsyncMock(return_value=TaskResult(status="success"))


def _task_failed(msg: str = "failed"):
    return AsyncMock(return_value=TaskResult(status="failed", message=msg))


# --- PushMainStory ---

def test_push_main_story_name_and_description():
    proc = PushMainStory()
    assert proc.name == "push_main_story"
    assert "story" in proc.description.lower()


def test_push_main_story_success_clears_stages():
    """Full happy path: hub -> story -> 2 stages cleared -> hub."""
    device = MockDevice()
    ctx = ProcessContext(device=device, config={"max_stages": 2})

    with patch(
        "anime_game_afk.games.aether_gazer.processes.push_main_story"
        ".ReturnToHub.execute",
        _task_success(),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.push_main_story"
        ".EnterMainStory.execute",
        _task_success(),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.push_main_story"
        ".ClearSingleStage.execute",
        _task_success(),
    ):
        result = _run(PushMainStory().execute(ctx))

    assert result.status == "success"
    assert result.data["stages_cleared"] == 2


def test_push_main_story_fails_if_hub_unreachable():
    device = MockDevice()
    ctx = ProcessContext(device=device)

    with patch(
        "anime_game_afk.games.aether_gazer.processes.push_main_story"
        ".ReturnToHub.execute",
        _task_failed("no hub"),
    ):
        result = _run(PushMainStory().execute(ctx))

    assert result.status == "failed"
    assert "hub" in result.message.lower()


def test_push_main_story_fails_if_story_unreachable():
    device = MockDevice()
    ctx = ProcessContext(device=device)

    with patch(
        "anime_game_afk.games.aether_gazer.processes.push_main_story"
        ".ReturnToHub.execute",
        _task_success(),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.push_main_story"
        ".EnterMainStory.execute",
        _task_failed("no story"),
    ):
        result = _run(PushMainStory().execute(ctx))

    assert result.status == "failed"
    assert "story" in result.message.lower()


def test_push_main_story_stops_on_stage_failure():
    """If first stage fails immediately, returns 'failed' with 0 cleared."""
    device = MockDevice()
    ctx = ProcessContext(device=device, config={"max_stages": 5})

    with patch(
        "anime_game_afk.games.aether_gazer.processes.push_main_story"
        ".ReturnToHub.execute",
        _task_success(),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.push_main_story"
        ".EnterMainStory.execute",
        _task_success(),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.push_main_story"
        ".ClearSingleStage.execute",
        _task_failed("stage failed"),
    ):
        result = _run(PushMainStory().execute(ctx))

    assert result.status == "failed"
    assert result.data["stages_cleared"] == 0


def test_push_main_story_respects_max_stages():
    """max_stages from config caps the loop."""
    device = MockDevice()
    ctx = ProcessContext(device=device, config={"max_stages": 3})

    with patch(
        "anime_game_afk.games.aether_gazer.processes.push_main_story"
        ".ReturnToHub.execute",
        _task_success(),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.push_main_story"
        ".EnterMainStory.execute",
        _task_success(),
    ), patch(
        "anime_game_afk.games.aether_gazer.processes.push_main_story"
        ".ClearSingleStage.execute",
        _task_success(),
    ):
        result = _run(PushMainStory().execute(ctx))

    assert result.data["stages_cleared"] == 3
