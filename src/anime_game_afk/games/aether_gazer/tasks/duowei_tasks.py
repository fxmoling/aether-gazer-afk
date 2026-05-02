"""多维变量 (Multidimensional Variable) — roguelike combat task.

Navigation: hub → 挑战 tab → 多维变量 → setup wizard → arena
Strategy:   1-1 treasure → swipe + walk to portal → 1-2 fight → ESC+H exit

Simplified strategy (minimum score per run):
  - Only clear through 1-2 then ESC+H+Enter exit for minimum score
  - Treasure: click center + confirm (unified for single/multi card)
  - Portal: swipe camera left (fractional dx=0.02) + W walk + J spam
  - Battle: J J U J I J O R 1 2 attack cycle until victory
  - Exit: ESC → H (退出并结算) → Enter → settlement → return

Camera rotation uses fractional swipe (0.0–1.0) for resolution independence.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.knowledge.keys import (
    VK_ENTER, VK_ESCAPE, VK_J, VK_W, VK_H, VK_S,
)
from anime_game_afk.games.aether_gazer.ops.primitives import (
    ClickOp,
    SleepOp,
)
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext, TaskResult
from anime_game_afk.games.aether_gazer.tasks.navigation_tasks import ReturnToHub
from anime_game_afk.games.aether_gazer.combat.script import load_script
from anime_game_afk.games.aether_gazer.combat.service import AutoBattleService
from anime_game_afk.vision.ocr import ocr_once

# ── Camera rotation (fractional, resolution-scaled) ──
# Base swipe dx calibrated at 1280x720. Same fractional dx produces more
# pixel distance on higher resolutions, causing more rotation. Scale
# inversely by (base_width / actual_width) to keep the angle consistent.
_PORTAL_SWIPE_DX_BASE = 0.02   # dx at 1280 width
_PORTAL_SWIPE_REF_WIDTH = 1280  # calibration resolution
_PORTAL_SWIPE_FROM = (0.55, 0.5)
_PORTAL_SWIPE_DURATION = 300  # ms

# ── Fixed coordinates (all fractional 0.0–1.0) ──
_REWARD_CONFIRM = (0.608, 0.847)    # "确认" overlap zone (92% of single-card btn)
_SCREEN_CENTER = (0.50, 0.40)       # Center click to select card / dismiss


class DuoweiCombat:
    """Run one 多维变量 cycle: navigate → setup → 1-1 → portal → 1-2 → exit.

    Flow:
        1. Navigate to 多维变量 page, handle "继续挑战" if present
        2. Setup wizard: difficulty(下一步) → character(下一步) → beacon(开始挑战)
        3. Arena 1-1: dismiss treasure → swipe camera → W+J walk to portal
        4. Arena 1-2: fight battle → handle reward (center click + confirm)
        5. ESC + H + Enter → settlement screens → return to 多维变量 page
    """

    name = "duowei_combat"
    description = "多维变量: 挑战1-2层获取积分"
    category = "challenge"
    requires_ocr = True

    # Timing
    _SETUP_WAIT = 3.0
    _LOADING_WAIT = 8.0
    def __init__(self) -> None:
        pass

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        """Run one complete 多维变量 cycle."""
        try:
            ctx.logger.info("=== DuoweiCombat: starting ===")
            # Action 1: Navigate to 多维变量 and click 开始挑战
            ctx.logger.info("[duowei] Action 1: Navigate")
            if not await self._navigate_to_duowei(ctx):
                return TaskResult(status="failed", message="Navigation failed")

            # Action 2: Setup wizard (difficulty → character → beacon)
            ctx.logger.info("[duowei] Action 2: Setup wizard")
            await self._complete_setup(ctx)

            # Wait for arena to load
            await SleepOp(self._LOADING_WAIT).run(ctx)

            # Action 3: Handle 1-1 treasure
            ctx.logger.info("[duowei] Action 3: 1-1 treasure")
            await self._handle_treasure(ctx)
            await SleepOp(1.0).run(ctx)

            # Action 4: Walk to portal (swipe + W + J)
            ctx.logger.info("[duowei] Action 4: Walk to portal")
            if not await self._walk_to_portal(ctx):
                ctx.logger.warning("[duowei] Portal not found, exiting")
                await self._exit_and_settle(ctx)
                return TaskResult(status="failed", message="Portal not found")

            # Wait for 1-2 to load
            await SleepOp(5.0).run(ctx)

            # Handle any transition dialogs/treasure before battle
            await self._dismiss_dialogs(ctx)
            await self._handle_treasure(ctx)

            # Action 5: Fight 1-2
            ctx.logger.info("[duowei] Action 5: Fight 1-2")
            battle = await self._fight_battle(ctx)
            ctx.logger.info(f"[duowei] Battle result: {battle}")

            # Handle post-battle reward
            await SleepOp(2.0).run(ctx)
            await self._handle_reward(ctx)

            # Action 6: Exit and settle
            ctx.logger.info("[duowei] Action 6: Exit and settle")
            await self._exit_and_settle(ctx)

            ctx.logger.info("=== DuoweiCombat: completed successfully ===")
            return TaskResult(
                status="success",
                message=f"多维变量 completed (battle: {battle})",
            )
        except Exception as exc:
            ctx.logger.error(f"=== DuoweiCombat: failed — {exc} ===")
            try:
                await self._exit_and_settle(ctx)
            except Exception:
                pass
            return TaskResult(status="failed", message=str(exc))

    # ── Action 1: Navigation ──

    async def _navigate_to_duowei(self, ctx: TaskContext) -> bool:
        """Navigate to 多维变量 page and click 开始挑战/继续挑战."""
        ctx.logger.info("[duowei] _navigate_to_duowei starting")
        img = ctx.screenshot()
        ocr = ocr_once(img)
        full = " ".join(r.text for r in ocr._items)
        ctx.logger.debug(f"[duowei] OCR full text: {full[:100]}")

        # Already on 多维变量 detail page (has unique "记忆珍宝图鉴" text)
        if "记忆珍宝图鉴" in full:
            ctx.logger.info("[duowei] Already on 多维变量 page")
            return await self._click_start_or_continue(ctx, ocr, full)

        # Any other page: return to hub → battle page → challenge tab
        ctx.logger.info("[duowei] Returning to hub first")
        hub = ReturnToHub()
        await hub.execute(ctx)

        # Press J to enter battle page from hub
        ctx.device.press_key(VK_J)
        await SleepOp(1.5).run(ctx)

        # Click 挑战 tab on battle page (bottom-right)
        ctx.device.click(0.83, 0.9)
        await SleepOp(2.0).run(ctx)

        # Find 多维变量 — may need to scroll left on challenge page
        for scroll_attempt in range(3):
            img = ctx.screenshot()
            ocr = ocr_once(img)
            full = " ".join(r.text for r in ocr._items)
            ctx.logger.debug(f"[duowei] OCR full text: {full[:100]}")

            # Find all "多维变量" matches
            matches = [
                r for r in ocr._items if "多维变量" in r.text
            ]
            ctx.logger.info(f"[duowei] Found {len(matches)} '多维变量' matches")
            if len(matches) == 1:
                # Only one match — click it, then re-check if we landed
                # on the detail page or just highlighted the heading
                r = matches[0].region
                ctx.device.click(
                    (r.x + r.w // 2) / 1280, (r.y + r.h // 2) / 720,
                )
                await SleepOp(2.0).run(ctx)
                img = ctx.screenshot()
                ocr = ocr_once(img)
                full = " ".join(r.text for r in ocr._items)
                ctx.logger.debug(f"[duowei] OCR full text: {full[:100]}")
                if "开始挑战" in full or "继续挑战" in full:
                    return await self._click_start_or_continue(ctx, ocr, full)
                # Didn't land on detail page — may need another click
                matches2 = [
                    r for r in ocr._items if "多维变量" in r.text
                ]
                if len(matches2) >= 2:
                    best = max(matches2, key=lambda r: r.region.y)
                    r = best.region
                    ctx.device.click(
                        (r.x + r.w // 2) / 1280, (r.y + r.h // 2) / 720,
                    )
                    await SleepOp(2.0).run(ctx)
                    img = ctx.screenshot()
                    ocr = ocr_once(img)
                    full = " ".join(r.text for r in ocr._items)
                    ctx.logger.debug(f"[duowei] OCR full text: {full[:100]}")
                    return await self._click_start_or_continue(ctx, ocr, full)
            elif len(matches) >= 2:
                # Multiple matches — click the lowest one (card icon)
                best = max(matches, key=lambda r: r.region.y)
                r = best.region
                ctx.device.click(
                    (r.x + r.w // 2) / 1280, (r.y + r.h // 2) / 720,
                )
                await SleepOp(2.0).run(ctx)
                img = ctx.screenshot()
                ocr = ocr_once(img)
                full = " ".join(r.text for r in ocr._items)
                ctx.logger.debug(f"[duowei] OCR full text: {full[:100]}")
                return await self._click_start_or_continue(ctx, ocr, full)

            # Scroll challenge list by clicking left edge
            ctx.logger.debug(
                f"[duowei] 多维变量 not visible, scrolling left ({scroll_attempt + 1}/3)"
            )
            ctx.device.click(0.05, 0.5)
            await SleepOp(1.5).run(ctx)

        ctx.logger.warning("[duowei] 多维变量 not found after scrolling")
        return False

    async def _click_start_or_continue(self, ctx, ocr, full: str) -> bool:
        """Click 开始挑战 or 继续挑战, handling the 'ongoing battle' dialog."""
        # Try 继续挑战 first (has priority — means unfinished run)
        for label in ["继续挑战", "开始挑战"]:
            match = ocr.find(label)
            if match:
                ctx.logger.info(f"[duowei] Clicking '{label}' button")
                r = match.region
                ctx.device.click(
                    (r.x + r.w // 2) / 1280, (r.y + r.h // 2) / 720,
                )
                await SleepOp(self._SETUP_WAIT).run(ctx)

                # Check for "尚未结束的战局" dialog
                img = ctx.screenshot()
                ocr2 = ocr_once(img)
                full2 = " ".join(r.text for r in ocr2._items)
                if "尚未结束" in full2 or "战局" in full2:
                    ctx.logger.info("[duowei] Ongoing battle dialog, pressing ESC to settle")
                    ctx.device.press_key(VK_ESCAPE)
                    await SleepOp(5.0).run(ctx)
                    # Click through settlement then retry
                    await self._click_through_settlement(ctx)
                    # Re-navigate
                    img = ctx.screenshot()
                    ocr3 = ocr_once(img)
                    match3 = ocr3.find("开始挑战")
                    if match3:
                        r3 = match3.region
                        ctx.device.click(
                            (r3.x + r3.w // 2) / 1280,
                            (r3.y + r3.h // 2) / 720,
                        )
                        await SleepOp(self._SETUP_WAIT).run(ctx)
                return True

        ctx.logger.warning("[duowei] Neither 开始挑战 nor 继续挑战 found")
        return False

    # ── Action 2: Setup wizard ──

    async def _complete_setup(self, ctx: TaskContext) -> None:
        """Difficulty(Lv16) → Character(下一步) → Beacon(赏金猎人 + 开始挑战)."""
        # Step 1: Select LV16 difficulty, then click 下一步
        ctx.logger.info("[duowei] Setup: selecting difficulty")
        await self._select_difficulty(ctx, target_lv=16)
        await SleepOp(1.5).run(ctx)
        if not await self._ocr_click(ctx, "下一步", "difficulty"):
            await SleepOp(1.0).run(ctx)
            await self._ocr_click(ctx, "下一步", "difficulty fallback")
        await SleepOp(self._SETUP_WAIT).run(ctx)

        # Step 2: Character → 下一步
        ctx.logger.info("[duowei] Setup: advancing past character page")
        await self._ocr_click(ctx, "下一步", "character")
        await SleepOp(self._SETUP_WAIT).run(ctx)

        # Step 3: Beacon page → scroll down, find 赏金猎人, click, then 开始挑战
        ctx.logger.info("[duowei] Setup: selecting beacon")
        await self._select_beacon(ctx)
        await self._ocr_click(ctx, "开始挑战", "beacon start")
        await SleepOp(self._SETUP_WAIT).run(ctx)

    async def _select_difficulty(self, ctx: TaskContext, target_lv: int = 16) -> bool:
        """Scroll difficulty list and click the target LV item.

        Returns True if target difficulty is confirmed selected.
        Gives up after 5 scroll attempts and treats as success (proceed anyway).
        """
        target_str = f"lv{target_lv}"
        max_scrolls = 5

        for scroll in range(max_scrolls):
            img = ctx.screenshot()
            ocr = ocr_once(img)

            # Check right panel — if already at target, done
            full = " ".join(r.text for r in ocr._items)
            if f"难度等级：{target_lv}" in full or f"难度等级:{target_lv}" in full:
                ctx.logger.info(f"[duowei] Already at LV{target_lv}")
                return True

            # Find exact LV match (screenshot is always 1280x720)
            for item in ocr._items:
                txt = item.text.strip().lower().replace(" ", "")
                if txt == target_str:
                    r = item.region
                    ctx.device.click(
                        (r.x + r.w // 2) / 1280, (r.y + r.h // 2) / 720,
                    )
                    ctx.logger.info(
                        f"[duowei] Clicked LV{target_lv} at ({r.x},{r.y})"
                    )
                    await SleepOp(1.0).run(ctx)
                    return True

            # Scroll down to reveal more levels, wait 1s extra to let UI settle
            ctx.logger.debug(
                f"[duowei] LV{target_lv} not visible, scrolling ({scroll + 1}/{max_scrolls})"
            )
            ctx.device.swipe(0.3, 0.7, 0.3, 0.3, 500)
            await SleepOp(2.0).run(ctx)  # 1s scroll + 1s settle

        ctx.logger.warning(
            f"[duowei] LV{target_lv} not found after {max_scrolls} scrolls, proceeding anyway"
        )
        return True  # treat as success — click 下一步 regardless

    async def _ocr_click(self, ctx: TaskContext, text: str, label: str) -> bool:
        """OCR-find text and click its center. Returns True if found."""
        img = ctx.screenshot()
        ocr = ocr_once(img)
        match = ocr.find(text)
        if match:
            r = match.region
            ctx.device.click(
                (r.x + r.w // 2) / 1280,
                (r.y + r.h // 2) / 720,
            )
            ctx.logger.debug(f"[duowei] {label}: clicked {text}")
            return True
        ctx.logger.debug(f"[duowei] {label}: {text} not found")
        return False

    async def _select_beacon(self, ctx: TaskContext) -> None:
        """Scroll beacon list and select 赏金猎人, 孤狼之道, 残酷天平.

        OCR → click any visible target → scroll → repeat.
        Stops when all 3 are selected or after 5 scroll cycles.
        """
        targets = ["赏金猎人", "孤狼之道", "残酷天平"]
        selected: set[str] = set()
        max_scrolls = 5

        for scroll in range(max_scrolls):
            img = ctx.screenshot()
            ocr = ocr_once(img)

            # Try to click each unselected target visible on screen
            found_any = False
            for name in targets:
                if name in selected:
                    continue
                match = ocr.find(name)
                if match:
                    r = match.region
                    ctx.device.click(
                        (r.x + r.w // 2) / 1280,
                        (r.y + r.h // 2) / 720,
                    )
                    selected.add(name)
                    found_any = True
                    ctx.logger.info(
                        f"[duowei] Selected beacon: {name} ({len(selected)}/{len(targets)})"
                    )
                    await SleepOp(1.0).run(ctx)

            if len(selected) >= len(targets):
                ctx.logger.info("[duowei] All beacons selected")
                return

            if not found_any:
                # Nothing new found — scroll down to reveal more beacons
                ctx.logger.debug(
                    f"[duowei] No new beacons visible, scrolling ({scroll + 1}/{max_scrolls})"
                )
                ctx.device.swipe(0.5, 0.5, 0.5, 0.2, 500)
                await SleepOp(1.5).run(ctx)

        ctx.logger.info(
            f"[duowei] Beacon selection done: {len(selected)}/{len(targets)} "
            f"selected ({selected or 'none'}), proceeding"
        )

    # ── Action 3: Treasure handling ──

    async def _handle_treasure(self, ctx: TaskContext) -> None:
        """Handle treasure screen: click center (select card) + confirm."""
        img = ctx.screenshot()
        ocr = ocr_once(img)
        full = " ".join(r.text for r in ocr._items)

        if "珍宝" not in full:
            return

        ctx.logger.info("[duowei] Handling treasure selection")
        # Click center to select a card (works for both single/multi)
        await ClickOp(*_SCREEN_CENTER).run(ctx)
        await SleepOp(1.0).run(ctx)
        # Click confirm (overlap zone works for 1-button and 2-button layouts)
        await ClickOp(*_REWARD_CONFIRM).run(ctx)
        await SleepOp(2.0).run(ctx)

        # Verify treasure dismissed
        img = ctx.screenshot()
        ocr = ocr_once(img)
        full = " ".join(r.text for r in ocr._items)
        if "珍宝" in full:
            # Retry with confirm
            await ClickOp(*_REWARD_CONFIRM).run(ctx)
            await SleepOp(2.0).run(ctx)

    # ── Action 4: Portal navigation ──

    async def _walk_to_portal(self, ctx: TaskContext) -> bool:
        """Swipe camera left to align with portal, then W walk + J spam.

        Camera rotation uses fractional swipe (dx=0.02) for resolution
        independence. User-configurable multiplier scales the angle.
        """
        ctx.logger.info("[duowei] Swipe + W walk + J spam")

        # Load user multiplier (0.5–2.0, default 1.0)
        from anime_game_afk.config.user_config import UserConfig
        multiplier = UserConfig.load().duowei_swipe_multiplier()

        # Scale swipe dx by resolution (calibrated at 1280 width)
        actual_w = ctx.device.actual_resolution.width
        dx = _PORTAL_SWIPE_DX_BASE * _PORTAL_SWIPE_REF_WIDTH / actual_w * multiplier
        ctx.logger.debug(
            f"[duowei] Portal swipe dx={dx:.4f} (base={_PORTAL_SWIPE_DX_BASE}, "
            f"ref={_PORTAL_SWIPE_REF_WIDTH}, actual={actual_w}, mult={multiplier:.1f})"
        )

        fx, fy = _PORTAL_SWIPE_FROM
        ctx.device.swipe(fx, fy, fx - dx, fy, _PORTAL_SWIPE_DURATION)
        await SleepOp(0.5).run(ctx)

        # Walk W while spamming J to trigger portal interaction
        for step in range(12):
            ctx.device.hold_key(VK_W, 0.8)
            ctx.device.press_key(VK_J)
            await SleepOp(0.2).run(ctx)

            # Check for scene transition every 3 steps
            if step % 3 == 2:
                ctx.logger.debug(f"[duowei] Walk step {step + 1}/12")
                if await self._check_portal_entered(ctx):
                    return True

        # Fallback: walk back, scan more angles
        ctx.logger.warning("[duowei] Primary walk missed, fallback scan")
        ctx.device.hold_key(VK_S, 4.0)
        await SleepOp(0.3).run(ctx)

        # Fallback rotation per step: ~45° (scaled by resolution)
        fallback_dx = 0.025 * _PORTAL_SWIPE_REF_WIDTH / actual_w

        for angle in range(8):
            ctx.logger.debug(f"[duowei] Fallback scan: angle {angle + 1}/8, step 0/8")
            ctx.device.swipe(fx, fy, fx - fallback_dx, fy, _PORTAL_SWIPE_DURATION)
            await SleepOp(0.3).run(ctx)

            for step in range(8):
                ctx.device.hold_key(VK_W, 0.8)
                ctx.device.press_key(VK_J)
                await SleepOp(0.2).run(ctx)

                if step % 2 == 1:
                    ctx.logger.debug(f"[duowei] Fallback scan: angle {angle + 1}/8, step {step + 1}/8")
                    if await self._check_portal_entered(ctx):
                        return True

            ctx.device.hold_key(VK_S, 3.0)
            await SleepOp(0.2).run(ctx)

        return False

    async def _check_portal_entered(self, ctx: TaskContext) -> bool:
        """Check if we transitioned through portal (battle/treasure/loading)."""
        img = ctx.screenshot()
        ocr = ocr_once(img)
        full = " ".join(r.text for r in ocr._items)

        if "击退" in full or "剩余" in full:
            ctx.logger.info("[duowei] Battle detected — portal entered!")
            return True
        if "珍宝" in full:
            ctx.logger.info("[duowei] Treasure detected — portal entered!")
            return True
        # Loading screen: very little OCR text
        if len(ocr._items) <= 2 and "当前关卡" not in full:
            ctx.logger.info("[duowei] Loading screen — portal entered!")
            return True
        return False

    # ── Action 5: Combat ──

    async def _fight_battle(self, ctx: TaskContext) -> str:
        """Execute combat script until battle ends (with debounce)."""
        ctx.logger.info("[duowei] _fight_battle starting")
        await SleepOp(3.0).run(ctx)  # Wait for battle to fully load

        from anime_game_afk.config.user_config import UserConfig
        script_name = UserConfig.load().combat_script()
        try:
            script = load_script(script_name)
        except FileNotFoundError:
            ctx.logger.warning(
                f"[duowei] Script '{script_name}' not found, falling back to 'default'"
            )
            script = load_script("default")
        ctx.logger.info(f"[duowei] Using combat script: {script.name}")
        service = AutoBattleService(script, check_interval=2.0)
        await service.run_until_battle_ends(ctx, extra_confirms=3)

        ctx.logger.info("[duowei] Battle ended")
        return "won"

    # ── Post-battle reward ──

    async def _handle_reward(self, ctx: TaskContext) -> None:
        """Handle post-battle reward: center click + confirm overlap zone.

        Two layouts:
          - Multi-card: 放弃 + 确认 buttons → click center selects a card
          - Single-card: 确认 only → click center is harmless
        Confirm overlap zone (0.668, 0.846) works for both layouts.
        Only triggers on treasure/reward screens, not generic arena HUD.
        """
        for attempt in range(3):
            img = ctx.screenshot()
            ocr = ocr_once(img)
            full = " ".join(r.text for r in ocr._items)

            # Only act on actual reward/treasure screens
            is_reward = "珍宝" in full or "放弃" in full
            is_confirm_only = "确认" in full and "击退" not in full and "当前关卡" not in full
            if not is_reward and not is_confirm_only:
                return

            ctx.logger.info(f"[duowei] Reward screen (attempt {attempt + 1})")
            await ClickOp(*_SCREEN_CENTER).run(ctx)
            await SleepOp(1.0).run(ctx)
            await ClickOp(*_REWARD_CONFIRM).run(ctx)
            await SleepOp(2.0).run(ctx)

    # ── Dialog dismissal ──

    async def _dismiss_dialogs(self, ctx: TaskContext) -> None:
        """Dismiss generic confirmation dialogs (rewards, popups)."""
        for _ in range(5):
            img = ctx.screenshot()
            ocr = ocr_once(img)
            full = " ".join(r.text for r in ocr._items)

            if "确认" in full and "击退" not in full and "珍宝" not in full:
                match = ocr.find("确认")
                if match:
                    r = match.region
                    ctx.device.click(
                        (r.x + r.w // 2) / 1280, (r.y + r.h // 2) / 720,
                    )
                else:
                    ctx.device.press_key(VK_ENTER)
                await SleepOp(2.0).run(ctx)
            else:
                break

    # ── Action 6: Exit and settle ──

    async def _exit_and_settle(self, ctx: TaskContext) -> None:
        """ESC → H (退出并结算) → Enter → click through settlement."""
        ctx.logger.info("[duowei] Pressing ESC → H → Enter for exit")
        ctx.device.press_key(VK_ESCAPE)
        await SleepOp(1.5).run(ctx)
        ctx.device.press_key(VK_H)
        await SleepOp(2.0).run(ctx)
        ctx.device.press_key(VK_ENTER)
        await SleepOp(5.0).run(ctx)

        ctx.logger.info("[duowei] Clicking through settlement screens")
        await self._click_through_settlement(ctx)

    async def _click_through_settlement(self, ctx: TaskContext) -> None:
        """Click through settlement/result screens until back at menu."""
        for _ in range(15):
            img = ctx.screenshot()
            ocr = ocr_once(img)
            full = " ".join(r.text for r in ocr._items)
            ctx.logger.debug(f"[duowei] Settlement round {_ + 1}/15, OCR: {full[:80]}")

            # Back at 多维变量 page
            if "多维变量" in full and (
                "开始挑战" in full or "维度偏移" in full
            ):
                ctx.logger.info("[duowei] Back at menu/challenge page")
                return
            # Back at challenge hub
            if "情报" in full or "常驻" in full or "刻印" in full:
                ctx.logger.info("[duowei] Back at menu/challenge page")
                return

            # Settlement result screen: has 积分 + 退出 button
            if "积分" in full or "伤害统计" in full:
                ctx.logger.info("[duowei] Settlement screen detected, clicking 退出")
                # Fixed "退出" button position on settlement screen
                ctx.device.click(0.901, 0.931)
                await SleepOp(2.0).run(ctx)
                continue

            # Click 退出 button via OCR
            match = ocr.find("退出")
            if match:
                r = match.region
                ctx.device.click(
                    (r.x + r.w // 2) / 1280, (r.y + r.h // 2) / 720,
                )
                await SleepOp(2.0).run(ctx)
                continue

            # Click 确认/确定
            for label in ["确认", "确定"]:
                match = ocr.find(label)
                if match:
                    r = match.region
                    ctx.device.click(
                        (r.x + r.w // 2) / 1280, (r.y + r.h // 2) / 720,
                    )
                    await SleepOp(2.0).run(ctx)
                    break
            else:
                # Generic Enter to dismiss
                ctx.device.press_key(VK_ENTER)
                await SleepOp(1.0).run(ctx)

        # Force ESC as last resort
        for _ in range(3):
            ctx.device.press_key(VK_ESCAPE)
            await SleepOp(1.0).run(ctx)
