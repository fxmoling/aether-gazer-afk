"""Battle state detection check.

Triple-signal AND detection:

1. **Pause icon (||)** template at right-top (grayscale CCOEFF_NORMED)
2. **Dodge button (Space)** template at right-bottom (grayscale CCOEFF_NORMED)
3. **Skill-region contrast** — the area where J/Tab/U/I/O buttons appear
   must have high grayscale standard deviation (buttons present → high
   contrast, empty explore world → low contrast).

All three must pass for ``passed=True``.  This eliminates the false
positive from 多维变量 exploration mode which has pause+dodge but no
skill buttons.

Uses the page template infrastructure (index.json + identify_page)
for resolution scaling, caching, and fractional search regions.

No side effects.
"""
from __future__ import annotations

import cv2
import numpy as np
from loguru import logger

from anime_game_afk.games.aether_gazer.checks.base import CheckResult
from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.games.aether_gazer.ops.perception.identify_page import (
    is_on_page,
)

# Two skill-button regions — either passing confirms battle.
# Region A (new post-2026 UI): right-middle, where J/Tab/U/I/O/Space icons
#   actually sit after the UI revamp added a keyboard-hint bar at bottom.
#   Calibrated 2026-05-11: std ~43-55 in battle, <30 in explore.
# Region B (legacy UI): bottom-right corner where skill buttons used to be
#   before the revamp.  Kept for compatibility in case the user has the old
#   UI layout or a different game version.
#   Legacy calibration: std 52-57+ in battle, 5-32 in explore.
_SKILL_REGION_A = (0.50, 0.58, 0.80, 0.74)   # new UI
_SKILL_REGION_B = (0.6875, 0.875, 0.9219, 0.9583)  # legacy UI

# Minimum grayscale std in either region to confirm skill buttons present.
_SKILL_STD_THRESHOLD = 40.0


class InBattleCheck:
    """Check if the game is currently in a battle.

    Detection uses three signals (all must pass):

    1. **Pause icon (||)** at right-top — unique to battle screens.
    2. **Dodge button (Space)** at right-bottom — stable across characters.
    3. **Skill-region contrast** — std ≥ 40 in the J–O button area.

    Signals 1+2 reject menus/lobbies.  Signal 3 rejects explore mode
    (多维变量) which has pause+dodge but no skill buttons.

    False negatives are harmless (retry in 0.5–2 s); false positives
    are harmful (pressing keys in non-battle screens).
    """

    async def evaluate(self, ctx: OpContext) -> CheckResult:
        img = ctx.device.screenshot()

        # Signal 1+2: pause icon + dodge button template match
        if not is_on_page(img, "battle_hud"):
            return CheckResult(
                passed=False,
                data={"method": "triple_signal", "stage": "template"},
                message="not in battle (template mismatch)",
            )

        # Signal 3: either skill-button region must have high contrast
        skill_std_a = _skill_region_std(img, _SKILL_REGION_A)
        skill_std_b = _skill_region_std(img, _SKILL_REGION_B)
        in_battle = (skill_std_a >= _SKILL_STD_THRESHOLD or
                     skill_std_b >= _SKILL_STD_THRESHOLD)
        logger.debug(
            "InBattleCheck: skill_std A={:.1f} B={:.1f} threshold={:.1f} => {}",
            skill_std_a, skill_std_b, _SKILL_STD_THRESHOLD, in_battle,
        )
        return CheckResult(
            passed=in_battle,
            data={
                "method": "triple_signal",
                "skill_std_a": round(skill_std_a, 1),
                "skill_std_b": round(skill_std_b, 1),
            },
            message="in battle" if in_battle else "not in battle (low skill contrast)",
        )


def _skill_region_std(img: np.ndarray, region: tuple[float, float, float, float]) -> float:
    """Compute grayscale std of the given fractional region."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    h, w = gray.shape[:2]
    x1, y1, x2, y2 = region
    roi = gray[int(y1 * h) : int(y2 * h), int(x1 * w) : int(x2 * w)]
    return float(roi.std())
