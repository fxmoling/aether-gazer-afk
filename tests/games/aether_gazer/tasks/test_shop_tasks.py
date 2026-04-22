"""Tests for tasks.shop_tasks -- BuyIntelShards, ClaimFreeStamina.

Updated to match the Op/Check refactoring: shop tasks now use Check
classes (HasTextCheck, FindTextCheck, etc.) instead of bare ocr_find
imports, and ReturnToHubAction instead of smart_return_to_hub function.

Mock strategy: patch the underlying vision functions at the Check module
level (checks.ocr.ocr_find, checks.ocr.ocr_once, etc.) and patch Op
classes (ReturnToHubAction.run, WakeHubUiAction.run, etc.) at their class level.
"""
import asyncio
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, patch, MagicMock

import numpy as np

from anime_game_afk.core.types import Rect
from anime_game_afk.games.aether_gazer.ops.base import OpResult
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext
from anime_game_afk.games.aether_gazer.tasks.shop_tasks import (
    BuyIntelShards,
    ClaimFreeStamina,
)
from anime_game_afk.vision.types import TextResult


@dataclass
class MockDevice:
    click_log: list = field(default_factory=list)
    key_log: list = field(default_factory=list)
    swipe_log: list = field(default_factory=list)

    def screenshot(self) -> np.ndarray:
        return np.zeros((900, 1600, 3), dtype=np.uint8)

    def click(self, x: int, y: int) -> None:
        self.click_log.append((x, y))

    def press_key(self, vk_code: int) -> None:
        self.key_log.append(vk_code)

    def hold_key(self, vk_code: int, duration_s: float) -> None:
        pass

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> None:
        self.swipe_log.append((x1, y1, x2, y2))


def _run(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro)


# Patch targets for Op classes used by shop tasks
_SHOP = "anime_game_afk.games.aether_gazer.tasks.shop_tasks"
_RETURN_TO_HUB_RUN = f"{_SHOP}.ReturnToHubAction.run"
_WAKE_HUB_RUN = f"{_SHOP}.WakeHubUiAction.run"
_IS_ON_PAGE = f"{_SHOP}.is_on_page"
_SMART_RETURN_RUN = f"{_SHOP}.ReturnToHubAction.run"

# Patch targets for underlying vision functions used by Check classes
_OCR_FIND = "anime_game_afk.games.aether_gazer.checks.ocr.ocr_find"
_OCR_FIND_ALL = "anime_game_afk.games.aether_gazer.checks.ocr.ocr_find_all"
_OCR_ONCE = "anime_game_afk.games.aether_gazer.checks.ocr.ocr_once"
_OCR_FULL = "anime_game_afk.games.aether_gazer.checks.ocr.ocr_full"
_PAGE_IS_ON_PAGE = "anime_game_afk.games.aether_gazer.checks.page.is_on_page"


# -- BuyIntelShards -- metadata --

def test_buy_intel_name():
    assert BuyIntelShards.name == "buy_intel_shards"


def test_buy_intel_description():
    assert "\u60c5\u62a5" in BuyIntelShards.description


def test_buy_intel_metadata():
    assert BuyIntelShards.category == "daily_shop"
    assert BuyIntelShards.requires_ocr is True
    assert BuyIntelShards.safe is False
    assert "shop_daily" in BuyIntelShards.requires_pages


def test_buy_intel_can_run():
    device = MockDevice()
    ctx = TaskContext(device=device)
    assert _run(BuyIntelShards().can_run(ctx)) is True


# -- BuyIntelShards -- execution --

def test_buy_intel_fails_when_nav_fails():
    """BuyIntelShards returns failed when cannot reach daily purchase page."""
    device = MockDevice()
    ctx = TaskContext(device=device)

    with patch(
        _RETURN_TO_HUB_RUN,
        AsyncMock(return_value=OpResult(success=False, error="no hub")),
    ), patch(
        _WAKE_HUB_RUN,
        AsyncMock(return_value=OpResult(success=True)),
    ):
        result = _run(BuyIntelShards().execute(ctx))

    assert result.status == "failed"
    assert "navigate" in result.message.lower() or "daily" in result.message.lower()


# -- ClaimFreeStamina -- metadata --

def test_claim_free_stamina_name():
    assert ClaimFreeStamina.name == "claim_free_stamina"


def test_claim_free_stamina_description():
    assert "stamina" in ClaimFreeStamina.description.lower()


def test_claim_free_stamina_metadata():
    assert ClaimFreeStamina.category == "daily_shop"
    assert ClaimFreeStamina.requires_ocr is True
    assert ClaimFreeStamina.safe is True  # Free item
    assert "shop_supply" in ClaimFreeStamina.requires_pages


def test_claim_free_stamina_can_run():
    device = MockDevice()
    ctx = TaskContext(device=device)
    assert _run(ClaimFreeStamina().can_run(ctx)) is True


# -- ClaimFreeStamina -- execution --

def test_claim_free_stamina_fails_when_nav_fails():
    """ClaimFreeStamina fails when cannot reach daily supply page."""
    device = MockDevice()
    ctx = TaskContext(device=device)

    with patch(
        _RETURN_TO_HUB_RUN,
        AsyncMock(return_value=OpResult(success=False, error="no hub")),
    ), patch(
        _WAKE_HUB_RUN,
        AsyncMock(return_value=OpResult(success=True)),
    ):
        result = _run(ClaimFreeStamina().execute(ctx))

    assert result.status == "failed"
    assert "navigate" in result.message.lower() or "supply" in result.message.lower()


def test_claim_free_stamina_skips_when_cooldown():
    """ClaimFreeStamina returns skipped when cooldown is active.

    The task navigates to daily supply, then checks OCR:
    - FindTextCheck("免费") -> not found (ocr_find returns None)
    - HasTextCheck("冷却") -> found (ocr_find returns TextResult)
    -> returns "skipped" with cooldown message
    """
    device = MockDevice()
    ctx = TaskContext(device=device)

    def mock_ocr_find(img, target, **kwargs):
        """Mock ocr_find for Check classes.

        HasTextCheck("免费") and FindTextCheck("免费") both call ocr_find.
        HasTextCheck("冷却") also calls ocr_find.
        Navigation verification (HasTextCheck("冷却"/"免费"/"日常补给"))
        also goes through ocr_find.
        """
        if target == "\u51b7\u5374":  # 冷却
            return TextResult(
                text="\u51b7\u5374",
                confidence=0.95,
                region=Rect(350, 290, 50, 20),
            )
        if target == "\u514d\u8d39":  # 免费
            return None
        # Navigation verification: return match for 日常补给 or other nav checks
        if target == "\u65e5\u5e38\u8865\u7ed9":  # 日常补给
            return TextResult(
                text="\u65e5\u5e38\u8865\u7ed9",
                confidence=0.90,
                region=Rect(500, 120, 100, 30),
            )
        return None

    with patch(
        _RETURN_TO_HUB_RUN,
        AsyncMock(return_value=OpResult(success=True)),
    ), patch(
        _WAKE_HUB_RUN,
        AsyncMock(return_value=OpResult(success=True)),
    ), patch(
        _IS_ON_PAGE,
        return_value=True,
    ), patch(
        _SMART_RETURN_RUN,
        AsyncMock(return_value=OpResult(success=True)),
    ), patch(
        _OCR_FIND,
        side_effect=mock_ocr_find,
    ):
        result = _run(ClaimFreeStamina().execute(ctx))

    assert result.status == "skipped"
    assert "cooldown" in result.message.lower()
