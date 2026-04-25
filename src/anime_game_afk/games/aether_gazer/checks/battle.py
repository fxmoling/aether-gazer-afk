"""Battle state detection check.

Dual-signal AND detection: matches pause icon (right-top) AND dodge
button (right-bottom) in a single screenshot.  Both must match for
``passed=True``.

Uses the page template infrastructure (index.json + identify_page)
for resolution scaling, caching, and fractional search regions.

No side effects.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.checks.base import CheckResult
from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.games.aether_gazer.ops.perception.identify_page import (
    is_on_page,
)


class InBattleCheck:
    """Check if the game is currently in a battle.

    Detection uses two template signals registered as ``battle_hud``
    in the page template index:

    1. **Pause icon (||)** at right-top — unique to battle screens.
    2. **Dodge button (Space)** at right-bottom — stable across characters.

    Both signals must match (AND logic).  False negatives are harmless
    (retry in 0.5–2 s); false positives are harmful (pressing keys in
    non-battle screens).
    """

    async def evaluate(self, ctx: OpContext) -> CheckResult:
        img = ctx.device.screenshot()
        in_battle = is_on_page(img, "battle_hud")
        return CheckResult(
            passed=in_battle,
            data={"method": "dual_template"},
            message="in battle" if in_battle else "not in battle",
        )
