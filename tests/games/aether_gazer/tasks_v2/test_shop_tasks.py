"""Tests for tasks_v2.shop_tasks — ClaimFreeStamina."""
import asyncio
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, patch

import numpy as np

from anime_game_afk.games.aether_gazer.ops.base import OpResult
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ESCAPE
from anime_game_afk.games.aether_gazer.tasks_v2.base import TaskContext
from anime_game_afk.games.aether_gazer.tasks_v2.shop_tasks import ClaimFreeStamina


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


def test_claim_free_stamina_success():
    """ClaimFreeStamina returns success when navigation succeeds."""
    device = MockDevice()
    ctx = TaskContext(device=device)

    with patch(
        "anime_game_afk.games.aether_gazer.tasks_v2.shop_tasks.GotoPageOp.run",
        AsyncMock(
            return_value=OpResult(success=True, data={"page_id": "shop"})
        ),
    ):
        result = _run(ClaimFreeStamina().execute(ctx))

    assert result.status == "success"
    assert result.data.get("claimed") == "free_stamina"


def test_claim_free_stamina_fails_if_no_shop():
    """ClaimFreeStamina fails when cannot navigate to shop."""
    device = MockDevice()
    ctx = TaskContext(device=device)

    with patch(
        "anime_game_afk.games.aether_gazer.tasks_v2.shop_tasks.GotoPageOp.run",
        AsyncMock(return_value=OpResult(success=False, error="no route")),
    ):
        result = _run(ClaimFreeStamina().execute(ctx))

    assert result.status == "failed"
    assert "shop" in result.message.lower()


def test_claim_free_stamina_presses_escape_to_dismiss():
    """ClaimFreeStamina presses ESC to dismiss popup after claiming."""
    device = MockDevice()
    ctx = TaskContext(device=device)

    with patch(
        "anime_game_afk.games.aether_gazer.tasks_v2.shop_tasks.GotoPageOp.run",
        AsyncMock(
            return_value=OpResult(success=True, data={"page_id": "shop"})
        ),
    ):
        _run(ClaimFreeStamina().execute(ctx))

    assert VK_ESCAPE in device.key_log


def test_claim_free_stamina_can_run():
    device = MockDevice()
    ctx = TaskContext(device=device)
    assert _run(ClaimFreeStamina().can_run(ctx)) is True


def test_claim_free_stamina_name():
    assert ClaimFreeStamina.name == "claim_free_stamina"
