"""历战轮回 (Battle Recurrence) — infinite combat loop task.

Simplified strategy: user starts on the preparation page.
Each cycle: verify page → click 作战开始 → J-spam loop → detect 轮回节点-10
→ Enter + restart click → 准备作战 → repeat.

Requires user to be on the 历战轮回 battle preparation page.
"""
from __future__ import annotations

import time

from anime_game_afk.games.aether_gazer.knowledge.keys import (
    VK_ENTER, letter_to_vk,
)
from anime_game_afk.games.aether_gazer.ops.primitives import (
    ClickOp, ClickPxOp, PressKeyOp, SleepOp,
)
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext, TaskResult
from anime_game_afk.config.user_config import UserConfig
from anime_game_afk.vision.ocr import ocr_once

# Fixed coordinates (fractional 0.0-1.0)
_RESTART_CLICK = (0.8469, 0.7181)  # "Restart loop" button after reaching node 10

# Timing constants
_KEY_INTERVAL = 0.5      # seconds between next-challenge key presses
_OCR_EVERY_N_KEYS = 10   # OCR check every N key presses (~5s)
_RESTART_WAIT = 1.5      # wait after clicking restart button
_LOADING_WAIT = 3.0      # wait for battle to load
_CYCLE_TIMEOUT = 300.0   # max seconds per cycle (5 minutes)


class LizhanCombat:
    """Run one 历战轮回 cycle: verify → start → combat loop → restart.

    A "cycle" runs from clicking 作战开始 through all 10 nodes until
    轮回节点-10 is detected, then restarts. Returns to the preparation page.
    """

    name = "lizhan_combat"
    description = "历战轮回: 无限刷轮回节点"
    category = "challenge"
    requires_ocr = True

    def __init__(self) -> None:
        cfg = UserConfig.load()
        next_key_letter = cfg.lizhan_next_key()
        self._next_key_vk = letter_to_vk(next_key_letter)

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        """Run one complete 历战轮回 cycle."""
        try:
            ctx.logger.info("=== LizhanCombat: starting ===")

            # Step 1: Verify we're on the right page
            ctx.logger.info("[lizhan] Step 1: Verify page")
            img = ctx.screenshot()
            ocr = ocr_once(img)

            has_node = ocr.has("轮回节点")
            has_start = ocr.find("作战开始")

            if not has_node or not has_start:
                all_text = " ".join(r.text for r in ocr.items)
                ctx.logger.warning(
                    f"[lizhan] Page check failed: "
                    f"轮回节点={'✓' if has_node else '✗'}, "
                    f"作战开始={'✓' if has_start else '✗'} | "
                    f"OCR text: {all_text[:120]}"
                )
                return TaskResult(
                    status="failed",
                    message="未在历战轮回作战准备页面，请手动导航到该页面后重试",
                )

            # Step 2: Click 作战开始
            ctx.logger.info("[lizhan] Step 2: Click 作战开始")
            start_btn = has_start  # TextResult from find()
            r = start_btn.region
            await ClickPxOp(
                r.x + r.w // 2, r.y + r.h // 2, wait=0.3
            ).run(ctx)
            await SleepOp(_LOADING_WAIT).run(ctx)

            # Step 3: Combat loop — press next-challenge key, OCR periodically
            ctx.logger.info("[lizhan] Step 3: Combat loop")
            cycle_start = time.monotonic()
            key_count = 0

            while True:
                # Watchdog: timeout per cycle
                elapsed = time.monotonic() - cycle_start
                if elapsed > _CYCLE_TIMEOUT:
                    ctx.logger.warning(
                        f"[lizhan] Cycle timeout ({_CYCLE_TIMEOUT}s), aborting"
                    )
                    return TaskResult(
                        status="failed",
                        message=f"Cycle timeout after {elapsed:.0f}s",
                    )

                # Press next-challenge key
                await PressKeyOp(self._next_key_vk, wait=_KEY_INTERVAL).run(ctx)
                key_count += 1

                # OCR check every N key presses
                if key_count % _OCR_EVERY_N_KEYS == 0:
                    ctx.logger.debug(
                        f"[lizhan] OCR check (keys={key_count}, "
                        f"elapsed={elapsed:.0f}s)"
                    )
                    img = ctx.screenshot()
                    ocr = ocr_once(img)
                    all_text = " ".join(r.text for r in ocr.items)
                    ctx.logger.debug(f"[lizhan] OCR: {all_text[:120]}")

                    # Check for end-of-loop marker
                    if ocr.has("轮回节点-10"):
                        ctx.logger.info(
                            "[lizhan] Found 轮回节点-10! Restarting loop."
                        )
                        return await self._restart_loop(ctx)

            # Should not reach here
            return TaskResult(status="failed", message="Unexpected exit")

        except Exception as exc:
            ctx.logger.error(f"=== LizhanCombat: failed — {exc} ===")
            return TaskResult(status="failed", message=str(exc))

    async def _restart_loop(self, ctx: TaskContext) -> TaskResult:
        """Handle the restart sequence after reaching 轮回节点-10."""
        # Press Enter to confirm
        ctx.logger.info("[lizhan] Restart: pressing Enter")
        await PressKeyOp(VK_ENTER, wait=2.0).run(ctx)

        # Click the restart button at fixed position
        ctx.logger.info("[lizhan] Restart: clicking restart button")
        await ClickOp(
            _RESTART_CLICK[0], _RESTART_CLICK[1], wait=_RESTART_WAIT,
        ).run(ctx)

        # Wait then find and click 准备作战 or 作战开始
        ctx.logger.info("[lizhan] Restart: looking for 准备作战/作战开始")
        for attempt in range(5):
            img = ctx.screenshot()
            ocr = ocr_once(img)

            btn = ocr.find("准备作战") or ocr.find("作战开始")
            if btn:
                r = btn.region
                ctx.logger.info(
                    f"[lizhan] Found '{btn.text}' at "
                    f"({r.x + r.w // 2}, {r.y + r.h // 2})"
                )
                await ClickPxOp(
                    r.x + r.w // 2, r.y + r.h // 2, wait=0.3
                ).run(ctx)
                await SleepOp(_LOADING_WAIT).run(ctx)
                ctx.logger.info("=== LizhanCombat: cycle completed ===")
                return TaskResult(
                    status="success",
                    message="历战轮回 cycle completed (restart initiated)",
                )

            ctx.logger.debug(
                f"[lizhan] 准备作战/作战开始 not found (attempt {attempt + 1}/5)"
            )
            await SleepOp(1.0).run(ctx)

        ctx.logger.warning("[lizhan] Could not find 准备作战/作战开始 after restart")
        return TaskResult(
            status="failed",
            message="准备作战/作战开始 not found after restart",
        )
