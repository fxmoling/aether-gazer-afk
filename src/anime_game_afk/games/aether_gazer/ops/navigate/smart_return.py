"""Reliably return to main hub from any page depth.

Composite Action that cycles through multiple escape strategies until
the hub is detected. Uses primitive Ops (ClickOp, PressKeyOp) and
Checks (AtHubCheck) — no direct ctx.device.* calls.

Optimized: one screenshot + one OCR per cycle (via OcrScanCheck),
then reuses the OcrResult for all keyword checks in that cycle.

Strategy per cycle:
1. Check if already at hub (AtHubCheck — template + OCR)
2. Click back button (frac 0.022, 0.039) → re-check hub
3. Press ESC → check for exit dialog (= we're at hub)
4. If screen unchanged after ESC → press Enter (dismiss popup)

Fallback: delegates to WakeHubUiAction after max attempts.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.checks.ocr import OcrScanCheck
from anime_game_afk.games.aether_gazer.checks.page import AtHubCheck
from anime_game_afk.games.aether_gazer.checks.state import ScreenUnchangedCheck
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ENTER, VK_ESCAPE
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.primitives import (
    ClickOp,
    PressKeyOp,
    ScreenshotOp,
    SleepOp,
)


class ReturnToHubAction:
    """Reliably return to hub from any page depth.

    Strategy (cycles until hub detected):
    1. Check if already at hub (AtHubCheck)
    2. Click back button (frac 0.022, 0.039)
    3. Press ESC — closes overlays/panels
    4. Check for exit dialog (= we're at hub already, cancel with ESC)
    5. If screen unchanged → press Enter (dismiss popup)
    """

    def __init__(self, max_attempts: int = 10) -> None:
        self._max_attempts = max_attempts

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.logger.info("[smart_return] Starting return to hub")

        hub_check = AtHubCheck()
        prev_img: np.ndarray | None = None

        for attempt in range(self._max_attempts):
            # ── Step 0: Check if already at hub ──
            # AtHubCheck does: screenshot → template match → OCR fallback
            # This is the only heavy check per cycle start
            hub_result = await hub_check.evaluate(ctx)
            if hub_result.passed:
                ctx.logger.info(
                    f"[smart_return] Hub reached after {attempt} steps"
                )
                return OpResult(
                    success=True,
                    data={"attempts": attempt, "method": hub_result.message},
                )

            # ── Step 1: Try back button (0.022, 0.039) ──
            ctx.logger.debug(
                f"[smart_return][{attempt}] Trying back (0.022, 0.039)"
            )
            await ClickOp(0.022, 0.039, wait=1.5).run(ctx)

            # Quick hub re-check after back click
            hub_result = await hub_check.evaluate(ctx)
            if hub_result.passed:
                ctx.logger.info("[smart_return] Hub reached after back click")
                return OpResult(
                    success=True,
                    data={"attempts": attempt, "method": "back_click"},
                )

            # ── Step 2: Try ESC ──
            ctx.logger.debug(f"[smart_return][{attempt}] Trying ESC")

            # Capture pre-ESC screenshot for unchanged detection
            pre_esc = await ScreenshotOp().run(ctx)
            if pre_esc.success:
                prev_img = pre_esc.data

            await PressKeyOp(VK_ESCAPE, wait=1.5).run(ctx)

            # Check hub after ESC (template + OCR)
            hub_r2 = await hub_check.evaluate(ctx)
            if hub_r2.passed:
                ctx.logger.info("[smart_return] Hub reached after ESC")
                return OpResult(
                    success=True,
                    data={"attempts": attempt, "method": "esc_hub"},
                )

            # Check exit dialog (= we ARE at hub, cancel with ESC)
            ocr_r = await OcrScanCheck().evaluate(ctx)
            if ocr_r.data and (
                ocr_r.data.has("退出游戏") or ocr_r.data.has("是否退出")
            ):
                ctx.logger.info(
                    "[smart_return] Exit dialog detected — at hub, cancelling"
                )
                await PressKeyOp(VK_ESCAPE, wait=1.0).run(ctx)
                return OpResult(
                    success=True,
                    data={"attempts": attempt, "method": "exit_dialog"},
                )

            # ── Step 3: Screen unchanged → press Enter ──
            if prev_img is not None:
                unchanged_r = await ScreenUnchangedCheck(
                    prev_image=prev_img
                ).evaluate(ctx)
                if unchanged_r.passed:
                    ctx.logger.debug(
                        f"[smart_return][{attempt}] Screen unchanged, trying Enter"
                    )
                    await PressKeyOp(VK_ENTER, wait=1.5).run(ctx)

        # ── Final fallback: WakeHubUiAction ──
        ctx.logger.warning("[smart_return] Fallback to WakeHubUiAction")

        from anime_game_afk.games.aether_gazer.ops.navigate.wake_hub_ui import (
            WakeHubUiAction,
        )

        await WakeHubUiAction().run(ctx)
        await SleepOp(1.0).run(ctx)

        return OpResult(
            success=False,
            error="Could not reach hub after max attempts",
            data={"attempts": self._max_attempts},
        )
