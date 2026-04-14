"""Reliably return to main hub from any page depth.

Composite Action that cycles through multiple escape strategies until
the hub is detected. Uses primitive Ops (ClickOp, PressKeyOp) and
Checks (AtHubCheck) — no direct ctx.device.* calls.

Optimized: one screenshot + one OCR per cycle (via OcrScanCheck),
then reuses the OcrResult for all keyword checks in that cycle.

Strategy per cycle:
1. Check if already at hub (AtHubCheck — template + OCR)
2. Click back button (35, 35) → re-check hub
3. Press ESC → check for exit dialog (= we're at hub)
4. If screen unchanged after ESC → press Enter (dismiss popup)

Fallback: delegates to WakeHubUiAction after max attempts.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.checks.page import AtHubCheck
from anime_game_afk.games.aether_gazer.knowledge.constants import (
    BACK_BUTTON_X,
    BACK_BUTTON_Y,
)
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ENTER, VK_ESCAPE
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.primitives import (
    ClickOp,
    PressKeyOp,
    ScreenshotOp,
    SleepOp,
)

import numpy as np


class ReturnToHubAction:
    """Reliably return to hub from any page depth.

    Strategy (cycles until hub detected):
    1. Check if already at hub (AtHubCheck)
    2. Click back button (35, 35)
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

            # ── Step 1: Try back button (35, 35) ──
            ctx.logger.debug(
                f"[smart_return][{attempt}] Trying back "
                f"({BACK_BUTTON_X},{BACK_BUTTON_Y})"
            )
            await ClickOp(BACK_BUTTON_X, BACK_BUTTON_Y, wait=1.5).run(ctx)

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

            # After ESC: one screenshot + one OCR to check everything
            from anime_game_afk.vision.ocr import ocr_once
            from anime_game_afk.games.aether_gazer.ops.perception.identify_page import is_on_page

            post_esc_img = ctx.device.screenshot()

            # Template match for hub
            if is_on_page(post_esc_img, "main_hub"):
                ctx.logger.info("[smart_return] Hub reached after ESC (template)")
                return OpResult(
                    success=True,
                    data={"attempts": attempt, "method": "esc_template"},
                )

            # One OCR pass — check hub keywords + exit dialog
            ocr = ocr_once(post_esc_img)

            # Check hub via OCR (relaxed: 2+ keywords)
            hub_kw = [kw for kw in ("前往作战", "探测", "修正者", "仓库") if ocr.has(kw)]
            if len(hub_kw) >= 2:
                ctx.logger.info(
                    f"[smart_return] Hub reached after ESC "
                    f"(OCR {len(hub_kw)}/4 keywords)"
                )
                return OpResult(
                    success=True,
                    data={"attempts": attempt, "method": "esc_ocr"},
                )

            # Check exit dialog (= we ARE at hub, just cancel)
            if ocr.has("退出游戏") or ocr.has("是否退出"):
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
                diff = float(np.mean(np.abs(
                    post_esc_img.astype(float) - prev_img.astype(float)
                )))
                if diff < 5.0:
                    ctx.logger.debug(
                        f"[smart_return][{attempt}] "
                        f"Screen unchanged (diff={diff:.1f}), trying Enter"
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
