"""OCR-based checks — text detection and recognition.

All checks take a screenshot internally and analyze via OCR.
None of them modify game state.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable

import numpy as np

from anime_game_afk.core.types import Rect
from anime_game_afk.games.aether_gazer.checks.base import CheckResult
from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.vision.ocr import (
    OcrResult,
    ocr_find,
    ocr_find_all,
    ocr_full,
    ocr_once,
)


@dataclass(frozen=True)
class OcrScan:
    """Screenshot and OCR result captured in the same pass."""

    image: np.ndarray
    result: OcrResult


async def ocr_scan_with_retry(
    ctx: OpContext,
    *,
    region: Rect | None = None,
    scale: float = 0.7,
    threshold: float = 0.5,
    retries: int = 0,
    retry_delay: float = 0.0,
    ready: Callable[[OcrResult], bool] | None = None,
) -> OcrScan:
    """Run OCR with optional retry until the result is ready.

    ``retries`` is the number of extra attempts after the first pass.
    The default is no retry. If ``ready`` is omitted, any recognized text
    counts as a successful OCR pass.
    """

    attempts = max(1, retries + 1)
    is_ready = ready or (lambda result: len(result) > 0)
    last_scan: OcrScan | None = None

    for attempt in range(1, attempts + 1):
        image = ctx.device.screenshot()
        result = ocr_once(
            image,
            region=region,
            scale=scale,
            threshold=threshold,
        )
        scan = OcrScan(image=image, result=result)
        last_scan = scan
        if is_ready(result):
            if attempt > 1:
                ctx.logger.info(
                    f"OCR succeeded on attempt {attempt}/{attempts}"
                )
            return scan

        if attempt < attempts:
            ctx.logger.debug(
                f"OCR attempt {attempt}/{attempts} not ready; "
                f"retrying in {retry_delay:.1f}s"
            )
            if retry_delay > 0:
                await asyncio.sleep(retry_delay)

    assert last_scan is not None
    return last_scan


class FindTextCheck:
    """Find specific text on screen and return its position.

    Returns passed=True if text is found. data is the TextResult with
    region coordinates for clicking.
    """

    def __init__(
        self,
        target: str,
        region: Rect | None = None,
        threshold: float = 0.5,
    ) -> None:
        self._target = target
        self._region = region
        self._threshold = threshold

    async def evaluate(self, ctx: OpContext) -> CheckResult:
        img = ctx.device.screenshot()
        result = ocr_find(img, self._target, region=self._region,
                          threshold=self._threshold)
        if result is None:
            return CheckResult(
                passed=False,
                message=f"'{self._target}' not found",
            )
        return CheckResult(
            passed=True,
            data=result,
            message=(
                f"found '{self._target}' at "
                f"({result.region.x},{result.region.y}) "
                f"conf={result.confidence:.2f}"
            ),
        )


# Backward compatibility alias
HasTextCheck = FindTextCheck


class FindAllTextCheck:
    """Find all occurrences of specific text on screen.

    Returns passed=True if at least one match is found.
    data is list[TextResult].
    """

    def __init__(
        self,
        target: str,
        region: Rect | None = None,
        threshold: float = 0.5,
    ) -> None:
        self._target = target
        self._region = region
        self._threshold = threshold

    async def evaluate(self, ctx: OpContext) -> CheckResult:
        img = ctx.device.screenshot()
        results = ocr_find_all(
            img, self._target,
            region=self._region,
            threshold=self._threshold,
        )
        if not results:
            return CheckResult(
                passed=False,
                message=f"'{self._target}' not found",
            )
        return CheckResult(
            passed=True,
            data=results,
            message=f"found {len(results)} matches for '{self._target}'",
        )


class OcrScanCheck:
    """Run OCR on a region and return all recognized text.

    Returns passed=True if any text was recognized.
    data is the OcrResult (batch API).
    """

    def __init__(
        self,
        region: Rect | None = None,
        scale: float = 0.7,
        threshold: float = 0.5,
        retries: int = 0,
        retry_delay: float = 0.0,
    ) -> None:
        self._region = region
        self._scale = scale
        self._threshold = threshold
        self._retries = retries
        self._retry_delay = retry_delay

    async def evaluate(self, ctx: OpContext) -> CheckResult:
        scan = await ocr_scan_with_retry(
            ctx,
            region=self._region,
            scale=self._scale,
            threshold=self._threshold,
            retries=self._retries,
            retry_delay=self._retry_delay,
        )
        result = scan.result
        if len(result) == 0:
            return CheckResult(
                passed=False,
                message="no text recognized",
            )
        return CheckResult(
            passed=True,
            data=result,
            message=f"recognized {len(result)} text items",
        )


class OcrFullCheck:
    """Run full OCR (no scaling) and return raw TextResult list.

    Returns passed=True if any text was recognized.
    data is list[TextResult].
    """

    def __init__(
        self,
        region: Rect | None = None,
        threshold: float = 0.5,
    ) -> None:
        self._region = region
        self._threshold = threshold

    async def evaluate(self, ctx: OpContext) -> CheckResult:
        img = ctx.device.screenshot()
        results = ocr_full(img, region=self._region,
                           threshold=self._threshold)
        if not results:
            return CheckResult(
                passed=False,
                message="no text recognized",
            )
        return CheckResult(
            passed=True,
            data=results,
            message=f"recognized {len(results)} text items",
        )
