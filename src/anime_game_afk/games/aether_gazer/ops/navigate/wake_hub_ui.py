"""Wake up hub UI from idle mode.

When the hub is idle (screensaver-like), the UI is hidden.  Clicks the
back-button position (0.022, 0.039) which exits idle even if the button
is not yet visible.

Uses template matching to detect hub state first — if already active,
does nothing (avoids triggering the exit dialog with ESC).

Composite Action: uses ClickOp primitive + AtHubCheck / is_on_page.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.perception.identify_page import (
    is_on_page,
)
from anime_game_afk.games.aether_gazer.ops.primitives import (
    ClickOp,
    SleepOp,
)


class WakeHubUiAction:
    """Wake idle hub UI using back-button click, with active-hub short-circuit.

    Strategy:
    1. Screenshot + template check ``main_hub`` → already active → return
    2. Screenshot + template check ``hub_idle`` → click back button → wait
    3. Neither → click center (dismiss overlay) + click back button
    """

    async def run(self, ctx: OpContext) -> OpResult:
        img = ctx.device.screenshot()

        # Fast path: hub is already active — nothing to do
        if is_on_page(img, "main_hub"):
            ctx.logger.debug("Hub already active, no wake needed")
            return OpResult(success=True)

        # Idle hub: click back-button position to wake
        if is_on_page(img, "hub_idle"):
            ctx.logger.debug("Hub idle detected, clicking back button to wake")
            await ClickOp(x=0.022, y=0.039, wait=1.5).run(ctx)
            ctx.logger.debug("Woke hub UI from idle")
            return OpResult(success=True)

        # Unknown state: click center (dismiss potential overlay) then back
        ctx.logger.debug("Unknown hub state, clicking center + back")
        await ClickOp(x=0.5, y=0.5, wait=0.5).run(ctx)
        await ClickOp(x=0.022, y=0.039, wait=1.0).run(ctx)
        ctx.logger.debug("Woke hub UI (unknown state)")
        return OpResult(success=True)
