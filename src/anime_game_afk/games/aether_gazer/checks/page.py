"""Page identification checks.

Checks for determining which game page/screen is currently displayed.
Uses template matching and/or OCR. No side effects.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.checks.base import CheckResult
from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.games.aether_gazer.ops.perception.identify_page import (
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


# Hub detection keywords — must match helpers._HUB_KEYWORDS
_HUB_KEYWORDS = ("前往作战", "探测", "修正者", "仓库")

# Partial hub keywords — if we see at least 2, probably at hub
# (some may be obscured by overlays or idle mode)
_HUB_MIN_KEYWORDS = 2


class AtHubCheck:
    """Check if we are at the main hub (active, with UI visible).

    Strategy: fast template match first (~5ms), idle check (~5ms),
    OCR fallback (~2s).

    ``passed=True`` means the hub is *interactive* (active state with
    UI visible).  When the hub is in idle mode (UI hidden, music player
    visible), ``passed=False`` is returned with ``hub_state="idle"`` in
    ``data`` so callers can act on it (e.g. click back-button to wake).

    OCR detection uses a relaxed threshold: if at least 2 of the 4
    hub keywords are visible, we consider it hub. This handles cases
    where the hub is partially obscured (overlays, popups).
    """

    async def evaluate(self, ctx: OpContext) -> CheckResult:
        img = ctx.device.screenshot()

        # Fast path: active hub template match
        if is_on_page(img, "main_hub"):
            return CheckResult(
                passed=True,
                data={"method": "template", "hub_state": "active"},
                message="at hub (template match)",
            )

        # Check for idle hub (UI hidden, music player visible)
        if is_on_page(img, "hub_idle"):
            return CheckResult(
                passed=False,
                data={"hub_state": "idle"},
                message="hub idle (UI hidden, click back to wake)",
            )

        # Slow path: OCR with relaxed keyword matching
        ocr = ocr_once(img)

        # Count how many hub keywords are visible
        found = [kw for kw in _HUB_KEYWORDS if ocr.has(kw)]

        if len(found) >= _HUB_MIN_KEYWORDS:
            return CheckResult(
                passed=True,
                data={"method": "ocr", "keywords_found": found, "hub_state": "active"},
                message=f"at hub (OCR {len(found)}/{len(_HUB_KEYWORDS)} keywords)",
            )

        return CheckResult(
            passed=False,
            data={"keywords_found": found, "ocr": ocr},
            message=f"not at hub (only {len(found)}/{len(_HUB_KEYWORDS)} keywords)",
        )
