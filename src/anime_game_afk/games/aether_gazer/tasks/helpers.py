"""Shared helpers for task implementations.

is_at_hub / is_at_hub_with_ocr: **Centralized** hub detection.
smart_return_to_hub: Reliably return to hub from any depth.
rapid_click: Click a fixed position multiple times.

All hub detection MUST go through is_at_hub() or is_at_hub_with_ocr().
Do NOT scatter "前往作战"/"探测" checks across files.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import numpy as np

from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ENTER, VK_ESCAPE
from anime_game_afk.games.aether_gazer.ops.navigate.smart_return import ReturnToHubAction
from anime_game_afk.games.aether_gazer.ops.navigate.wake_hub_ui import WakeHubUiAction
from anime_game_afk.games.aether_gazer.ops.perception.identify_page import is_on_page
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext
from anime_game_afk.vision.ocr import ocr_once, OcrResult

if TYPE_CHECKING:
    pass

# ── Hub detection ──
# Requires ALL 4 keywords visible via OCR to confirm hub.
# Cost: zero when reusing an existing OcrResult — pure string matching.
_HUB_KEYWORDS = ("前往作战", "探测", "修正者", "仓库")


def is_at_hub(img: np.ndarray) -> bool:
    """Check if screenshot shows main hub. Authoritative hub check.

    Strategy: fast template match first (5ms), then OCR fallback (2s).
    Use is_at_hub_with_ocr() if you already have an OcrResult.
    """
    if is_on_page(img, "main_hub"):
        return True
    ocr = ocr_once(img)
    return ocr.has_all(*_HUB_KEYWORDS)


def is_at_hub_with_ocr(img: np.ndarray, ocr: OcrResult) -> bool:
    """Check hub using an existing OcrResult. Zero extra OCR cost.

    Use this when you already called ocr_once() and want to reuse
    the result for hub detection + other checks in the same pass.
    """
    if is_on_page(img, "main_hub"):
        return True
    return ocr.has_all(*_HUB_KEYWORDS)


# ── Return to hub ──


async def smart_return_to_hub(ctx: TaskContext, max_attempts: int = 10) -> bool:
    """Reliably return to hub from any page depth.

    Strategy (cycles until hub detected):
    1. Check if already at hub (template match + 4-keyword OCR)
    2. Click back button (35, 35) — most pages have it
    3. Press ESC — closes overlays/panels
    4. After ESC, check for "退出游戏" dialog (= we're at hub)
    5. If screen unchanged after ESC → press Enter (dismiss popup)

    Uses ocr_once for batch OCR — one pass per screenshot.
    """
    ctx.logger.info("  [smart_return] Starting return to hub")
    prev_img = None

    for attempt in range(max_attempts):
        img = ctx.device.screenshot()

        # One OCR pass for hub check + idle + exit dialog
        ocr = ocr_once(img)

        if is_at_hub_with_ocr(img, ocr):
            ctx.logger.info(
                f"  [smart_return] Hub reached after {attempt} steps"
            )
            return True

        # Idle screen ("正在播放") — click to wake
        if ocr.has("正在播放"):
            ctx.logger.info(
                f"  [smart_return][{attempt}] Idle screen, clicking to wake"
            )
            ctx.device.click(800, 400)
            await asyncio.sleep(1.5)
            continue

        # Step 1: Try back button (35, 35)
        ctx.logger.debug(f"  [smart_return][{attempt}] Trying back (35,35)")
        ctx.device.click(35, 35)
        await asyncio.sleep(1.5)

        img = ctx.device.screenshot()
        if is_at_hub(img):
            ctx.logger.info("  [smart_return] Hub reached after back click")
            return True

        # Step 2: Try ESC
        ctx.logger.debug(f"  [smart_return][{attempt}] Trying ESC")
        prev_img = img
        ctx.device.press_key(VK_ESCAPE)
        await asyncio.sleep(1.5)

        img = ctx.device.screenshot()
        ocr = ocr_once(img)

        if is_at_hub_with_ocr(img, ocr):
            ctx.logger.info("  [smart_return] Hub reached after ESC")
            return True

        # ESC triggered "退出游戏" dialog → we ARE at hub
        if ocr.has("退出游戏") or ocr.has("是否退出"):
            ctx.logger.info(
                "  [smart_return] Exit dialog detected — at hub, cancelling"
            )
            ctx.device.press_key(VK_ESCAPE)
            await asyncio.sleep(1.0)
            return True

        # Step 3: Screen unchanged → press Enter
        if prev_img is not None:
            diff = float(np.mean(np.abs(
                img.astype(float) - prev_img.astype(float)
            )))
            if diff < 5.0:
                ctx.logger.debug(
                    f"  [smart_return][{attempt}] "
                    f"Screen unchanged (diff={diff:.1f}), trying Enter"
                )
                ctx.device.press_key(VK_ENTER)
                await asyncio.sleep(1.5)

    # Final fallback
    ctx.logger.warning("  [smart_return] Fallback to ReturnToHubAction")
    await WakeHubUiAction().run(ctx)
    await asyncio.sleep(0.5)
    await ReturnToHubAction().run(ctx)
    await asyncio.sleep(1.0)
    return False


# ── Utilities ──


async def rapid_click(
    ctx: TaskContext,
    x: int,
    y: int,
    times: int = 5,
    interval: float = 0.5,
) -> None:
    """Click a fixed position multiple times rapidly."""
    for _ in range(times):
        ctx.device.click(x, y)
        await asyncio.sleep(interval)
