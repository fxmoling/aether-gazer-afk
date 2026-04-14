"""Tests for tasks.story_tasks — NavigateToChapter, SelectLatestStage."""
import asyncio
from dataclasses import dataclass, field

import numpy as np

from anime_game_afk.games.aether_gazer.tasks.base import TaskContext
from anime_game_afk.games.aether_gazer.tasks.story_tasks import (
    NavigateToChapter,
    SelectLatestStage,
)


@dataclass
class MockDevice:
    click_log: list = field(default_factory=list)

    def screenshot(self) -> np.ndarray:
        return np.zeros((900, 1600, 3), dtype=np.uint8)
    def click(self, x: int, y: int) -> None:
        self.click_log.append((x, y))
    def press_key(self, vk_code: int) -> None: ...
    def hold_key(self, vk_code: int, duration_s: float) -> None: ...


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# --- NavigateToChapter ---

def test_navigate_to_chapter_zero_skips_scroll():
    """Chapter index 0 returns success without clicking."""
    device = MockDevice()
    ctx = TaskContext(device=device)
    result = _run(NavigateToChapter(chapter_index=0).execute(ctx))
    assert result.status == "success"
    assert result.data["chapter"] == 0
    # No click needed for index 0
    assert len(device.click_log) == 0


def test_navigate_to_chapter_positive_clicks():
    """Chapter index > 0 clicks the calculated row position."""
    device = MockDevice()
    ctx = TaskContext(device=device)
    result = _run(NavigateToChapter(chapter_index=2).execute(ctx))
    assert result.status == "success"
    assert result.data["chapter"] == 2
    # Should have clicked to scroll to chapter
    assert len(device.click_log) == 1
    _, y = device.click_log[0]
    # y should be > 200 (offset) + 2 * row_height
    assert y > 200


def test_navigate_to_chapter_can_run():
    device = MockDevice()
    ctx = TaskContext(device=device)
    assert _run(NavigateToChapter().can_run(ctx)) is True


def test_navigate_to_chapter_name():
    assert NavigateToChapter.name == "navigate_to_chapter"


# --- SelectLatestStage ---

def test_select_latest_stage_returns_success():
    device = MockDevice()
    ctx = TaskContext(device=device)
    result = _run(SelectLatestStage().execute(ctx))
    assert result.status == "success"
    assert result.data.get("action") == "stage_selected"


def test_select_latest_stage_clicks_active_stage():
    """SelectLatestStage clicks the active stage area."""
    device = MockDevice()
    ctx = TaskContext(device=device)
    _run(SelectLatestStage().execute(ctx))
    assert (532, 450) in device.click_log  # int(0.333 * 1600) = 532


def test_select_latest_stage_can_run():
    device = MockDevice()
    ctx = TaskContext(device=device)
    assert _run(SelectLatestStage().can_run(ctx)) is True


def test_select_latest_stage_name():
    assert SelectLatestStage.name == "select_latest_stage"
