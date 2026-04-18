"""Tests for tasks.startup_tasks -- SkipStartupPopups, LaunchAndReachHub.

Updated to match the Op/Check refactoring: tasks now use Check classes
(OnPageCheck, OcrScanCheck, AtHubCheck) and primitive Ops (PressKeyOp,
ClickOp, ScreenshotOp) instead of bare function imports.

Mock strategy: patch the underlying vision functions at the Check module
level so that Check.evaluate() behaves deterministically.
"""
import asyncio
from dataclasses import dataclass, field
from unittest.mock import patch, MagicMock, AsyncMock

import numpy as np

from anime_game_afk.games.aether_gazer.tasks.base import TaskContext
from anime_game_afk.games.aether_gazer.tasks.startup_tasks import (
    LaunchAndReachHub,
    SkipStartupPopups,
    ensure_game_running,
)
from anime_game_afk.vision.ocr import OcrResult
from anime_game_afk.vision.types import TextResult
from anime_game_afk.core.types import Rect


@dataclass
class MockDevice:
    click_log: list = field(default_factory=list)
    key_log: list = field(default_factory=list)
    _screenshots: list = field(default_factory=list)
    _call_idx: int = 0

    def screenshot(self) -> np.ndarray:
        if self._screenshots:
            idx = min(self._call_idx, len(self._screenshots) - 1)
            self._call_idx += 1
            return self._screenshots[idx]
        return np.zeros((900, 1600, 3), dtype=np.uint8)

    def click(self, x: int, y: int) -> None:
        self.click_log.append((x, y))

    def press_key(self, vk_code: int) -> None:
        self.key_log.append(vk_code)

    def hold_key(self, vk_code: int, duration_s: float) -> None:
        pass


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# -- Helpers --

def _make_hub_ocr():
    """Create OcrResult that looks like main hub."""
    return OcrResult([
        TextResult(text="前往作战", confidence=0.95, region=Rect(1400, 830, 100, 30)),
        TextResult(text="探测", confidence=0.92, region=Rect(750, 830, 60, 30)),
        TextResult(text="修正者", confidence=0.90, region=Rect(900, 830, 80, 30)),
        TextResult(text="仓库", confidence=0.91, region=Rect(1100, 830, 60, 30)),
    ])


def _make_loading_ocr():
    """Create OcrResult that looks like loading screen."""
    return OcrResult([
        TextResult(text="正在加载", confidence=0.90, region=Rect(700, 500, 200, 40)),
    ])


def _make_login_ocr():
    """Create OcrResult that looks like login screen."""
    return OcrResult([
        TextResult(text="点击屏幕进入游戏", confidence=0.88, region=Rect(600, 700, 300, 40)),
    ])


def _make_popup_ocr():
    """Create OcrResult with event popup containing 活动."""
    return OcrResult([
        TextResult(text="活动公告", confidence=0.87, region=Rect(600, 100, 200, 40)),
    ])


def _make_event_ocr():
    """Create OcrResult with event popup (should click close)."""
    return OcrResult([
        TextResult(text="限时活动", confidence=0.90, region=Rect(400, 200, 200, 40)),
        TextResult(text="前往", confidence=0.88, region=Rect(750, 700, 80, 35)),
    ])


def _make_idle_ocr():
    """Create OcrResult that looks like idle/screensaver mode."""
    return OcrResult([
        TextResult(text="正在播放", confidence=0.90, region=Rect(700, 400, 200, 40)),
    ])


def _make_empty_ocr():
    """Create empty OcrResult."""
    return OcrResult([])


# Patch targets for the underlying vision functions used by Check classes.
# OnPageCheck and AtHubCheck import from checks.page which uses:
#   is_on_page from ops.perception.identify_page
#   ocr_once from vision.ocr
# OcrScanCheck imports from checks.ocr which uses:
#   ocr_once from vision.ocr
_PAGE_IS_ON_PAGE = "anime_game_afk.games.aether_gazer.checks.page.is_on_page"
_PAGE_OCR_ONCE = "anime_game_afk.games.aether_gazer.checks.page.ocr_once"
_OCR_OCR_ONCE = "anime_game_afk.games.aether_gazer.checks.ocr.ocr_once"
_OCR_OCR_FIND = "anime_game_afk.games.aether_gazer.checks.ocr.ocr_find"


# -- SkipStartupPopups Tests --

class TestSkipStartupPopups:
    """Test popup dismissal task."""

    def test_can_run_always_true(self):
        device = MockDevice()
        ctx = TaskContext(device=device)
        task = SkipStartupPopups(max_attempts=5)
        assert _run(task.can_run(ctx)) is True

    def test_succeeds_when_already_at_hub(self):
        """If already at hub, succeeds immediately.

        The task flow for attempt 0:
        1. OnPageCheck("main_hub").evaluate(ctx) -> calls is_on_page(img, "main_hub")
           -> True -> enters hub-verify block
        2. OcrScanCheck().evaluate(ctx) -> calls ocr_once(img) -> hub OCR
           -> has_all("前往作战","探测","修正者","仓库") -> True -> return success
        """
        device = MockDevice()
        ctx = TaskContext(device=device)
        task = SkipStartupPopups(max_attempts=5)

        with patch(_PAGE_IS_ON_PAGE, return_value=True), \
             patch(_OCR_OCR_ONCE, return_value=_make_hub_ocr()), \
             patch(_PAGE_OCR_ONCE, return_value=_make_hub_ocr()):
            result = _run(task.execute(ctx))

        assert result.status == "success"
        assert result.data["attempts"] == 0

    def test_handles_loading_screen(self):
        """Loading screen causes waiting, not dismissal."""
        device = MockDevice()
        ctx = TaskContext(device=device)
        task = SkipStartupPopups(max_attempts=3)

        call_count = 0

        def mock_is_on_page(img, page_id):
            nonlocal call_count
            call_count += 1
            return call_count >= 3  # Hub found on 3rd check

        hub_ocr = _make_hub_ocr()

        def mock_ocr_once(img, **kwargs):
            if call_count >= 3:
                return hub_ocr
            return _make_loading_ocr()

        with patch(_PAGE_IS_ON_PAGE, side_effect=mock_is_on_page), \
             patch(_PAGE_OCR_ONCE, side_effect=mock_ocr_once), \
             patch(_OCR_OCR_ONCE, side_effect=mock_ocr_once):
            result = _run(task.execute(ctx))

        assert result.status == "success"

    def test_clicks_dismiss_for_event_popup(self):
        """When popup is shown (not hub, not exit), clicks dismiss position."""
        device = MockDevice()
        ctx = TaskContext(device=device)
        task = SkipStartupPopups(max_attempts=3)

        call_count = 0

        def mock_is_on_page(img, page_id):
            nonlocal call_count
            call_count += 1
            return call_count >= 3

        hub_ocr = _make_hub_ocr()

        def mock_ocr_once(img, **kwargs):
            if call_count >= 3:
                return hub_ocr
            return _make_popup_ocr()

        with patch(_PAGE_IS_ON_PAGE, side_effect=mock_is_on_page), \
             patch(_PAGE_OCR_ONCE, side_effect=mock_ocr_once), \
             patch(_OCR_OCR_ONCE, side_effect=mock_ocr_once):
            result = _run(task.execute(ctx))

        assert result.status == "success"
        # Simplified logic: clicks (0.4, 0.05) for any non-hub, non-exit screen
        assert (0.4, 0.05) in device.click_log

    def test_clicks_dismiss_for_event_forward_button(self):
        """When event popup with 限时 found, clicks dismiss position."""
        device = MockDevice()
        ctx = TaskContext(device=device)
        task = SkipStartupPopups(max_attempts=3)

        call_count = 0

        def mock_is_on_page(img, page_id):
            nonlocal call_count
            call_count += 1
            return call_count >= 3

        hub_ocr = _make_hub_ocr()

        def mock_ocr_once(img, **kwargs):
            if call_count >= 3:
                return hub_ocr
            return _make_event_ocr()

        with patch(_PAGE_IS_ON_PAGE, side_effect=mock_is_on_page), \
             patch(_PAGE_OCR_ONCE, side_effect=mock_ocr_once), \
             patch(_OCR_OCR_ONCE, side_effect=mock_ocr_once):
            result = _run(task.execute(ctx))

        assert (0.4, 0.05) in device.click_log

    def test_handles_login_screen(self):
        """Login screen gets a dismiss click."""
        device = MockDevice()
        ctx = TaskContext(device=device)
        task = SkipStartupPopups(max_attempts=3)

        call_count = 0

        def mock_is_on_page(img, page_id):
            nonlocal call_count
            call_count += 1
            return call_count >= 3

        hub_ocr = _make_hub_ocr()

        def mock_ocr_once(img, **kwargs):
            if call_count >= 3:
                return hub_ocr
            return _make_login_ocr()

        with patch(_PAGE_IS_ON_PAGE, side_effect=mock_is_on_page), \
             patch(_PAGE_OCR_ONCE, side_effect=mock_ocr_once), \
             patch(_OCR_OCR_ONCE, side_effect=mock_ocr_once):
            result = _run(task.execute(ctx))

        # Simplified: clicks (0.4, 0.05) for login screen too
        assert (0.4, 0.05) in device.click_log

    def test_fails_when_max_attempts_exceeded(self):
        """Returns failed when max attempts reached without hub."""
        device = MockDevice()
        ctx = TaskContext(device=device)
        task = SkipStartupPopups(max_attempts=2)

        with patch(_PAGE_IS_ON_PAGE, return_value=False), \
             patch(_PAGE_OCR_ONCE, return_value=_make_empty_ocr()), \
             patch(_OCR_OCR_ONCE, return_value=_make_empty_ocr()):
            result = _run(task.execute(ctx))

        assert result.status == "failed"

    def test_metadata(self):
        """Task has correct metadata attributes."""
        task = SkipStartupPopups()
        assert task.name == "skip_startup_popups"
        assert task.category == "startup"
        assert task.requires_ocr is True
        assert task.safe is True

    def test_handles_idle_screen(self):
        """Idle screen gets a click to wake up."""
        device = MockDevice()
        ctx = TaskContext(device=device)
        task = SkipStartupPopups(max_attempts=3)

        call_count = 0

        def mock_is_on_page(img, page_id):
            nonlocal call_count
            call_count += 1
            return call_count >= 3

        hub_ocr = _make_hub_ocr()

        def mock_ocr_once(img, **kwargs):
            if call_count >= 3:
                return hub_ocr
            return _make_idle_ocr()

        with patch(_PAGE_IS_ON_PAGE, side_effect=mock_is_on_page), \
             patch(_PAGE_OCR_ONCE, side_effect=mock_ocr_once), \
             patch(_OCR_OCR_ONCE, side_effect=mock_ocr_once):
            result = _run(task.execute(ctx))

        # Simplified: clicks (0.4, 0.05) for idle screen too
        assert (0.4, 0.05) in device.click_log


# -- LaunchAndReachHub Tests --

class TestLaunchAndReachHub:
    """Test the combined launch + hub task."""

    def test_metadata(self):
        task = LaunchAndReachHub()
        assert task.name == "launch_and_reach_hub"
        assert task.category == "startup"
        assert task.safe is True

    def test_can_run_always_true(self):
        device = MockDevice()
        ctx = TaskContext(device=device)
        task = LaunchAndReachHub()
        assert _run(task.can_run(ctx)) is True

    def test_delegates_to_skip_popups(self):
        """execute() delegates to SkipStartupPopups."""
        device = MockDevice()
        ctx = TaskContext(device=device)
        task = LaunchAndReachHub(max_popup_attempts=5)

        with patch(_PAGE_IS_ON_PAGE, return_value=True), \
             patch(_PAGE_OCR_ONCE, return_value=_make_hub_ocr()), \
             patch(_OCR_OCR_ONCE, return_value=_make_hub_ocr()):
            result = _run(task.execute(ctx))

        assert result.status == "success"


# -- ensure_game_running Tests --

class TestEnsureGameRunning:
    """Test the Phase 1 convenience function."""

    def test_calls_game_launcher(self, tmp_path):
        """ensure_game_running creates a GameLauncher and calls ensure_running."""
        exe = tmp_path / "AetherGazer.exe"
        exe.write_bytes(b"fake")

        with patch(
            "anime_game_afk.core.game_launcher.GameLauncher"
        ) as MockLauncher:
            mock_instance = MockLauncher.return_value
            mock_instance.ensure_running.return_value = True

            result = ensure_game_running(
                exe_path=str(exe),
                window_title="AetherGazer",
                timeout=30,
            )

        assert result is True
        mock_instance.ensure_running.assert_called_once_with(timeout=30)
