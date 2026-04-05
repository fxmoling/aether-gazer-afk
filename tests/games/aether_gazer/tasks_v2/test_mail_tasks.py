"""Tests for tasks_v2.mail_tasks — CollectAllMail."""
import asyncio
from dataclasses import dataclass, field

import numpy as np

from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ESCAPE, VK_H
from anime_game_afk.games.aether_gazer.tasks_v2.base import TaskContext
from anime_game_afk.games.aether_gazer.tasks_v2.mail_tasks import CollectAllMail


@dataclass
class MockDevice:
    click_log: list = field(default_factory=list)
    key_log: list = field(default_factory=list)

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


def test_collect_all_mail_returns_success():
    device = MockDevice()
    ctx = TaskContext(device=device)
    result = _run(CollectAllMail().execute(ctx))
    assert result.status == "success"
    assert result.data.get("action") == "mail_collected"


def test_collect_all_mail_presses_h_shortcut():
    """CollectAllMail uses H shortcut to open mail panel."""
    device = MockDevice()
    ctx = TaskContext(device=device)
    _run(CollectAllMail().execute(ctx))
    assert VK_H in device.key_log


def test_collect_all_mail_presses_escape_to_close():
    """CollectAllMail presses ESC to close mail panel."""
    device = MockDevice()
    ctx = TaskContext(device=device)
    _run(CollectAllMail().execute(ctx))
    assert VK_ESCAPE in device.key_log


def test_collect_all_mail_clicks_collect_all():
    """CollectAllMail clicks the Collect All button."""
    device = MockDevice()
    ctx = TaskContext(device=device)
    _run(CollectAllMail().execute(ctx))
    assert (1400, 820) in device.click_log


def test_collect_all_mail_can_run():
    device = MockDevice()
    ctx = TaskContext(device=device)
    assert _run(CollectAllMail().can_run(ctx)) is True


def test_collect_all_mail_name():
    assert CollectAllMail.name == "collect_all_mail"
