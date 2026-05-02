"""刻印 tab tasks — activities under the 刻印 (Keyin) tab.

Contains:
- MediumSeizureCombat: 介质攫取 — combat + reward claim
- JointSpecialOpsSweep: 联合特勤 — find S-rank and sweep

Shared navigation: hub → 前往作战 → 刻印 tab → node

OCR-verified coordinates (2026-04-19, 1280×720):
    前往作战:   (0.912, 0.936)
    刻印 tab:   (0.669, 0.919)
    介质攫取:   OCR two-state logic (see _navigate_to_interior)
    开始挑战:   (0.797, 0.911)
    奖励领取:   (0.104, 0.913)
    一键领取:   (0.811, 0.924)
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ENTER, VK_ESCAPE
from anime_game_afk.games.aether_gazer.ops.navigate.smart_return import (
    ReturnToHubAction,
)
from anime_game_afk.games.aether_gazer.ops.navigate.wake_hub_ui import WakeHubUiAction
from anime_game_afk.games.aether_gazer.ops.primitives import (
    ClickOp,
    PressKeyOp,
    ScreenshotOp,
    SleepOp,
)
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext, TaskResult
from anime_game_afk.vision.ocr import ocr_once


class MediumSeizureCombat:
    """Run 介质攫取 (Medium Seizure): one combat + claim rewards.

    Flow:
        1. Wake hub + return to hub
        2. Navigate: hub → 前往作战 → 刻印 → 介质攫取 interior
        3. Start challenge → passive battle (wait for completion)
        4. Claim rewards via 奖励领取 → 一键领取
        5. Return to hub
    """

    name = "medium_seizure_combat"
    description = "介质攫取: fight one battle and claim score rewards"
    category = "daily_activity"
    requires_pages = ("main_hub", "battle_select")
    requires_ocr = True
    safe = False  # Consumes a battle attempt

    # Navigation coordinates (OCR-verified 2026-04-19)
    _GOTO_BATTLE = (0.912, 0.936)    # "前往作战" on hub
    _KEYIN_TAB = (0.669, 0.919)      # "刻印" tab
    _START_CHALLENGE = (0.797, 0.911)  # "开始挑战"
    _REWARD_CLAIM = (0.104, 0.913)   # "奖励领取"
    _ONE_KEY_CLAIM = (0.811, 0.924)  # "一键领取"

    # Battle wait config
    _BATTLE_CHECK_INTERVAL = 10  # seconds between OCR checks
    _BATTLE_TIMEOUT = 300        # 5 minutes max

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        ctx.logger.info("=== MediumSeizureCombat: starting ===")
        try:
            # Step 1: Ensure at hub
            ctx.logger.info("[Step 1] Ensure at hub (wake + return)")
            await WakeHubUiAction().run(ctx)
            await ReturnToHubAction().run(ctx)
            await SleepOp(0.5).run(ctx)

            # Step 2: Navigate to 介质攫取 interior
            ctx.logger.info("[Step 2] Navigate to 介质攫取 interior")
            nav_ok = await self._navigate_to_interior(ctx)
            if not nav_ok:
                ctx.logger.error("[Step 2] FAILED: navigation to 介质攫取")
                return TaskResult(status="failed", message="Navigation to 介质攫取 failed")

            # Step 2.5: Check if all weekly rewards already claimed
            ctx.logger.info("[Step 2.5] Check if weekly rewards already claimed")
            needs_battle = await self._check_rewards_incomplete(ctx)
            if not needs_battle:
                ctx.logger.info("[medium_seizure] All rewards claimed, skipping battle")
                await PressKeyOp(VK_ESCAPE, wait=1.0).run(ctx)
                await ReturnToHubAction().run(ctx)
                ctx.logger.info("=== MediumSeizureCombat: completed (skipped) ===")
                return TaskResult(
                    status="skipped", message="本周奖励已领取完"
                )

            # Step 3: Start challenge
            ctx.logger.info("[Step 3] Clicking 开始挑战")
            ctx.logger.info("[medium_seizure] Clicking 开始挑战")
            await ClickOp(*self._START_CHALLENGE, wait=1.5).run(ctx)

            # Step 4: Enter battle (press Enter on team/stage detail)
            ctx.logger.info("[Step 4] Enter battle — pressing Enter")
            await PressKeyOp(VK_ENTER, wait=3.0).run(ctx)

            # Step 5: Passive battle wait
            ctx.logger.info("[Step 5] Waiting for battle to end")
            battle_result = await self._wait_for_battle_end(ctx)
            ctx.logger.info(f"[Step 5] Battle result: {battle_result}")
            if battle_result != "success":
                ctx.logger.error(f"[Step 5] FAILED: battle {battle_result}")
                return TaskResult(status="failed", message=f"Battle {battle_result}")

            # Step 6: After battle ends, navigate back to interior for rewards
            ctx.logger.info("[Step 6] Dismissing post-battle screens")
            await SleepOp(2.0).run(ctx)
            # Battle completion may return us to interior or a results screen.
            # Press Enter/ESC to dismiss any results, then re-navigate if needed.
            await PressKeyOp(VK_ENTER, wait=1.0).run(ctx)
            await PressKeyOp(VK_ENTER, wait=1.0).run(ctx)

            # Check if we're back at interior
            interior_ok = await self._verify_interior(ctx)
            if not interior_ok:
                # Try navigating back from hub
                ctx.logger.info("[medium_seizure] Not at interior, re-navigating")
                await ReturnToHubAction().run(ctx)
                nav_ok = await self._navigate_to_interior(ctx)
                if not nav_ok:
                    ctx.logger.error("[Step 6] FAILED: cannot re-navigate to interior")
                    return TaskResult(
                        status="failed", message="Cannot re-navigate to interior for rewards"
                    )

            # Step 7: Claim rewards
            ctx.logger.info("[Step 7] Claiming rewards")
            await self._claim_rewards(ctx)

            # Step 8: Return to hub
            ctx.logger.info("[Step 8] Return to hub")
            await PressKeyOp(VK_ESCAPE, wait=1.0).run(ctx)
            await ReturnToHubAction().run(ctx)

            ctx.logger.info("=== MediumSeizureCombat: completed successfully ===")
            return TaskResult(status="success", message="介质攫取 complete")
        except Exception as exc:
            ctx.logger.error(f"=== MediumSeizureCombat: failed — {exc} ===")
            raise

    async def _navigate_to_interior(self, ctx: TaskContext) -> bool:
        """Hub → 前往作战 → 刻印 tab → 介质攫取 node → interior page."""
        ctx.logger.info("[medium_seizure] Navigating: hub → 前往作战")
        await ClickOp(*self._GOTO_BATTLE, wait=1.5).run(ctx)

        ctx.logger.info("[medium_seizure] Clicking 刻印 tab")
        await ClickOp(*self._KEYIN_TAB, wait=1.5).run(ctx)

        # Two-state OCR logic for 介质攫取 node
        ctx.logger.info("[medium_seizure] OCR locating 介质 node")
        img = ctx.device.screenshot()
        ocr = ocr_once(img)
        matches = ocr.find_all("介质")

        if len(matches) == 0:
            ctx.logger.warning("[medium_seizure] No 介质 found on 刻印 tab")
            return False

        if len(matches) == 1:
            # State 1: only node text visible, click it to enter detail
            m = matches[0]
            r = m.region
            ih, iw = img.shape[:2]
            fx = (r.x + r.w / 2) / iw
            fy = (r.y + r.h / 2) / ih
            ctx.logger.info(f"[medium_seizure] State1: single 介质 at ({fx:.3f}, {fy:.3f})")
            await ClickOp(fx, fy, wait=1.5).run(ctx)

            # Re-scan for state 2
            img = ctx.device.screenshot()
            ocr = ocr_once(img)
            matches = ocr.find_all("介质")

        if len(matches) >= 2:
            # State 2: title + node both visible, pick largest y (the node button)
            ih, iw = img.shape[:2]
            best = max(matches, key=lambda m: (m.region.y + m.region.h / 2))
            r = best.region
            fx = (r.x + r.w / 2) / iw
            fy = (r.y + r.h / 2) / ih
            ctx.logger.info(
                f"[medium_seizure] State2: clicking 介質 node at ({fx:.3f}, {fy:.3f})"
            )
            await ClickOp(fx, fy, wait=1.5).run(ctx)

        # Verify we reached interior
        return await self._verify_interior(ctx)

    async def _verify_interior(self, ctx: TaskContext) -> bool:
        """Check if we're on the 介质攫取 interior page via OCR."""
        img = ctx.device.screenshot()
        ocr = ocr_once(img)
        # "积分倍" is a reliable substring (OCR reads 率 as 宰 sometimes)
        if ocr.has("积分倍") or ocr.has("开始挑战") or ocr.has("今日积分"):
            ctx.logger.info("[medium_seizure] Interior page verified")
            return True
        ctx.logger.warning("[medium_seizure] Interior page NOT verified")
        return False

    async def _check_rewards_incomplete(self, ctx: TaskContext) -> bool:
        """Open reward page, check if any reward shows "未完成".

        Returns True if battle is still needed (未完成 found),
        False if all rewards already claimed (no 未完成).
        """
        ctx.logger.info("[medium_seizure] Checking reward status")
        await ClickOp(*self._REWARD_CLAIM, wait=1.0).run(ctx)

        img = ctx.device.screenshot()
        ocr = ocr_once(img)

        has_incomplete = ocr.has("未完成")
        ctx.logger.info(
            f"[medium_seizure] Reward check: 未完成={'found' if has_incomplete else 'not found'}"
        )

        # Go back to interior
        await PressKeyOp(VK_ESCAPE, wait=1.0).run(ctx)
        return has_incomplete

    async def _wait_for_battle_end(self, ctx: TaskContext) -> str:
        """Passively wait in battle until "任务完成" detected or timeout.

        The character stands idle; future combat_strategy hook can be added here.

        Returns:
            "success" if battle completed, "timeout" if max wait exceeded.
        """
        ctx.logger.info(
            f"[medium_seizure] Passive battle wait "
            f"(check every {self._BATTLE_CHECK_INTERVAL}s, "
            f"timeout {self._BATTLE_TIMEOUT}s)"
        )
        elapsed = 0

        while elapsed < self._BATTLE_TIMEOUT:
            await SleepOp(self._BATTLE_CHECK_INTERVAL).run(ctx)
            elapsed += self._BATTLE_CHECK_INTERVAL

            img = ctx.device.screenshot()
            ocr = ocr_once(img)

            if ocr.has("任务完成"):
                ctx.logger.info(
                    f"[medium_seizure] '任务完成' detected after {elapsed}s"
                )
                await PressKeyOp(VK_ENTER, wait=2.0).run(ctx)
                return "success"

            # Also check for "结算" or battle result indicators
            if ocr.has("结算") or ocr.has("评价"):
                ctx.logger.info(
                    f"[medium_seizure] Battle result screen after {elapsed}s"
                )
                await PressKeyOp(VK_ENTER, wait=2.0).run(ctx)
                return "success"

            ctx.logger.debug(
                f"[medium_seizure] Battle ongoing ({elapsed}s / {self._BATTLE_TIMEOUT}s)"
            )

        ctx.logger.warning("[medium_seizure] Battle timeout reached")
        return "timeout"

    async def _claim_rewards(self, ctx: TaskContext) -> None:
        """Click 奖励领取 → 一键领取 × 3."""
        ctx.logger.info("[medium_seizure] Clicking 奖励领取")
        await ClickOp(*self._REWARD_CLAIM, wait=0.5).run(ctx)

        ctx.logger.info("[medium_seizure] Clicking 一键领取 × 3")
        for i in range(3):
            await ClickOp(*self._ONE_KEY_CLAIM, wait=0.25).run(ctx)

        # Brief wait for claim animation
        await SleepOp(0.5).run(ctx)

        # ESC back to interior
        await PressKeyOp(VK_ESCAPE, wait=1.0).run(ctx)


class JointSpecialOpsSweep:
    """联合特勤 (Joint Special Ops) — find S-rank challenge and sweep.

    Navigation: hub → 前往作战 → 刻印 tab → 联合特勤 node → interior page
    Flow:
        1. Navigate to 联合特勤 interior page
        2. OCR for S级 challenge card
        3. If not found → click 刷新 (bottom right), retry up to 3 times
        4. If S级 still not found after all attempts → return to hub (skip)
        5. If S级 found → click it → min multiplier (<<) → max multiplier (>>)
           → 扫荡 → confirm → dismiss result
        6. Return to hub

    Sweep multiplier strategy same as JointDefenseSweep:
        click << (reset to min) → >> (raise to max available) → 扫荡
    """

    name = "joint_special_ops_sweep"
    description = "联合特勤: 寻找S级并扫荡"
    category = "daily_activity"
    requires_pages = ("main_hub", "battle_select")
    requires_ocr = True
    safe = False  # Consumes sweep resources

    # Navigation (shared with MediumSeizureCombat — same tab)
    _GOTO_BATTLE = (0.912, 0.936)    # "前往作战" on hub
    _KEYIN_TAB = (0.669, 0.919)      # "刻印" tab

    # Multiplier buttons (same layout as JointDefenseSweep)
    _MIN_MULTI_X = 0.738    # << button
    _MIN_MULTI_Y = 0.791
    _MAX_MULTI_X = 0.97     # >> button
    _MAX_MULTI_Y = 0.791

    # Refresh button — circular icon at bottom-right of 联合特勤 interior
    # Verified via coord-picker: user clicked px=(1555, 998) in 1920x1080
    _REFRESH_X = 0.810
    _REFRESH_Y = 0.924

    _MAX_REFRESH = 3

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        ctx.logger.info("=== JointSpecialOpsSweep: starting ===")
        try:
            # Step 1: Ensure at hub
            ctx.logger.info("[Step 1] Ensure at hub")
            await WakeHubUiAction().run(ctx)
            await ReturnToHubAction().run(ctx)
            await SleepOp(0.5).run(ctx)

            # Step 2: Navigate to 联合特勤 interior
            ctx.logger.info("[Step 2] Navigate to 联合特勤")
            nav_ok = await self._navigate_to_special_ops(ctx)
            if not nav_ok:
                ctx.logger.error("[Step 2] FAILED: could not enter 联合特勤")
                await ReturnToHubAction().run(ctx)
                return TaskResult(
                    status="failed", message="Navigation to 联合特勤 failed"
                )

            # Step 3: Find S级 (with refresh retries)
            ctx.logger.info("[Step 3] Search for S级 challenge")
            s_found = await self._find_and_select_s_rank(ctx)
            if not s_found:
                ctx.logger.info(
                    "[Step 3] S级 not found after all attempts, returning to hub"
                )
                await PressKeyOp(VK_ESCAPE, wait=1.0).run(ctx)
                await ReturnToHubAction().run(ctx)
                ctx.logger.info("=== JointSpecialOpsSweep: skipped (no S级) ===")
                return TaskResult(
                    status="skipped", message="S级未找到，已返回大厅"
                )

            # Step 4: Min → Max multiplier → Sweep
            ctx.logger.info("[Step 4] Set multiplier (min→max) and sweep")
            sweep_ok = await self._min_max_sweep(ctx)
            if not sweep_ok:
                ctx.logger.error("[Step 4] FAILED: sweep failed")
                await PressKeyOp(VK_ESCAPE, wait=0.5).run(ctx)
                await ReturnToHubAction().run(ctx)
                return TaskResult(status="failed", message="扫荡 failed")

            # Step 5: Confirm and dismiss
            ctx.logger.info("[Step 5] Confirm sweep and dismiss result")
            await self._confirm_and_dismiss(ctx)

            # Step 6: Return to hub
            ctx.logger.info("[Step 6] Return to hub")
            await PressKeyOp(VK_ESCAPE, wait=1.0).run(ctx)
            await ReturnToHubAction().run(ctx)

            ctx.logger.info("=== JointSpecialOpsSweep: completed ===")
            return TaskResult(
                status="success", message="联合特勤 S级扫荡完成"
            )
        except Exception as exc:
            ctx.logger.error(f"=== JointSpecialOpsSweep: failed — {exc} ===")
            raise

    # ------------------------------------------------------------------
    # Navigation: hub → 刻印 tab → 联合特勤
    # ------------------------------------------------------------------

    async def _navigate_to_special_ops(self, ctx: TaskContext) -> bool:
        """Hub → 前往作战 → 刻印 tab → find and click 联合特勤."""
        ctx.logger.info("[joint_ops] Navigating: hub → 前往作战")
        await ClickOp(*self._GOTO_BATTLE, wait=1.5).run(ctx)

        ctx.logger.info("[joint_ops] Clicking 刻印 tab")
        await ClickOp(*self._KEYIN_TAB, wait=1.5).run(ctx)

        # OCR to find 联合特勤 / 特勤 on the tab
        ctx.logger.info("[joint_ops] OCR locating 联合特勤 node")
        img = ctx.device.screenshot()
        ocr = ocr_once(img)

        match = ocr.find("联合特勤") or ocr.find("特勤") or ocr.find("联合")

        if match is None:
            ctx.logger.warning("[joint_ops] 联合特勤 not found on 刻印 tab")
            return False

        ih, iw = img.shape[:2]
        r = match.region
        fx = (r.x + r.w / 2) / iw
        fy = (r.y + r.h / 2) / ih
        ctx.logger.info(
            f"[joint_ops] Found '{match.text}' at ({fx:.3f}, {fy:.3f})"
        )
        await ClickOp(fx, fy, wait=1.5).run(ctx)

        # Two-state logic (same pattern as 介质攫取):
        # First click may show detail, second click enters interior
        img = ctx.device.screenshot()
        ocr = ocr_once(img)
        matches = ocr.find_all("特勤")
        if len(matches) >= 2:
            ih, iw = img.shape[:2]
            best = max(matches, key=lambda m: m.region.y + m.region.h / 2)
            r = best.region
            fx = (r.x + r.w / 2) / iw
            fy = (r.y + r.h / 2) / ih
            ctx.logger.info(
                f"[joint_ops] State2: clicking node at ({fx:.3f}, {fy:.3f})"
            )
            await ClickOp(fx, fy, wait=1.5).run(ctx)

        # Verify interior page
        await SleepOp(1.0).run(ctx)
        img = ctx.device.screenshot()
        ocr = ocr_once(img)
        if ocr.has("级") or ocr.has("刷新") or ocr.has("LEVEL") or ocr.has("特勤"):
            ctx.logger.info("[joint_ops] Interior page verified")
            return True

        ctx.logger.warning(
            "[joint_ops] Could not verify interior page, proceeding anyway"
        )
        return True

    # ------------------------------------------------------------------
    # Find S级 with refresh retries
    # ------------------------------------------------------------------

    async def _find_and_select_s_rank(self, ctx: TaskContext) -> bool:
        """OCR scan for S级 challenge. Refresh up to 3 times if not found."""
        for attempt in range(1, self._MAX_REFRESH + 1):
            ctx.logger.info(
                f"[joint_ops] Attempt {attempt}/{self._MAX_REFRESH}: "
                f"scanning for S级"
            )
            img = ctx.device.screenshot()
            ocr = ocr_once(img)
            ih, iw = img.shape[:2]

            # Try "S级" first (most reliable)
            s_match = ocr.find("S级")

            # Fallback: look for standalone "S" near grade-related text
            if s_match is None:
                for item in ocr.items:
                    text = item.text.strip()
                    if text == "S" or text == "S级":
                        s_match = item
                        break

            if s_match is not None:
                r = s_match.region
                fx = (r.x + r.w / 2) / iw
                fy = (r.y + r.h / 2) / ih
                ctx.logger.info(
                    f"[joint_ops] S级 found: '{s_match.text}' "
                    f"at ({fx:.3f}, {fy:.3f})"
                )
                await ClickOp(fx, fy, wait=1.5).run(ctx)
                return True

            ctx.logger.info(
                f"[joint_ops] S级 not found (attempt {attempt})"
            )

            # Don't refresh on the last attempt
            if attempt >= self._MAX_REFRESH:
                break

            # Click refresh button (fixed position, bottom right)
            ctx.logger.info(
                f"[joint_ops] Clicking 刷新 at fixed coord "
                f"({self._REFRESH_X}, {self._REFRESH_Y})"
            )
            await ClickOp(self._REFRESH_X, self._REFRESH_Y, wait=1.5).run(ctx)

            # Handle possible confirmation popup
            await SleepOp(0.5).run(ctx)
            img2 = ctx.device.screenshot()
            ocr2 = ocr_once(img2)
            if ocr2.has("确定") or ocr2.has("确认"):
                ctx.logger.info("[joint_ops] Confirm refresh popup")
                await PressKeyOp(VK_ENTER, wait=1.5).run(ctx)

            await SleepOp(1.0).run(ctx)

        ctx.logger.warning(
            "[joint_ops] S级 not found after all refresh attempts"
        )
        return False

    # ------------------------------------------------------------------
    # Min → Max multiplier → Sweep
    # ------------------------------------------------------------------

    async def _min_max_sweep(self, ctx: TaskContext) -> bool:
        """Click << (min), >> (max), then 扫荡 — same as JointDefenseSweep."""
        # Click << (min) to reset multiplier
        ctx.logger.info(
            f"[joint_ops] Clicking << (min) at "
            f"({self._MIN_MULTI_X}, {self._MIN_MULTI_Y})"
        )
        await ClickOp(self._MIN_MULTI_X, self._MIN_MULTI_Y, wait=0.3).run(ctx)

        # Click >> (max) to set highest affordable multiplier
        ctx.logger.info(
            f"[joint_ops] Clicking >> (max) at "
            f"({self._MAX_MULTI_X}, {self._MAX_MULTI_Y})"
        )
        await ClickOp(self._MAX_MULTI_X, self._MAX_MULTI_Y, wait=0.5).run(ctx)

        # Find and click 扫荡
        img = ctx.device.screenshot()
        ocr = ocr_once(img)
        sweep = ocr.find("扫荡")

        if sweep is None:
            ctx.logger.error("[joint_ops] 扫荡 button not found")
            return False

        ih, iw = img.shape[:2]
        r = sweep.region
        sx = (r.x + r.w / 2) / iw
        sy = (r.y + r.h / 2) / ih
        ctx.logger.info(f"[joint_ops] Clicking 扫荡 at ({sx:.3f}, {sy:.3f})")
        await ClickOp(sx, sy, wait=1.5).run(ctx)
        return True

    # ------------------------------------------------------------------
    # Confirm and dismiss
    # ------------------------------------------------------------------

    async def _confirm_and_dismiss(self, ctx: TaskContext) -> None:
        """Confirm sweep popup and dismiss result screen."""
        # Confirm sweep
        ctx.logger.info("[joint_ops] Pressing Enter to confirm sweep")
        await PressKeyOp(VK_ENTER, wait=2.0).run(ctx)

        # Check for stamina-insufficient popup
        img = ctx.device.screenshot()
        ocr = ocr_once(img)
        if ocr.has("补充") or ocr.has("冷却剂") or ocr.has("吨吨值"):
            ctx.logger.info(
                "[joint_ops] Stamina insufficient, pressing ESC to cancel"
            )
            await PressKeyOp(VK_ESCAPE, wait=0.5).run(ctx)
            return

        # Dismiss result screen
        await SleepOp(2.0).run(ctx)
        for _ in range(5):
            await PressKeyOp(VK_ENTER, wait=0.2).run(ctx)
