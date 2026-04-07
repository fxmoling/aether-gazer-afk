"""Reliably return to main hub from any page depth.

Composite Op that cycles through multiple escape strategies until
the hub is detected. Uses primitive Ops (ClickOp, PressKeyOp) and
Checks (AtHubCheck, HasTextCheck, ScreenUnchangedCheck) — no direct
ctx.device.* calls.

Strategy per cycle:
1. Check if already at hub (AtHubCheck)
2. Check for idle screen ("正在播放") → click center to wake
3. Click back button (35, 35) → re-check hub
4. Press ESC → re-check hub + exit-dialog detection
5. If screen unchanged after ESC → press Enter (dismiss popup)

Fallback: delegates to WakeHubUiOp + ReturnToHubOp after max attempts.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.checks.ocr import HasTextCheck
from anime_game_afk.games.aether_gazer.checks.page import AtHubCheck
from anime_game_afk.games.aether_gazer.checks.state import ScreenUnchangedCheck
from anime_game_afk.games.aether_gazer.knowledge.constants import (
    BACK_BUTTON_X,
    BACK_BUTTON_Y,
    SCREEN_CENTER_X,
    SCREEN_CENTER_Y,
)
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ENTER, VK_ESCAPE
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.primitives import (
    ClickOp,
    PressKeyOp,
    ScreenshotOp,
    SleepOp,
)


class SmartReturnToHubOp:
    """Reliably return to hub from any page depth.

    Strategy (cycles until hub detected):
    1. Check if already at hub (AtHubCheck)
    2. Click back button (35, 35)
    3. Press ESC — closes overlays/panels
    4. Check for "退出游戏" dialog (= we're at hub already, just cancel)
    5. If screen unchanged → press Enter (dismiss popup)
    """

    def __init__(self, max_attempts: int = 10) -> None:
        self._max_attempts = max_attempts

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.logger.info("[smart_return] Starting return to hub")
        prev_img = None

        hub_check = AtHubCheck()
        screenshot_op = ScreenshotOp()

        for attempt in range(self._max_attempts):
            # ── Step 0: Check if already at hub ──
            hub_result = await hub_check.evaluate(ctx)
            if hub_result.passed:
                ctx.logger.info(
                    f"[smart_return] Hub reached after {attempt} steps"
                )
                return OpResult(
                    success=True,
                    data={"attempts": attempt, "method": hub_result.message},
                )

            # ── Idle screen ("正在播放") — click center to wake ──
            idle_check = HasTextCheck("正在播放")
            idle_result = await idle_check.evaluate(ctx)
            if idle_result.passed:
                ctx.logger.info(
                    f"[smart_return][{attempt}] Idle screen, clicking to wake"
                )
                await ClickOp(SCREEN_CENTER_X, SCREEN_CENTER_Y, wait=1.5).run(ctx)
                continue

            # ── Step 1: Try back button (35, 35) ──
            ctx.logger.debug(
                f"[smart_return][{attempt}] Trying back "
                f"({BACK_BUTTON_X},{BACK_BUTTON_Y})"
            )
            await ClickOp(BACK_BUTTON_X, BACK_BUTTON_Y, wait=1.5).run(ctx)

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
            pre_esc = await screenshot_op.run(ctx)
            if pre_esc.success:
                prev_img = pre_esc.data

            await PressKeyOp(VK_ESCAPE, wait=1.5).run(ctx)

            # Re-check hub after ESC
            hub_result = await hub_check.evaluate(ctx)
            if hub_result.passed:
                ctx.logger.info("[smart_return] Hub reached after ESC")
                return OpResult(
                    success=True,
                    data={"attempts": attempt, "method": "esc"},
                )

            # ── Step 3: Check for exit-game dialog ──
            # ESC at hub triggers "退出游戏" / "是否退出" → we ARE at hub
            exit_check = HasTextCheck("退出游戏")
            exit_result = await exit_check.evaluate(ctx)
            if not exit_result.passed:
                exit_check2 = HasTextCheck("是否退出")
                exit_result = await exit_check2.evaluate(ctx)

            if exit_result.passed:
                ctx.logger.info(
                    "[smart_return] Exit dialog detected — at hub, cancelling"
                )
                await PressKeyOp(VK_ESCAPE, wait=1.0).run(ctx)
                return OpResult(
                    success=True,
                    data={"attempts": attempt, "method": "exit_dialog"},
                )

            # ── Step 4: Screen unchanged → press Enter ──
            if prev_img is not None:
                unchanged_check = ScreenUnchangedCheck(prev_img)
                unchanged_result = await unchanged_check.evaluate(ctx)
                if unchanged_result.passed:
                    diff = unchanged_result.data.get("diff", 0.0)
                    ctx.logger.debug(
                        f"[smart_return][{attempt}] "
                        f"Screen unchanged (diff={diff:.1f}), trying Enter"
                    )
                    await PressKeyOp(VK_ENTER, wait=1.5).run(ctx)

        # ── Final fallback: WakeHubUiOp + ReturnToHubOp ──
        ctx.logger.warning("[smart_return] Fallback to ReturnToHubOp")

        from anime_game_afk.games.aether_gazer.ops.navigate.return_to_hub import (
            ReturnToHubOp,
        )
        from anime_game_afk.games.aether_gazer.ops.navigate.wake_hub_ui import (
            WakeHubUiOp,
        )

        await WakeHubUiOp().run(ctx)
        await SleepOp(0.5).run(ctx)
        await ReturnToHubOp().run(ctx)
        await SleepOp(1.0).run(ctx)

        return OpResult(
            success=False,
            error="Could not reach hub after max attempts",
            data={"attempts": self._max_attempts},
        )
