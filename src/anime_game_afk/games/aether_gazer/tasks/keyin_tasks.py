"""介质攫取 (Medium Seizure) — combat activity under 刻印 tab.

Navigation: hub → 前往作战 → 刻印 tab → 介质攫取 node → interior page
Actions:    start challenge → passive battle wait → claim rewards → return

This is a COMBAT activity (no sweep/扫荡). The task enters battle,
waits passively for timeout/completion, then claims score-threshold rewards.

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
