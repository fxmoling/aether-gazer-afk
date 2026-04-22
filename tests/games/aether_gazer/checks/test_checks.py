"""Tests for all Check classes in checks/ package.

Uses mocks to isolate checks from real OCR, vision, and page detection.
"""
import asyncio
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import numpy as np

from anime_game_afk.core.types import Rect
from anime_game_afk.games.aether_gazer.checks.base import CheckResult
from anime_game_afk.games.aether_gazer.checks.ocr import (
    FindAllTextCheck,
    FindTextCheck,
    HasTextCheck,
    OcrFullCheck,
    OcrScanCheck,
)
from anime_game_afk.games.aether_gazer.checks.page import (
    AtHubCheck,
    OnPageCheck,
)
from anime_game_afk.games.aether_gazer.checks.state import (
    DetectGameStateCheck,
    ScreenUnchangedCheck,
)
from anime_game_afk.games.aether_gazer.checks.vision import (
    HasColorCheck,
    TemplateMatchCheck,
)
from anime_game_afk.games.aether_gazer.ops.base import GameState, OpContext
from anime_game_afk.vision.ocr import OcrResult
from anime_game_afk.vision.types import MatchResult, TextResult


@dataclass
class MockDevice:
    """Minimal device mock for testing."""
    click_log: list = None
    key_log: list = None

    def __post_init__(self):
        self.click_log = self.click_log or []
        self.key_log = self.key_log or []

    def screenshot(self) -> np.ndarray:
        return np.zeros((900, 1600, 3), dtype=np.uint8)

    def click(self, x: int, y: int) -> None:
        self.click_log.append((x, y))

    def press_key(self, vk_code: int) -> None:
        self.key_log.append(vk_code)

    def hold_key(self, vk_code: int, duration_s: float) -> None:
        self.key_log.append((vk_code, duration_s))


def _run(coro):
    """Helper: run a coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_ctx() -> OpContext:
    return OpContext(device=MockDevice())


def _text_result(text: str = "测试", conf: float = 0.9) -> TextResult:
    return TextResult(text=text, confidence=conf, region=Rect(10, 20, 50, 15))


# ── OCR Checks ──


@patch("anime_game_afk.games.aether_gazer.checks.ocr.ocr_find")
def test_has_text_check_passed(mock_ocr_find):
    mock_ocr_find.return_value = _text_result("前往作战")
    check = HasTextCheck("前往作战")
    result = _run(check.evaluate(_make_ctx()))
    assert result.passed
    assert result.data.text == "前往作战"
    mock_ocr_find.assert_called_once()


@patch("anime_game_afk.games.aether_gazer.checks.ocr.ocr_find")
def test_has_text_check_failed(mock_ocr_find):
    mock_ocr_find.return_value = None
    check = HasTextCheck("不存在")
    result = _run(check.evaluate(_make_ctx()))
    assert not result.passed
    assert result.data is None


@patch("anime_game_afk.games.aether_gazer.checks.ocr.ocr_find")
def test_find_text_check_passed(mock_ocr_find):
    mock_ocr_find.return_value = _text_result("探测")
    check = FindTextCheck("探测")
    result = _run(check.evaluate(_make_ctx()))
    assert result.passed
    assert result.data.text == "探测"


@patch("anime_game_afk.games.aether_gazer.checks.ocr.ocr_find")
def test_find_text_check_failed(mock_ocr_find):
    mock_ocr_find.return_value = None
    check = FindTextCheck("探测")
    result = _run(check.evaluate(_make_ctx()))
    assert not result.passed


@patch("anime_game_afk.games.aether_gazer.checks.ocr.ocr_find_all")
def test_find_all_text_check_passed(mock_ocr_find_all):
    mock_ocr_find_all.return_value = [
        _text_result("情报A"),
        _text_result("情报B"),
    ]
    check = FindAllTextCheck("情报")
    result = _run(check.evaluate(_make_ctx()))
    assert result.passed
    assert len(result.data) == 2


@patch("anime_game_afk.games.aether_gazer.checks.ocr.ocr_find_all")
def test_find_all_text_check_failed(mock_ocr_find_all):
    mock_ocr_find_all.return_value = []
    check = FindAllTextCheck("情报")
    result = _run(check.evaluate(_make_ctx()))
    assert not result.passed


@patch("anime_game_afk.games.aether_gazer.checks.ocr.ocr_once")
def test_ocr_scan_check_passed(mock_ocr_once):
    mock_ocr_once.return_value = OcrResult([_text_result("hello")])
    check = OcrScanCheck()
    result = _run(check.evaluate(_make_ctx()))
    assert result.passed
    assert len(result.data) == 1


@patch("anime_game_afk.games.aether_gazer.checks.ocr.ocr_once")
def test_ocr_scan_check_failed(mock_ocr_once):
    mock_ocr_once.return_value = OcrResult([])
    check = OcrScanCheck()
    result = _run(check.evaluate(_make_ctx()))
    assert not result.passed


@patch("anime_game_afk.games.aether_gazer.checks.ocr.ocr_full")
def test_ocr_full_check_passed(mock_ocr_full):
    mock_ocr_full.return_value = [_text_result("text1"), _text_result("text2")]
    check = OcrFullCheck()
    result = _run(check.evaluate(_make_ctx()))
    assert result.passed
    assert len(result.data) == 2


@patch("anime_game_afk.games.aether_gazer.checks.ocr.ocr_full")
def test_ocr_full_check_failed(mock_ocr_full):
    mock_ocr_full.return_value = []
    check = OcrFullCheck()
    result = _run(check.evaluate(_make_ctx()))
    assert not result.passed


# ── Page Checks ──


@patch("anime_game_afk.games.aether_gazer.checks.page.is_on_page")
def test_on_page_check_passed(mock_is_on_page):
    mock_is_on_page.return_value = True
    check = OnPageCheck("main_hub")
    result = _run(check.evaluate(_make_ctx()))
    assert result.passed
    assert result.data == {"page": "main_hub"}


@patch("anime_game_afk.games.aether_gazer.checks.page.is_on_page")
def test_on_page_check_failed(mock_is_on_page):
    mock_is_on_page.return_value = False
    check = OnPageCheck("main_hub")
    result = _run(check.evaluate(_make_ctx()))
    assert not result.passed


@patch("anime_game_afk.games.aether_gazer.checks.page.ocr_once")
@patch("anime_game_afk.games.aether_gazer.checks.page.is_on_page")
def test_at_hub_check_passed_template(mock_is_on_page, mock_ocr_once):
    mock_is_on_page.return_value = True
    check = AtHubCheck()
    result = _run(check.evaluate(_make_ctx()))
    assert result.passed
    assert result.data["method"] == "template"
    mock_ocr_once.assert_not_called()


@patch("anime_game_afk.games.aether_gazer.checks.page.ocr_once")
@patch("anime_game_afk.games.aether_gazer.checks.page.is_on_page")
def test_at_hub_check_passed_ocr(mock_is_on_page, mock_ocr_once):
    mock_is_on_page.return_value = False
    mock_ocr_result = MagicMock()
    mock_ocr_result.has_all.return_value = True
    mock_ocr_once.return_value = mock_ocr_result
    check = AtHubCheck()
    result = _run(check.evaluate(_make_ctx()))
    assert result.passed
    assert result.data["method"] == "ocr"


@patch("anime_game_afk.games.aether_gazer.checks.page.ocr_once")
@patch("anime_game_afk.games.aether_gazer.checks.page.is_on_page")
def test_at_hub_check_failed(mock_is_on_page, mock_ocr_once):
    mock_is_on_page.return_value = False
    mock_ocr_result = MagicMock()
    mock_ocr_result.has_all.return_value = False
    # Relaxed check uses .has() per keyword — return False for all
    mock_ocr_result.has.return_value = False
    mock_ocr_once.return_value = mock_ocr_result
    check = AtHubCheck()
    result = _run(check.evaluate(_make_ctx()))
    assert not result.passed


# ── State Checks ──


@patch("anime_game_afk.games.aether_gazer.checks.state.detect_state")
def test_detect_game_state_check_known(mock_detect):
    mock_detect.return_value = (GameState.BATTLE, 0.95)
    check = DetectGameStateCheck()
    result = _run(check.evaluate(_make_ctx()))
    assert result.passed
    assert result.data["state"] == GameState.BATTLE
    assert result.data["confidence"] == 0.95


@patch("anime_game_afk.games.aether_gazer.checks.state.detect_state")
def test_detect_game_state_check_unknown(mock_detect):
    mock_detect.return_value = (GameState.UNKNOWN, 0.0)
    check = DetectGameStateCheck()
    result = _run(check.evaluate(_make_ctx()))
    assert not result.passed
    assert result.data["state"] == GameState.UNKNOWN


def test_screen_unchanged_check_same_image():
    prev = np.zeros((900, 1600, 3), dtype=np.uint8)
    check = ScreenUnchangedCheck(prev_image=prev, threshold=5.0)
    result = _run(check.evaluate(_make_ctx()))
    # MockDevice returns zeros, prev is zeros → identical
    assert result.passed
    assert result.data["diff"] == 0.0


def test_screen_unchanged_check_different_image():
    prev = np.full((900, 1600, 3), 200, dtype=np.uint8)
    check = ScreenUnchangedCheck(prev_image=prev, threshold=5.0)
    result = _run(check.evaluate(_make_ctx()))
    # MockDevice returns zeros, prev is 200 → large diff
    assert not result.passed
    assert result.data["diff"] > 5.0


# ── Vision Checks ──


@patch("anime_game_afk.games.aether_gazer.checks.vision.match_template")
def test_template_match_check_passed(mock_match):
    mock_match.return_value = MatchResult(
        score=0.85, x=100, y=200, w=50, h=30, matched=True,
    )
    tpl_img = np.zeros((30, 50, 3), dtype=np.uint8)
    check = TemplateMatchCheck(template_image=tpl_img, threshold=0.7)
    result = _run(check.evaluate(_make_ctx()))
    assert result.passed
    assert result.data.score == 0.85


@patch("anime_game_afk.games.aether_gazer.checks.vision.match_template")
def test_template_match_check_failed(mock_match):
    mock_match.return_value = MatchResult(
        score=0.3, x=0, y=0, w=50, h=30, matched=False,
    )
    tpl_img = np.zeros((30, 50, 3), dtype=np.uint8)
    check = TemplateMatchCheck(template_image=tpl_img, threshold=0.7)
    result = _run(check.evaluate(_make_ctx()))
    assert not result.passed


def test_template_match_check_no_template():
    check = TemplateMatchCheck()  # no template_path, no template_image
    result = _run(check.evaluate(_make_ctx()))
    assert not result.passed
    assert "not loaded" in result.message


@patch("anime_game_afk.games.aether_gazer.checks.vision.color_ratio")
def test_has_color_check_passed(mock_color_ratio):
    mock_color_ratio.return_value = 0.35
    check = HasColorCheck(
        hsv_low=(0, 100, 100),
        hsv_high=(10, 255, 255),
        min_ratio=0.1,
    )
    result = _run(check.evaluate(_make_ctx()))
    assert result.passed
    assert result.data["ratio"] == 0.35


@patch("anime_game_afk.games.aether_gazer.checks.vision.color_ratio")
def test_has_color_check_failed(mock_color_ratio):
    mock_color_ratio.return_value = 0.02
    check = HasColorCheck(
        hsv_low=(0, 100, 100),
        hsv_high=(10, 255, 255),
        min_ratio=0.1,
    )
    result = _run(check.evaluate(_make_ctx()))
    assert not result.passed
    assert result.data["ratio"] == 0.02
