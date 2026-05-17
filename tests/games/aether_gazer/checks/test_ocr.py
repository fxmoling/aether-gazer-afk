"""Tests for OCR check retry helpers."""
import asyncio
from dataclasses import dataclass, field

import numpy as np

from anime_game_afk.core.types import Rect
from anime_game_afk.games.aether_gazer.checks import ocr as ocr_checks
from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.vision.ocr import OcrResult, TextResult


@dataclass
class MockDevice:
    screenshots: int = 0

    def screenshot(self) -> np.ndarray:
        self.screenshots += 1
        return np.zeros((100, 200, 3), dtype=np.uint8)

    def click(self, x: int, y: int) -> None:
        pass

    def press_key(self, vk_code: int) -> None:
        pass

    def hold_key(self, vk_code: int, duration_s: float) -> None:
        pass


@dataclass
class MockLogger:
    messages: list[str] = field(default_factory=list)

    def info(self, msg: str, **ctx) -> None:
        self.messages.append(msg)

    def debug(self, msg: str, **ctx) -> None:
        self.messages.append(msg)

    def warning(self, msg: str, **ctx) -> None:
        self.messages.append(msg)

    def error(self, msg: str, **ctx) -> None:
        self.messages.append(msg)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _ocr_result(text: str) -> OcrResult:
    return OcrResult([
        TextResult(text=text, confidence=0.9, region=Rect(1, 2, 3, 4))
    ])


def test_ocr_scan_with_retry_defaults_to_single_attempt(monkeypatch):
    calls = 0

    def fake_ocr_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        return OcrResult([])

    monkeypatch.setattr(ocr_checks, "ocr_once", fake_ocr_once)
    device = MockDevice()
    ctx = OpContext(device=device, logger=MockLogger())

    scan = _run(ocr_checks.ocr_scan_with_retry(ctx))

    assert len(scan.result) == 0
    assert calls == 1
    assert device.screenshots == 1


def test_ocr_scan_with_retry_uses_ready_predicate(monkeypatch):
    results = [OcrResult([]), _ocr_result("加载中"), _ocr_result("震动")]

    def fake_ocr_once(*args, **kwargs):
        return results.pop(0)

    monkeypatch.setattr(ocr_checks, "ocr_once", fake_ocr_once)
    device = MockDevice()
    ctx = OpContext(device=device, logger=MockLogger())

    scan = _run(
        ocr_checks.ocr_scan_with_retry(
            ctx,
            retries=2,
            retry_delay=0.0,
            ready=lambda result: result.has("震动"),
        )
    )

    assert scan.result.has("震动")
    assert device.screenshots == 3
