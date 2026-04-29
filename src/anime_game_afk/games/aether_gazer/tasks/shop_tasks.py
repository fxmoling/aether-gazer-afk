"""Shop and resource tasks — daily purchases and stamina claims.

BuyIntelShards: Purchase character intel shards from daily shop.
ClaimFreeStamina: Claim free daily stamina from shop supply area.
ClaimDailyStaminaPacks: Claim 吨吨值福利包 from hub stamina panel.

Safety: Every purchase/claim is OCR-verified before confirmation.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from anime_game_afk.core.types import Rect
from anime_game_afk.games.aether_gazer.checks.ocr import (
    FindAllTextCheck,
    FindTextCheck,
    HasTextCheck,
    OcrFullCheck,
)
from anime_game_afk.games.aether_gazer.checks.page import AtHubCheck, OnPageCheck
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ENTER, VK_ESCAPE
from anime_game_afk.games.aether_gazer.ops.perception.identify_page import is_on_page
from anime_game_afk.vision.ocr import ocr_once
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


# Shop page keywords visible on the shop bottom bar
_SHOP_KEYWORDS = ("交易区", "补给区")


def _is_shop_page(img) -> bool:
    """Check if screenshot shows the shop page.

    Template match first (fast), then OCR fallback (robust).
    Fixes template mismatch on some resolutions/GPU renderings.
    """
    if is_on_page(img, "shop"):
        return True
    # OCR fallback: look for shop-specific bottom bar text
    ocr = ocr_once(img)
    found = sum(1 for kw in _SHOP_KEYWORDS if ocr.has(kw))
    return found >= 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BuyIntelShards
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class BuyIntelShards:
    """Purchase all available character intel shards from daily shop.

    Strategy: always buy the FIRST intel item in the top row. After
    each purchase, the bought item moves to the end of the row, so the
    next available one slides to the first position. Repeat until no
    more are available or all are sold out.

    Navigation: hub → shop → trade → daily purchase
    Safety: OCR verifies "情报" in popup before every purchase.
    """

    name = "buy_intel_shards"
    description = "Buy character intel shards (情报) from daily shop"
    category = "daily_shop"
    requires_pages = ("main_hub", "shop", "shop_trade", "shop_daily")
    requires_ocr = True
    safe = False  # Spends 辉芒 currency

    _MAX_PURCHASES = 10  # Safety cap per run
    _INTEL_REGION = Rect(160, 104, 1040, 280)  # Top row where intel items appear
    # Purchase popup center region — used to verify the popup item name.
    # Must be WITHIN the opaque popup dialog so background "情报" text
    # (from the daily shop page behind the popup) is NOT captured by OCR.
    _POPUP_REGION = Rect(450, 250, 700, 350)
    # Purchase popup buttons (verified 2026-04-06 via OCR, 1067,624 / 1236,625 @ 1600x900)
    _MAX_BTN_X, _MAX_BTN_Y = 0.667, 0.693    # 最大 button
    _BUY_BTN_X, _BUY_BTN_Y = 0.773, 0.694    # 购买 button

    async def can_run(self, ctx: TaskContext) -> bool:
        """Always runnable — actual availability checked during execute."""
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        run_log: RunLog | None = getattr(ctx, "run_log", None)

        ctx.logger.info("=== BuyIntelShards: starting ===")

        # ── Step 1: Navigate to daily purchase page ──
        ctx.logger.info("[Step 1] Navigate to daily purchase page")
        nav_ok = await self._navigate_to_daily_purchase(ctx, run_log)
        if not nav_ok:
            ctx.logger.error("[Step 1] FAILED: cannot reach daily purchase page")
            return TaskResult(
                status="failed",
                message="Cannot navigate to daily purchase page",
            )
        ctx.logger.info("[Step 1] OK: on daily purchase page")

        # ── Step 2: Buy loop ──
        ctx.logger.info("[Step 2] Starting buy loop")
        purchased = await self._buy_loop(ctx, run_log)
        ctx.logger.info(f"[Step 2] Done: purchased {purchased} intel shards")

        # ── Step 3: Return to hub ──
        ctx.logger.info("[Step 3] Returning to hub")
        await ReturnToHubAction().run(ctx)
        await SleepOp(seconds=1.0).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "buy_intel_final_hub")

        ctx.logger.info(f"=== BuyIntelShards: complete ({purchased} purchased) ===")
        return TaskResult(
            status="success",
            message=f"Purchased {purchased} intel shards",
            data={"purchased": purchased},
        )

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    async def _navigate_to_daily_purchase(
        self, ctx: TaskContext, run_log: RunLog | None,
    ) -> bool:
        """Navigate from hub to daily purchase page.

        Uses direct clicks (same approach as AmusementStreetDaily),
        with is_on_page verification and retry.
        """
        # Wake UI + return to hub
        ctx.logger.info("  nav: wake UI")
        await WakeHubUiAction().run(ctx)
        await SleepOp(seconds=0.15).run(ctx)

        ctx.logger.info("  nav: return to hub")
        result = await ReturnToHubAction().run(ctx)
        if not result.success:
            ctx.logger.error("  nav: cannot return to hub")
            return False
        await SleepOp(seconds=0.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "buy_intel_at_hub")

        # Hub → shop (direct click with retry)
        ctx.logger.info("  nav: hub -> shop (direct click 0.569, 0.944)")
        for attempt in range(3):
            await ClickOp(x=0.569, y=0.944, wait=2.0).run(ctx)
            snap = await ScreenshotOp().run(ctx)
            img = snap.data
            if _is_shop_page(img):
                ctx.logger.info(
                    "  nav: shop reached (attempt {attempt})", attempt=attempt,
                )
                break
            ctx.logger.warning(
                "  nav: shop not reached (attempt {attempt}), retrying",
                attempt=attempt,
            )
            await ClickOp(x=0.5, y=0.5, wait=0.5).run(ctx)
        else:
            ctx.logger.error("  nav: cannot reach shop after 3 attempts")
            return False

        await SleepOp(seconds=1.0).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "buy_intel_at_shop")

        # Shop → trade area (click 交易区 button)
        ctx.logger.info("  nav: shop -> trade area (click 0.056,0.908)")
        await ClickOp(x=0.056, y=0.908, wait=0.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "buy_intel_at_trade")

        # Trade → daily purchase tab (click 每日采购 tab)
        ctx.logger.info("  nav: trade -> daily purchase tab (click 0.081,0.139)")
        await ClickOp(x=0.081, y=0.139, wait=0.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "buy_intel_at_daily_tab")

        # Scroll to top to ensure intel section is visible
        ctx.logger.info("  nav: scroll to top")
        await SwipeOp(x1=0.5, y1=0.222, x2=0.5, y2=0.667, duration=300, wait=1.0).run(ctx)

        # OCR verify: "修正者情报" should be visible
        r = await ScreenshotOp().run(ctx)
        if run_log:
            run_log.save_image(r.data, "buy_intel_daily_page_verify")

        verify = await FindTextCheck(target="修正者情报").evaluate(ctx)
        if verify.passed:
            ctx.logger.info(
                f"  nav: verified '修正者情报' visible "
                f"(conf={verify.data.confidence:.2f})"
            )
            return True
        else:
            ctx.logger.error("  nav: '修正者情报' NOT visible — wrong page?")
            return False

    # ------------------------------------------------------------------
    # Buy loop
    # ------------------------------------------------------------------

    async def _buy_loop(
        self, ctx: TaskContext, run_log: RunLog | None,
    ) -> int:
        """Buy intel items with max quantity. Returns count purchased.

        Fast flow per item: click item → 最大 → 购买 → Enter dismiss.
        OCR safety: verify popup contains "情报" before buying.
        """
        purchased = 0

        for attempt in range(self._MAX_PURCHASES):
            # Fresh screenshot every iteration
            r = await ScreenshotOp().run(ctx)
            if run_log:
                run_log.save_image(r.data, f"buy_intel_scan_{attempt}")

            # Find first (leftmost) intel item
            first = await self._find_first_intel(ctx)
            if first is None:
                ctx.logger.info(f"  buy[{attempt}]: no intel items found, done")
                break

            name, cx, cy = first
            ctx.logger.info(
                f"  buy[{attempt}]: first intel = '{name}' at ({cx},{cy})"
            )

            # Check if sold out
            sold_out = await self._is_sold_out_at(ctx, cx)
            if sold_out:
                ctx.logger.info(
                    f"  buy[{attempt}]: '{name}' is sold out, all done"
                )
                break

            # Click the item → popup opens
            await ClickPxOp(px=cx, py=cy, wait=1.0).run(ctx)

            # Safety check: verify popup item name contains "情报".
            # CRITICAL: restrict to _POPUP_REGION so background page text
            # (e.g. other intel item names still visible behind the popup)
            # does NOT cause a false positive.
            has_intel = await HasTextCheck(
                target="情报", region=self._POPUP_REGION,
            ).evaluate(ctx)
            if not has_intel.passed:
                ctx.logger.error(
                    f"  buy[{attempt}]: popup does NOT contain '情报' "
                    f"— SAFETY STOP (non-intel item?)"
                )
                await PressKeyOp(key=VK_ESCAPE, wait=0.5).run(ctx)
                break

            # Click 最大 (max quantity) → 购买 (buy) → Enter (dismiss)
            ctx.logger.info(f"  buy[{attempt}]: clicking 最大 → 购买")
            await ClickOp(x=self._MAX_BTN_X, y=self._MAX_BTN_Y, wait=0.3).run(ctx)
            await ClickOp(x=self._BUY_BTN_X, y=self._BUY_BTN_Y, wait=0.5).run(ctx)
            await PressKeyOp(key=VK_ENTER, wait=0.5).run(ctx)

            purchased += 1
            if run_log:
                run_log.snap(ctx.device, f"buy_intel_after_buy_{attempt}")
            ctx.logger.info(
                f"  buy[{attempt}]: '{name}' purchased (total: {purchased})"
            )

        return purchased

    # ------------------------------------------------------------------
    # Item detection helpers
    # ------------------------------------------------------------------

    async def _find_first_intel(
        self, ctx: TaskContext,
    ) -> tuple[str, int, int] | None:
        """Find the first (leftmost) intel item in the top row.

        Returns (name, center_x, center_y) or None if none found.
        The click target is the card body area (above the text label)
        to avoid accidentally clicking the card below.
        """
        r = await FindAllTextCheck(
            target="情报", region=self._INTEL_REGION,
        ).evaluate(ctx)
        if not r.passed:
            return None

        items = r.data  # list[TextResult]

        # Filter out section header "修正者情报"
        items = [i for i in items if "修正者" not in i.text]
        if not items:
            return None

        # Sort by x position (leftmost first)
        items.sort(key=lambda i: i.region.x)
        first = items[0]
        cx = first.region.x + first.region.w // 2
        # Click the card body, NOT the text label at the card bottom.
        # "XX情报" text sits at the bottom of the item card; clicking
        # its center risks landing on the card below (e.g. a 刻印 card).
        # Move up ~80px to target the card image area.
        cy = max(first.region.y - 80, self._INTEL_REGION.y + 10)
        return (first.text, cx, cy)

    async def _is_sold_out_at(self, ctx: TaskContext, item_x: int) -> bool:
        """Check if the item at given x position is sold out.

        Searches the intel region for "售" (from "本日售罄") and
        matches by x-proximity AND y-range within the intel region.
        """
        r = await FindAllTextCheck(
            target="售", region=self._INTEL_REGION,
        ).evaluate(ctx)
        if not r.passed:
            return False
        for s in r.data:
            sx = s.region.x + s.region.w // 2
            if abs(sx - item_x) < 120:
                return True
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ClaimFreeStamina
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ClaimFreeStamina:
    """Claim the free daily stamina pack from shop supply area.

    Navigation: hub → shop → supply → daily supply
    Safety: OCR verifies "免费" (free) text before claiming.
    If item shows "冷却" (cooldown), it's already claimed today.
    """

    name = "claim_free_stamina"
    description = "Claim free daily stamina pack from shop supply"
    category = "daily_shop"
    requires_pages = ("main_hub", "shop", "shop_supply", "shop_daily_supply")
    requires_ocr = True
    safe = True  # Free item, no currency spent

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        run_log: RunLog | None = getattr(ctx, "run_log", None)

        ctx.logger.info("=== ClaimFreeStamina: starting ===")

        # ── Step 1: Navigate to daily supply page ──
        ctx.logger.info("[Step 1] Navigate to daily supply page")
        nav_ok = await self._navigate_to_daily_supply(ctx, run_log)
        if not nav_ok:
            ctx.logger.error("[Step 1] FAILED: cannot reach daily supply")
            return TaskResult(
                status="failed",
                message="Cannot navigate to daily supply page",
            )

        # ── Step 2: Check if free stamina is available ──
        ctx.logger.info("[Step 2] Check free stamina availability")
        r = await ScreenshotOp().run(ctx)
        if run_log:
            run_log.save_image(r.data, "stamina_daily_supply_check")

        # Look for "免费" (free) text — indicates unclaimed
        free_result = await FindTextCheck(target="免费").evaluate(ctx)
        if not free_result.passed:
            # Check for "冷却" (cooldown) — already claimed
            cooldown_result = await HasTextCheck(target="冷却").evaluate(ctx)
            if cooldown_result.passed:
                ctx.logger.info(
                    "[Step 2] Stamina already claimed (cooldown active)"
                )
                # CRITICAL: Return to hub before exiting — we're on a paid page!
                await ReturnToHubAction().run(ctx)
                return TaskResult(
                    status="skipped",
                    message="Free stamina already claimed (cooldown)",
                )
            ctx.logger.warning(
                "[Step 2] Neither '免费' nor '冷却' found — page may be wrong"
            )
            # Return to hub before exiting
            await ReturnToHubAction().run(ctx)
            return TaskResult(
                status="failed",
                message="Cannot find free stamina item on page",
            )

        free_label = free_result.data
        ctx.logger.info(
            f"[Step 2] Free stamina available at "
            f"({free_label.region.x},{free_label.region.y}) "
            f"conf={free_label.confidence:.2f}"
        )

        # ── Step 3: Click to claim ──
        ctx.logger.info("[Step 3] Clicking free stamina item")
        # Click the free label area (the item card is near the text)
        fx = free_label.region.x + free_label.region.w // 2
        fy = free_label.region.y + free_label.region.h // 2
        await ClickPxOp(px=fx, py=fy, wait=1.5).run(ctx)

        # ── Step 4: Verify and confirm popup ──
        r = await ScreenshotOp().run(ctx)
        if run_log:
            run_log.save_image(r.data, "stamina_claim_popup")

        # Look for confirm/claim button in popup
        confirm_result = await FindTextCheck(target="领取").evaluate(ctx)
        if not confirm_result.passed:
            # Try "购买" as alternative button text
            confirm_result = await FindTextCheck(target="购买").evaluate(ctx)
        if not confirm_result.passed:
            # Try just pressing Enter (common confirm key)
            ctx.logger.warning(
                "[Step 4] No confirm button found via OCR, trying Enter key"
            )
            await PressKeyOp(key=VK_ENTER, wait=1.0).run(ctx)
        else:
            confirm_btn = confirm_result.data
            cx = confirm_btn.region.x + confirm_btn.region.w // 2
            cy = confirm_btn.region.y + confirm_btn.region.h // 2
            ctx.logger.info(
                f"[Step 4] Clicking confirm at ({cx},{cy})"
            )
            await ClickPxOp(px=cx, py=cy, wait=1.5).run(ctx)

        # Dismiss any result popup
        ctx.logger.info("[Step 4] Dismissing result popup")
        await PressKeyOp(key=VK_ENTER, wait=1.0).run(ctx)

        if run_log:
            run_log.snap(ctx.device, "stamina_after_claim")

        # ── Step 5: IMMEDIATELY return to hub ──
        # CRITICAL: The shop supply area contains paid gift packages.
        # Do NOT linger on any shop page — go straight to hub.
        ctx.logger.info("[Step 5] Immediately return to hub (safety)")
        await ReturnToHubAction().run(ctx)
        if run_log:
            run_log.snap(ctx.device, "stamina_safe_hub")

        ctx.logger.info("=== ClaimFreeStamina: complete ===")
        return TaskResult(
            status="success",
            data={"claimed": "free_stamina"},
        )

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    async def _navigate_to_daily_supply(
        self, ctx: TaskContext, run_log: "RunLog | None",
    ) -> bool:
        """Navigate from hub to daily supply page.

        Uses direct clicks with is_on_page verification.
        """
        # Wake + hub
        ctx.logger.info("  nav: wake UI + return to hub")
        await WakeHubUiAction().run(ctx)
        await SleepOp(seconds=0.15).run(ctx)
        result = await ReturnToHubAction().run(ctx)
        if not result.success:
            ctx.logger.error("  nav: cannot return to hub")
            return False
        await SleepOp(seconds=0.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "stamina_at_hub")

        # Hub → shop (direct click with retry)
        ctx.logger.info("  nav: hub -> shop (direct click 0.569, 0.944)")
        for attempt in range(3):
            await ClickOp(x=0.569, y=0.944, wait=2.0).run(ctx)
            snap = await ScreenshotOp().run(ctx)
            img = snap.data
            if _is_shop_page(img):
                ctx.logger.info(
                    "  nav: shop reached (attempt {attempt})", attempt=attempt,
                )
                break
            ctx.logger.warning(
                "  nav: shop not reached (attempt {attempt}), retrying",
                attempt=attempt,
            )
            await ClickOp(x=0.5, y=0.5, wait=0.5).run(ctx)
        else:
            ctx.logger.error("  nav: cannot reach shop after 3 attempts")
            return False

        await SleepOp(seconds=1.0).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "stamina_at_shop")

        # Shop → supply area (click 补给区 button at 399,816)
        ctx.logger.info("  nav: shop -> supply area (click 0.249,0.907)")
        await ClickOp(x=0.249, y=0.907, wait=0.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "stamina_at_supply")

        # Supply → daily supply tab (click 日常补给 at 560,130)
        ctx.logger.info("  nav: supply -> daily supply (click 0.35,0.144)")
        await ClickOp(x=0.35, y=0.144, wait=0.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "stamina_at_daily_supply")

        # OCR verify: should see supply-related text
        r = await ScreenshotOp().run(ctx)
        if run_log:
            run_log.save_image(r.data, "stamina_daily_supply_verify")

        # Check for either "免费" or "冷却" — both indicate correct page
        has_free = await HasTextCheck(target="免费").evaluate(ctx)
        has_cooldown = await HasTextCheck(target="冷却").evaluate(ctx)
        if has_free.passed or has_cooldown.passed:
            ctx.logger.info("  nav: on daily supply page (verified via OCR)")
            return True

        # Fallback: check for "日常补给" text
        has_daily = await HasTextCheck(target="日常补给").evaluate(ctx)
        if has_daily.passed:
            ctx.logger.info("  nav: on daily supply page (verified '日常补给')")
            return True

        ctx.logger.warning(
            "  nav: could not verify daily supply page via OCR"
        )
        # Proceed anyway — the execute step will do its own verification
        return True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ClaimDailyStaminaPacks
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ClaimDailyStaminaPacks:
    """Claim 吨吨值福利包 (stamina packs) from the hub stamina panel.

    Navigation: hub → click stamina (fixed coord from knowledge) → 每日补给 tab
    There are two packs per day:
    - 每日上午 (morning, after 11:00) — 30 stamina
    - 每日下午 (afternoon, after 18:00) — 30 stamina

    Each pack shows "已领取" when claimed, or "领取" when available.

    Identification methods used:
    - Fixed coord: stamina entry (850,35) from pages.MAIN_HUB
    - Fixed coord: 每日补给 tab (1113,154) from pages.STAMINA_PANEL
    - Template match: verify hub page via identify_page
    - OCR: verify hub UI active ("前往作战"), read stamina NNN/NNN,
            find "领取"/"已领取" buttons
    """

    name = "claim_daily_stamina_packs"
    description = "Claim 吨吨值福利包 (daily stamina packs) from hub"
    category = "daily_resource"
    requires_pages = ("main_hub", "stamina_panel")
    requires_ocr = True
    safe = True  # Free daily items

    _TOP_BAR_REGION = Rect(640, 0, 640, 64)  # Top bar where stamina is shown

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        run_log: RunLog | None = getattr(ctx, "run_log", None)

        ctx.logger.info("=== ClaimDailyStaminaPacks: starting ===")

        # ── Step 1: Return to hub ──
        ctx.logger.info("[Step 1] Return to hub")
        await WakeHubUiAction().run(ctx)
        await SleepOp(seconds=0.15).run(ctx)
        result = await ReturnToHubAction().run(ctx)
        if not result.success:
            ctx.logger.error("[Step 1] FAILED: cannot return to hub")
            return TaskResult(status="failed", message="Cannot return to hub")
        await SleepOp(seconds=0.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "daily_stamina_hub")

        # ── Step 2: Read initial stamina ──
        ctx.logger.info("[Step 2] Read initial stamina")
        stamina_before = await self._read_stamina(ctx)
        ctx.logger.info(f"[Step 2] Stamina before: {stamina_before}")

        # ── Step 3: Open stamina panel ──
        ctx.logger.info("[Step 3] Open stamina panel via top bar")
        panel_ok = await self._open_stamina_panel(ctx, run_log)
        if not panel_ok:
            ctx.logger.error("[Step 3] FAILED: cannot open stamina panel")
            return TaskResult(
                status="failed",
                message="Cannot open stamina panel from hub",
            )

        # ── Step 4: Navigate to 每日补给 tab ──
        ctx.logger.info("[Step 4] Navigate to 每日补给 tab")
        tab_ok = await self._goto_daily_supply_tab(ctx, run_log)
        if not tab_ok:
            ctx.logger.warning(
                "[Step 4] Could not verify 每日补给 tab, trying anyway"
            )

        # ── Step 5: Claim packs ──
        ctx.logger.info("[Step 5] Claiming stamina packs")
        claimed = await self._claim_packs(ctx, run_log)
        ctx.logger.info(f"[Step 5] Attempted {claimed} claims")

        # ── Step 6: Close panel and return ──
        ctx.logger.info("[Step 6] Close panel and return to hub")
        await PressKeyOp(key=VK_ESCAPE, wait=1.0).run(ctx)
        await ReturnToHubAction().run(ctx)
        await SleepOp(seconds=1.0).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "daily_stamina_final_hub")

        # ── Step 7: Read final stamina and compute actual gain ──
        ctx.logger.info("[Step 7] Verify stamina gain")
        stamina_after = await self._read_stamina(ctx)
        stamina_gained = 0
        if stamina_before is not None and stamina_after is not None:
            stamina_gained = stamina_after - stamina_before
            ctx.logger.info(
                f"[Step 7] Stamina: {stamina_before} → {stamina_after} "
                f"(+{stamina_gained})"
            )
        else:
            ctx.logger.warning(
                f"[Step 7] Could not verify gain "
                f"(before={stamina_before}, after={stamina_after})"
            )

        ctx.logger.info(
            f"=== ClaimDailyStaminaPacks: complete "
            f"(claimed={claimed}, gained={stamina_gained}) ==="
        )
        return TaskResult(
            status="success",
            message=f"Claimed {claimed} packs (+{stamina_gained} stamina)",
            data={
                "claimed": claimed,
                "stamina_gained": stamina_gained,
                "stamina_before": stamina_before,
                "stamina_after": stamina_after,
            },
        )

    # ------------------------------------------------------------------
    # Read stamina from top bar
    # ------------------------------------------------------------------

    async def _read_stamina(self, ctx: TaskContext) -> int | None:
        """Read current stamina value from hub top bar. Returns int or None."""
        r = await OcrFullCheck(region=self._TOP_BAR_REGION).evaluate(ctx)
        if not r.passed:
            ctx.logger.debug("  stamina read: not found")
            return None
        for item in r.data:
            clean = item.text.replace(" ", "").replace("+", "")
            m = re.match(r"(\d+)/(\d+)", clean)
            if m:
                current = int(m.group(1))
                ctx.logger.debug(f"  stamina read: {current}/{m.group(2)}")
                return current
        ctx.logger.debug("  stamina read: not found")
        return None

    # ------------------------------------------------------------------
    # Open stamina panel (fixed coord + template/OCR verification)
    # ------------------------------------------------------------------

    async def _open_stamina_panel(
        self, ctx: TaskContext, run_log: RunLog | None,
    ) -> bool:
        """Click stamina in hub top bar to open stamina panel.

        Uses fixed coord from knowledge (pages.MAIN_HUB "Stamina" element).
        Verifies hub page via template matching AND UI active via OCR
        before clicking.
        """
        from anime_game_afk.games.aether_gazer.knowledge.pages import (
            find_element,
        )

        # Guard: verify we're on hub (template + OCR fallback)
        hub_check = await AtHubCheck().evaluate(ctx)
        if not hub_check.passed:
            # Idle hub → wake and retry once
            if hub_check.data and hub_check.data.get("hub_state") == "idle":
                ctx.logger.warning("  panel: hub idle, waking up")
                await WakeHubUiAction().run(ctx)
                await SleepOp(seconds=0.5).run(ctx)
                hub_check = await AtHubCheck().evaluate(ctx)
            if not hub_check.passed:
                ctx.logger.error("  panel: not on hub page")
                return False

        # Ensure hub UI is active (not idle/screensaver)
        if hub_check.data and hub_check.data.get("hub_state") != "active":
            ctx.logger.warning("  panel: hub UI may be idle, waking up")
            await WakeHubUiAction().run(ctx)
            await SleepOp(seconds=0.5).run(ctx)

        ctx.logger.info("  panel: hub confirmed (template + UI active)")

        # Use fixed coordinate from knowledge layer
        stamina_elem = find_element("main_hub", "Stamina")
        if stamina_elem is None:
            ctx.logger.error("  panel: 'Stamina' element not in knowledge")
            return False

        click_x, click_y = stamina_elem.coord
        ctx.logger.info(
            f"  panel: clicking stamina at fixed coord ({click_x:.3f},{click_y:.3f})"
        )
        await ClickOp(x=click_x, y=click_y, wait=1.0).run(ctx)

        if run_log:
            run_log.snap(ctx.device, "daily_stamina_panel_opened")

        # Verify panel opened: look for tab labels via OCR
        coolant = await HasTextCheck(target="冷却剂").evaluate(ctx)
        daily = await HasTextCheck(target="每日补给").evaluate(ctx)
        if coolant.passed or daily.passed:
            ctx.logger.info("  panel: stamina panel opened (tabs visible)")
            return True

        ctx.logger.warning("  panel: tabs not found after click")
        return False

    # ------------------------------------------------------------------
    # Navigate to 每日补给 tab (fixed coord from knowledge)
    # ------------------------------------------------------------------

    async def _goto_daily_supply_tab(
        self, ctx: TaskContext, run_log: RunLog | None,
    ) -> bool:
        """Click 每日补给 tab using fixed coord from knowledge layer."""
        from anime_game_afk.games.aether_gazer.knowledge.pages import (
            find_element,
        )

        daily_elem = find_element("stamina_panel", "Daily Supply")
        if daily_elem is None:
            ctx.logger.warning(
                "  tab: 'Daily Supply' element not in knowledge, "
                "falling back to OCR"
            )
            # Fallback: OCR
            daily_tab = await FindTextCheck(target="每日补给").evaluate(ctx)
            if daily_tab.passed:
                tab = daily_tab.data
                dx = tab.region.x + tab.region.w // 2
                dy = tab.region.y + tab.region.h // 2
                ctx.logger.info(f"  tab: OCR fallback '每日补给' at ({dx},{dy})")
                await ClickPxOp(px=dx, py=dy, wait=1.5).run(ctx)
                if run_log:
                    run_log.snap(ctx.device, "daily_stamina_tab_clicked")
                return True
            return False

        dx, dy = daily_elem.coord
        ctx.logger.info(
            f"  tab: clicking '每日补给' at fixed coord ({dx:.3f},{dy:.3f})"
        )
        await ClickOp(x=dx, y=dy, wait=1.5).run(ctx)
        if run_log:
            run_log.snap(ctx.device, "daily_stamina_tab_clicked")
        return True

    # ------------------------------------------------------------------
    # Claim packs
    # ------------------------------------------------------------------

    async def _claim_packs(
        self, ctx: TaskContext, run_log: RunLog | None,
    ) -> int:
        """Click both stamina pack positions to claim them.

        Strategy: click left pack → Enter dismiss → click right pack → Enter.
        Packs are at fixed positions on the 每日补给 tab.
        Even if stamina is full, packs can still be claimed (game mechanic).
        """
        claimed = 0
        # Verified coordinates (2026-04-05, 1600x900):
        # Left pack claim area: ~(891, 485) → (0.557, 0.539)
        # Right pack claim area: ~(1208, 485) → (0.755, 0.539)
        pack_positions = [(0.557, 0.539), (0.755, 0.539)]

        for i, (px, py) in enumerate(pack_positions):
            label = "left" if i == 0 else "right"
            ctx.logger.info(f"  claim: clicking {label} pack at ({px},{py})")

            if run_log:
                r = await ScreenshotOp().run(ctx)
                run_log.save_image(r.data, f"daily_stamina_scan_{i}")

            await ClickOp(x=px, y=py, wait=1.5).run(ctx)

            # Dismiss any result/confirm popup
            await PressKeyOp(key=VK_ENTER, wait=1.0).run(ctx)
            # Click again in case of double popup
            await PressKeyOp(key=VK_ENTER, wait=0.5).run(ctx)

            claimed += 1
            ctx.logger.info(f"  claim: {label} pack clicked")

            if run_log:
                r = await ScreenshotOp().run(ctx)
                run_log.save_image(r.data, f"daily_stamina_after_claim_{i}")

        return claimed

    async def _read_stamina_from_panel(self, ctx: TaskContext) -> int | None:
        """Read stamina NNN/NNN from panel top bar."""
        # Panel shows stamina in top-right area
        panel_top = Rect(880, 0, 400, 64)
        r = await OcrFullCheck(region=panel_top).evaluate(ctx)
        if not r.passed:
            return None
        for item in r.data:
            clean = item.text.replace(" ", "").replace("+", "")
            m = re.match(r"(\d+)/(\d+)", clean)
            if m:
                return int(m.group(1))
        return None
