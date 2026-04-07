"""Vision-based checks — template matching and color detection.

No side effects. All checks take a screenshot internally.
"""
from __future__ import annotations

import cv2
import numpy as np

from anime_game_afk.core.types import Rect
from anime_game_afk.games.aether_gazer.checks.base import CheckResult
from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.vision.color import color_ratio
from anime_game_afk.vision.matcher import match_template


class TemplateMatchCheck:
    """Check if a template image matches the current screen.

    template_path is loaded once on first evaluate. Alternatively,
    pass a pre-loaded numpy array via template_image.
    """

    def __init__(
        self,
        template_path: str | None = None,
        template_image: np.ndarray | None = None,
        region: Rect | None = None,
        threshold: float = 0.7,
    ) -> None:
        self._path = template_path
        self._image = template_image
        self._region = region
        self._threshold = threshold

    def _load(self) -> np.ndarray | None:
        if self._image is not None:
            return self._image
        if self._path is not None:
            img = cv2.imread(self._path)
            if img is not None:
                self._image = img  # cache
            return img
        return None

    async def evaluate(self, ctx: OpContext) -> CheckResult:
        tpl = self._load()
        if tpl is None:
            return CheckResult(
                passed=False,
                message="template not loaded",
            )
        img = ctx.device.screenshot()
        result = match_template(
            img, tpl, region=self._region, threshold=self._threshold,
        )
        return CheckResult(
            passed=result.matched,
            data=result,
            message=(
                f"template match score={result.score:.2f} "
                f"at ({result.x},{result.y})"
            ),
        )


class HasColorCheck:
    """Check if a region has a certain HSV color above a minimum ratio.

    Returns passed=True if the color ratio >= min_ratio.
    """

    def __init__(
        self,
        hsv_low: tuple[int, int, int],
        hsv_high: tuple[int, int, int],
        region: Rect | None = None,
        min_ratio: float = 0.1,
    ) -> None:
        self._hsv_low = hsv_low
        self._hsv_high = hsv_high
        self._region = region
        self._min_ratio = min_ratio

    async def evaluate(self, ctx: OpContext) -> CheckResult:
        img = ctx.device.screenshot()
        ratio = color_ratio(
            img, self._hsv_low, self._hsv_high, region=self._region,
        )
        passed = ratio >= self._min_ratio
        return CheckResult(
            passed=passed,
            data={"ratio": ratio},
            message=(
                f"color ratio={ratio:.3f} "
                f"({'above' if passed else 'below'} {self._min_ratio})"
            ),
        )
