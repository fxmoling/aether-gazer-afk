"""Page identification checks.

Checks for determining which game page/screen is currently displayed.
Uses template matching and/or OCR. No side effects.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.checks.base import CheckResult
from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.games.aether_gazer.ops.perception.identify_page import (
    identify,
    is_on_page,
)
from anime_game_afk.vision.ocr import ocr_once


class OnPageCheck:
    """Check if the current screen matches a specific page.

    Uses template matching via identify_page module.
    """

    def __init__(self, page: str) -> None:
        self._page = page

    async def evaluate(self, ctx: OpContext) -> CheckResult:
        img = ctx.device.screenshot()
        if is_on_page(img, self._page):
            return CheckResult(
                passed=True,
                data={"page": self._page},
                message=f"on page '{self._page}'",
            )
        return CheckResult(
            passed=False,
            message=f"not on page '{self._page}'",
        )


class IdentifyPageCheck:
    """Identify which page the current screen shows.

    Always passes (returns the best guess). data contains page_id
    and confidence. Check passed=True if confidence >= threshold.
    """

    def __init__(self, threshold: float = 0.65) -> None:
        self._threshold = threshold

    async def evaluate(self, ctx: OpContext) -> CheckResult:
        img = ctx.device.screenshot()
        page_id, confidence = identify(img)
        return CheckResult(
            passed=(page_id != "unknown" and confidence >= self._threshold),
            data={"page": page_id, "confidence": confidence},
            message=f"page='{page_id}' conf={confidence:.2f}",
        )


# Hub detection keywords — must match helpers._HUB_KEYWORDS
_HUB_KEYWORDS = ("前往作战", "探测", "修正者", "仓库")

# Partial hub keywords — if we see at least 2, probably at hub
# (some may be obscured by overlays or idle mode)
_HUB_MIN_KEYWORDS = 2


class AtHubCheck:
    """Check if we are at the main hub.

    Strategy: fast template match first (~5ms), OCR fallback (~2s).

    OCR detection uses a relaxed threshold: if at least 2 of the 4
    hub keywords are visible, we consider it hub. This handles cases
    where the hub is partially obscured (idle mode, overlays, popups).

    The strict 4-keyword check was causing false negatives when the
    hub was in idle mode (UI hidden) or had an overlay on top.
    """

    async def evaluate(self, ctx: OpContext) -> CheckResult:
        img = ctx.device.screenshot()

        # Fast path: template matching
        if is_on_page(img, "main_hub"):
            return CheckResult(
                passed=True,
                data={"method": "template"},
                message="at hub (template match)",
            )

        # Slow path: OCR with relaxed keyword matching
        ocr = ocr_once(img)

        # Count how many hub keywords are visible
        found = [kw for kw in _HUB_KEYWORDS if ocr.has(kw)]

        if len(found) >= _HUB_MIN_KEYWORDS:
            return CheckResult(
                passed=True,
                data={"method": "ocr", "keywords_found": found},
                message=f"at hub (OCR {len(found)}/{len(_HUB_KEYWORDS)} keywords)",
            )

        return CheckResult(
            passed=False,
            data={"keywords_found": found},
            message=f"not at hub (only {len(found)}/{len(_HUB_KEYWORDS)} keywords)",
        )
