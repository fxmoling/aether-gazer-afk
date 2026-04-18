"""Activity tasks — event-based daily activities.

JointDefenseSweep: Run sweep on 联防协议 (Joint Defense) activity.

Uses mixed identification methods:
- Fixed coord: hub elements, panel buttons (> >>)
- Template match: page identification via OnPageCheck
- OCR (batch via OcrScanCheck): activity names, dynamic text, button states
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from anime_game_afk.core.types import Rect
from anime_game_afk.games.aether_gazer.checks.ocr import OcrScanCheck
from anime_game_afk.games.aether_gazer.checks.page import OnPageCheck
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ENTER, VK_ESCAPE
from anime_game_afk.games.aether_gazer.ops.navigate.smart_return import ReturnToHubAction
from anime_game_afk.games.aether_gazer.ops.navigate.wake_hub_ui import WakeHubUiAction
from anime_game_afk.games.aether_gazer.ops.primitives import (
    ClickPxOp,
    ClickOp,
    PressKeyOp,
    ScreenshotOp,
    SleepOp,
    SwipeOp,
)
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext, TaskResult

if TYPE_CHECKING:
    from anime_game_afk.runtime.run_log import RunLog


class JointDefenseSweep:
    """Sweep the 联防协议 (Joint Defense) activity — 震动 stage.

    Navigation:
        hub → activity page (below H mail shortcut) → 联防协议 (scroll if needed)
        → 前往挑战 → 信息集纳 → 震动 → max multiplier (>>) → 扫荡
        → confirm → dismiss result → return to hub

    Identification methods:
        - Template match: verify hub page
        - OCR (batch): find "前往作战" (hub active), "联防协议" (activity list),
               "前往挑战", "信息集纳", "震动", "扫荡"
        - Fixed coord: H button offset for activity entrance,
                       << / >> button for multiplier (graphical, OCR can't read)

    Verified coordinates (2026-04-06, pixel-mapped):
        - H label: ~(1372, 140), activity entrance: ~(1372, 190)
        - 联防协议: found via OCR + scroll in left column
        - 前往挑战: OCR ~(1440, 839)
        - 信息集纳: OCR ~(1146, 839)
        - 震动: OCR ~(319, 497) on map
        - 掉落倍数 <<: fixed (1180, 712), >>: fixed (1552, 712)
        - 扫荡: OCR ~(1252, 841)
    """

    name = "joint_defense_sweep"
    description = "Sweep 联防协议 (Joint Defense) 震动 stage for drops"
    category = "daily_activity"
    requires_pages = ("main_hub",)
    requires_ocr = True
    safe = False  # Consumes 吨吨值 (30 per sweep)

    # H shortcut label search region (right side of hub)
    # At screenshot resolution (1280×720): x=1040..1200, y=80..160
    _H_SEARCH_REGION = Rect(1040, 80, 160, 80)
    # Activity list left column
    _LEFT_COLUMN = Rect(0, 80, 320, 560)
    # Multiplier buttons: 5-button layout << < [xN] > >>
    # Pixel-mapped from 008_jd_after_max_multi.jpg darkness scan:
    #   << button: half(590,355) = full(1180,710)  ← reset to min
    #   >> button: half(776,355) = full(1552,710)  ← set to max
    _MIN_MULTI_X = 0.738    # 1180 / 1600
    _MIN_MULTI_Y = 0.791    # 712 / 900
    _MAX_MULTI_X = 0.97     # 1552 / 1600
    _MAX_MULTI_Y = 0.791    # 712 / 900
    _MAX_SCROLL_ATTEMPTS = 5

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        run_log: RunLog | None = getattr(ctx, "run_log", None)

        ctx.logger.info("=== JointDefenseSweep: starting ===")

        # ── Step 1: Return to hub ──
        ctx.logger.info("[Step 1] Return to hub")
        await WakeHubUiAction().run(ctx)
        await SleepOp(seconds=0.15).run(ctx)
        result = await ReturnToHubAction().run(ctx)
        if not result.success:
            ctx.logger.error("[Step 1] FAILED: cannot return to hub")
            return TaskResult(status="failed", message="Cannot return to hub")
        await SleepOp(seconds=0.5).run(ctx)

        # Verify hub + UI active (one OCR pass)
        hub_check = await OnPageCheck(page="main_hub").evaluate(ctx)
        if not hub_check.passed:
            ctx.logger.error("[Step 1] Not on hub (template mismatch)")
            return TaskResult(status="failed", message="Not on hub page")
        r = await OcrScanCheck().evaluate(ctx)
        ocr = r.data
        if not ocr.has("前往作战"):
            ctx.logger.warning("[Step 1] Hub UI may be idle, waking")
            await WakeHubUiAction().run(ctx)
            await SleepOp(seconds=0.15).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "jd_hub")

        # ── Step 2: Enter activity page ──
        ctx.logger.info("[Step 2] Enter activity page (below H button)")
        nav_ok = await self._enter_activity_page(ctx, run_log)
        if not nav_ok:
            ctx.logger.error("[Step 2] FAILED: cannot enter activity page")
            return TaskResult(
                status="failed", message="Cannot enter activity page"
            )

        # ── Step 3: Find and click 联防协议 ──
        ctx.logger.info("[Step 3] Find '联防协议' in activity list")
        jd_ok = await self._find_and_click_joint_defense(ctx, run_log)
        if not jd_ok:
            ctx.logger.error("[Step 3] FAILED: '联防协议' not found")
            await self._safe_return_to_hub(ctx)
            return TaskResult(
                status="failed", message="联防协议 not found in activity list"
            )

        # ── Step 4: Click 前往挑战 ──
        ctx.logger.info("[Step 4] Click '前往挑战'")
        challenge_ok = await self._click_challenge(ctx, run_log)
        if not challenge_ok:
            ctx.logger.error("[Step 4] FAILED: challenge button not found")
            await self._safe_return_to_hub(ctx)
            return TaskResult(
                status="failed", message="Challenge button not found"
            )

        # ── Step 5: Click 信息集纳 ──
        ctx.logger.info("[Step 5] Click '信息集纳'")
        await self._click_info_collection(ctx, run_log)

        # ── Step 6: Click 震动 ──
        ctx.logger.info("[Step 6] Click '震动'")
        quake_ok = await self._click_quake(ctx, run_log)
        if not quake_ok:
            ctx.logger.error("[Step 6] FAILED: '震动' not found")
            await self._safe_return_to_hub(ctx)
            return TaskResult(status="failed", message="震动 not found on map")

        # ── Step 7: Max multiplier + sweep ──
        ctx.logger.info("[Step 7] Max multiplier and sweep")
        sweep_ok = await self._max_multi_and_sweep(ctx, run_log)
        if not sweep_ok:
            ctx.logger.error("[Step 7] FAILED: sweep failed")
            await self._safe_return_to_hub(ctx)
            return TaskResult(status="failed", message="Sweep failed")

        # ── Step 8: Confirm and dismiss ──
        ctx.logger.info("[Step 8] Confirm sweep and dismiss result")
        await self._confirm_and_dismiss(ctx, run_log)

        # ── Step 9: Collect 联防协议 rewards ──
        ctx.logger.info("[Step 9] Navigate back to collect 联防协议 rewards")
        await self._collect_joint_defense_rewards(ctx, run_log)

        # ── Step 10: Return to hub ──
        ctx.logger.info("[Step 10] Return to hub")
        await self._safe_return_to_hub(ctx)
        if run_log:
            run_log.snap(ctx.device, "jd_final_hub")

        ctx.logger.info("=== JointDefenseSweep: complete ===")
        return TaskResult(
            status="success",
            message="Joint Defense sweep completed",
            data={"stage": "震动"},
        )

    # ------------------------------------------------------------------
    # Step 2: Enter activity page
    # ------------------------------------------------------------------

    async def _enter_activity_page(
        self, ctx: TaskContext, run_log: RunLog | None,
    ) -> bool:
        """Find H label in hub, click ~50px below to enter activity page."""
        # Find "H" label via OCR (small region for speed)
        r = await OcrScanCheck(region=self._H_SEARCH_REGION).evaluate(ctx)
        h_label = None
        if r.passed:
            ocr = r.data
            for item in ocr.items:
                if item.text.strip() == "H":
                    h_label = item
                    break

        if h_label:
            hx = h_label.region.x + h_label.region.w // 2
            hy = h_label.region.y + h_label.region.h // 2
            click_px = hx
            click_py = hy + 50  # Activity entrance is ~50px below H
            ctx.logger.info(
                f"  nav: H found at ({hx},{hy}), "
                f"clicking activity at ({click_px},{click_py})"
            )
            await ClickPxOp(px=click_px, py=click_py, wait=0.5).run(ctx)
        else:
            # Fallback from verified data
            click_x, click_y = 0.858, 0.211  # 1372,190 @ 1600x900
            ctx.logger.warning(
                f"  nav: H not found via OCR, "
                f"using fallback ({click_x},{click_y})"
            )
            await ClickOp(x=click_x, y=click_y, wait=0.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "jd_activity_page")

        # Verify: one OCR pass to check for activity page keywords
        r = await OcrScanCheck().evaluate(ctx)
        if r.passed:
            ocr = r.data
            if ocr.has("前往挑战") or ocr.has("福利") or ocr.has("支线") or ocr.has("协议"):
                ctx.logger.info("  nav: activity page verified")
                return True

        ctx.logger.warning("  nav: could not verify activity page")
        return True  # Proceed anyway — later steps have their own verification

    # ------------------------------------------------------------------
    # Step 3: Find and click 联防协议
    # ------------------------------------------------------------------

    async def _find_and_click_joint_defense(
        self, ctx: TaskContext, run_log: RunLog | None,
    ) -> bool:
        """Find '联防协议' in activity list, scrolling if needed."""
        r = await OcrScanCheck().evaluate(ctx)
        ocr = r.data if r.passed else None
        found = ocr.find("联防协议") if ocr else None

        # Scroll down to find
        scroll_down = 0
        while found is None and scroll_down < self._MAX_SCROLL_ATTEMPTS:
            ctx.logger.info(
                f"  search: scrolling down ({scroll_down + 1}/"
                f"{self._MAX_SCROLL_ATTEMPTS})"
            )
            await SwipeOp(
                x1=0.125, y1=0.667, x2=0.125, y2=0.333, duration=300, wait=2.0,
            ).run(ctx)
            if run_log:
                snap_r = await ScreenshotOp().run(ctx)
                run_log.save_image(snap_r.data, f"jd_scroll_down_{scroll_down}")
            r = await OcrScanCheck().evaluate(ctx)
            ocr = r.data if r.passed else None
            found = ocr.find("联防协议") if ocr else None
            scroll_down += 1

        # Scroll back up if not found
        if found is None:
            ctx.logger.info("  search: not found scrolling down, scrolling up")
            for i in range(self._MAX_SCROLL_ATTEMPTS + scroll_down):
                await SwipeOp(
                    x1=0.125, y1=0.333, x2=0.125, y2=0.667, duration=300, wait=2.0,
                ).run(ctx)
                if run_log:
                    snap_r = await ScreenshotOp().run(ctx)
                    run_log.save_image(snap_r.data, f"jd_scroll_up_{i}")
                r = await OcrScanCheck().evaluate(ctx)
                ocr = r.data if r.passed else None
                found = ocr.find("联防协议") if ocr else None
                if found:
                    break

        if found is None:
            ctx.logger.error("  search: '联防协议' not found after scrolling")
            return False

        jdx = found.region.x + found.region.w // 2
        jdy = found.region.y + found.region.h // 2
        ctx.logger.info(
            f"  search: '联防协议' found at ({jdx},{jdy}) "
            f"conf={found.confidence:.2f}"
        )
        await ClickPxOp(px=jdx, py=jdy, wait=0.5).run(ctx)

        if run_log:
            run_log.snap(ctx.device, "jd_panel")

        # Verify: right panel should show "联防协议"
        r = await OcrScanCheck().evaluate(ctx)
        if r.passed and r.data.has("联防协议"):
            ctx.logger.info("  search: right panel verified '联防协议'")
        else:
            ctx.logger.warning("  search: could not verify right panel")
        return True

    # ------------------------------------------------------------------
    # Step 4: Click 前往挑战
    # ------------------------------------------------------------------

    async def _click_challenge(
        self, ctx: TaskContext, run_log: RunLog | None,
    ) -> bool:
        """Click 前往挑战 button."""
        r = await OcrScanCheck().evaluate(ctx)
        if not r.passed:
            ctx.logger.error("  challenge: OCR scan failed")
            return False
        ocr = r.data
        btn = ocr.find("前往挑战")
        if btn is None:
            btn = ocr.find("挑战")
        if btn is None:
            ctx.logger.error("  challenge: button not found")
            return False

        cx = btn.region.x + btn.region.w // 2
        cy = btn.region.y + btn.region.h // 2
        ctx.logger.info(f"  challenge: clicking '{btn.text}' at ({cx},{cy})")
        await ClickPxOp(px=cx, py=cy, wait=1.0).run(ctx)

        # Handle "前置章节" story prompt — dismiss with ESC (取消)
        r = await OcrScanCheck().evaluate(ctx)
        if r.passed:
            check_ocr = r.data
            if check_ocr.has("前置章节") or check_ocr.has("剧情观感"):
                ctx.logger.info("  challenge: story prompt detected, pressing ESC")
                await PressKeyOp(key=VK_ESCAPE, wait=0.5).run(ctx)

        if run_log:
            run_log.snap(ctx.device, "jd_after_challenge")
        return True

    # ------------------------------------------------------------------
    # Step 5: Click 信息集纳
    # ------------------------------------------------------------------

    async def _click_info_collection(
        self, ctx: TaskContext, run_log: RunLog | None,
    ) -> None:
        """Click 信息集纳 button (may already be selected)."""
        r = await OcrScanCheck().evaluate(ctx)
        if not r.passed:
            ctx.logger.info("  info: OCR scan failed, skipping")
            if run_log:
                run_log.snap(ctx.device, "jd_info_collection")
            return
        ocr = r.data
        btn = ocr.find("信息集纳")
        if btn is None:
            btn = ocr.find("集纳")
        if btn:
            cx = btn.region.x + btn.region.w // 2
            cy = btn.region.y + btn.region.h // 2
            ctx.logger.info(
                f"  info: clicking '{btn.text}' at ({cx},{cy})"
            )
            await ClickPxOp(px=cx, py=cy, wait=0.3).run(ctx)
        else:
            ctx.logger.info("  info: '信息集纳' not found, may already be selected")
        if run_log:
            run_log.snap(ctx.device, "jd_info_collection")

    # ------------------------------------------------------------------
    # Step 6: Click 震动
    # ------------------------------------------------------------------

    async def _click_quake(
        self, ctx: TaskContext, run_log: RunLog | None,
    ) -> bool:
        """Click '震动' node on the map."""
        r = await OcrScanCheck().evaluate(ctx)
        if not r.passed:
            ctx.logger.error("  quake: OCR scan failed")
            return False
        ocr = r.data
        quake = ocr.find("震动")
        if quake is None:
            ctx.logger.error("  quake: '震动' not found on map")
            return False

        cx = quake.region.x + quake.region.w // 2
        cy = quake.region.y + quake.region.h // 2
        ctx.logger.info(f"  quake: clicking '震动' at ({cx},{cy})")
        await ClickPxOp(px=cx, py=cy, wait=1.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "jd_battle_panel")
        return True

    # ------------------------------------------------------------------
    # Step 7: Max multiplier and sweep
    # ------------------------------------------------------------------

    async def _max_multi_and_sweep(
        self, ctx: TaskContext, run_log: RunLog | None,
    ) -> bool:
        """Set multiplier to max available, then click 扫荡.

        Strategy: click << (min) to reset, then >> (max) to set highest
        affordable multiplier. This ensures a clean reset before maximizing.
        Note: at x1, << is not visible, but clicking its position is harmless.
        If the panel closes unexpectedly, re-click 震动 to reopen it.
        """
        # First verify the battle panel is still open
        r = await OcrScanCheck().evaluate(ctx)
        ocr = r.data if r.passed else None
        if ocr is None or not ocr.has("扫荡"):
            ctx.logger.warning(
                "  multi: battle panel not open, re-clicking 震动"
            )
            if ocr:
                quake = ocr.find("震动")
                if quake:
                    cx = quake.region.x + quake.region.w // 2
                    cy = quake.region.y + quake.region.h // 2
                    await ClickPxOp(px=cx, py=cy, wait=2.0).run(ctx)

        # Step 1: Click << (min) to reset multiplier
        ctx.logger.info(
            f"  multi: clicking << (min) at "
            f"({self._MIN_MULTI_X},{self._MIN_MULTI_Y})"
        )
        await ClickOp(x=self._MIN_MULTI_X, y=self._MIN_MULTI_Y, wait=0.3).run(ctx)

        # Step 2: Click >> (max) to raise to highest affordable multiplier
        ctx.logger.info(
            f"  multi: clicking >> (max) at "
            f"({self._MAX_MULTI_X},{self._MAX_MULTI_Y})"
        )
        await ClickOp(x=self._MAX_MULTI_X, y=self._MAX_MULTI_Y, wait=0.5).run(ctx)

        snap_r = await ScreenshotOp().run(ctx)
        if run_log:
            run_log.save_image(snap_r.data, "jd_after_max_multi")

        # One OCR pass for multiplier + sweep button
        r = await OcrScanCheck().evaluate(ctx)
        ocr = r.data if r.passed else None
        if ocr:
            multi_text = ocr.find("x")
            if multi_text:
                ctx.logger.info(
                    f"  multi: multiplier now '{multi_text.text}'"
                )

        # Find and click 扫荡
        sweep = ocr.find("扫荡") if ocr else None
        if sweep is None:
            # Panel may have closed — try reopening
            ctx.logger.warning("  sweep: '扫荡' not found, trying to reopen panel")
            if ocr:
                quake = ocr.find("震动")
                if quake:
                    cx = quake.region.x + quake.region.w // 2
                    cy = quake.region.y + quake.region.h // 2
                    await ClickPxOp(px=cx, py=cy, wait=2.0).run(ctx)
                    await ClickOp(
                        x=self._MIN_MULTI_X, y=self._MIN_MULTI_Y, wait=0.3,
                    ).run(ctx)
                    await ClickOp(
                        x=self._MAX_MULTI_X, y=self._MAX_MULTI_Y, wait=0.5,
                    ).run(ctx)
                    r = await OcrScanCheck().evaluate(ctx)
                    ocr = r.data if r.passed else None
                    sweep = ocr.find("扫荡") if ocr else None

        if sweep is None:
            ctx.logger.error("  sweep: '扫荡' button still not found")
            return False

        sx = sweep.region.x + sweep.region.w // 2
        sy = sweep.region.y + sweep.region.h // 2
        ctx.logger.info(f"  sweep: clicking '扫荡' at ({sx},{sy})")
        await ClickPxOp(px=sx, py=sy, wait=0.3).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "jd_sweep_confirm")
        return True

    # ------------------------------------------------------------------
    # Step 8: Confirm and dismiss result
    # ------------------------------------------------------------------

    async def _confirm_and_dismiss(
        self, ctx: TaskContext, run_log: RunLog | None,
    ) -> None:
        """Confirm sweep popup and dismiss result screen.

        Flow:
        1. Sweep confirm popup → Enter (确定)
        2. Wait for sweep animation (~1s)
        3. Check for stamina-insufficient popup (补充吨吨值) → ESC to cancel
        4. Sweep result screen ("扫荡完成") → Enter (确认, NOT 再次扫荡)
           Note: ESC does NOT work on result screen, only Enter.
        """
        # 1. Confirm sweep popup
        ctx.logger.info("  confirm: pressing Enter to confirm sweep")
        await PressKeyOp(key=VK_ENTER, wait=1.0).run(ctx)

        if run_log:
            run_log.snap(ctx.device, "jd_sweep_result")

        # 2. Check for stamina-insufficient popup (one OCR pass)
        r = await OcrScanCheck().evaluate(ctx)
        if r.passed:
            ocr = r.data
            if ocr.has("补充") or ocr.has("冷却剂") or ocr.has("吨吨值"):
                ctx.logger.info(
                    "  confirm: stamina-insufficient popup detected, "
                    "pressing ESC to cancel"
                )
                await PressKeyOp(key=VK_ESCAPE, wait=0.5).run(ctx)
                if run_log:
                    run_log.snap(ctx.device, "jd_stamina_popup_canceled")
                return  # Don't try to dismiss result — sweep didn't happen

        # 3. Dismiss result screen with Enter (= 确认 button)
        ctx.logger.info("  confirm: pressing Enter to dismiss result (确认)")
        await PressKeyOp(key=VK_ENTER, wait=1.5).run(ctx)

        # 4. Verify we left the result screen (one OCR pass)
        r = await OcrScanCheck().evaluate(ctx)
        if r.passed:
            ocr = r.data
            if ocr.has("扫荡完成") or ocr.has("再次"):
                ctx.logger.info("  confirm: still on result page, Enter again")
                await PressKeyOp(key=VK_ENTER, wait=1.0).run(ctx)

        if run_log:
            run_log.snap(ctx.device, "jd_after_dismiss")

    # ------------------------------------------------------------------
    # Step 9: Collect 联防协议 rewards
    # ------------------------------------------------------------------

    async def _collect_joint_defense_rewards(
        self, ctx: TaskContext, run_log: RunLog | None,
    ) -> None:
        """Navigate back to 联防协议 detail page and click 一键领取 rewards.

        After sweep dismissal, press back to return to the 联防协议 detail
        page (where 前往挑战 was visible), then click the bottom-most orange
        一键领取 button to claim all completion rewards.
        """
        # Navigate back from challenge map to 联防协议 detail page
        for i in range(4):
            ctx.logger.info(f"  rewards: pressing back [{i}]")
            await ClickOp(x=0.022, y=0.039, wait=1.0).run(ctx)

            # Check if we see 前往挑战 — means we're on 联防协议 detail page
            r = await OcrScanCheck().evaluate(ctx)
            if r.passed and r.data.has("前往挑战"):
                ctx.logger.info("  rewards: reached 联防协议 detail page")
                break
        else:
            ctx.logger.warning(
                "  rewards: could not reach 联防协议 detail page"
            )
            return

        # Click bottom-most reward claim button (right side of task list)
        # Verified from 07_joint_defense_detail.png — blue arrow icon at right
        _REWARD_CLAIM_X, _REWARD_CLAIM_Y = 0.934, 0.829
        ctx.logger.info(
            f"  rewards: clicking bottom 一键领取 at "
            f"({_REWARD_CLAIM_X},{_REWARD_CLAIM_Y})"
        )
        await ClickOp(x=_REWARD_CLAIM_X, y=_REWARD_CLAIM_Y, wait=1.5).run(ctx)

        # Dismiss any reward popup
        await PressKeyOp(key=VK_ENTER, wait=1.0).run(ctx)

        if run_log:
            run_log.snap(ctx.device, "jd_rewards_collected")

    # ------------------------------------------------------------------
    # Safe return to hub
    # ------------------------------------------------------------------

    async def _safe_return_to_hub(self, ctx: TaskContext) -> None:
        """Return to hub from any depth in the activity flow.

        Alternates between back button (35,35) and ESC, since some
        pages only respond to one or the other. Checks for hub after
        each attempt via template matching.
        """
        ctx.logger.info("  return: navigating back to hub")
        for i in range(8):
            hub_check = await OnPageCheck(page="main_hub").evaluate(ctx)
            if hub_check.passed:
                ctx.logger.info(f"  return: hub reached after {i} actions")
                return

            # Alternate: even = back button, odd = ESC
            if i % 2 == 0:
                ctx.logger.debug(f"  return: clicking back (0.022,0.039) [{i}]")
                await ClickOp(x=0.022, y=0.039, wait=1.0).run(ctx)
            else:
                ctx.logger.debug(f"  return: pressing ESC [{i}]")
                await PressKeyOp(key=VK_ESCAPE, wait=1.0).run(ctx)

        # Final fallback
        ctx.logger.info("  return: using ReturnToHubAction as fallback")
        await ReturnToHubAction().run(ctx)
        await SleepOp(seconds=1.0).run(ctx)
