"""test_four_tasks.py — Execute all 4 daily tasks.

Task 1: 弥弥观测站 — G → 弥弥观测站 → 一键领取 ×10 → x10 if found → return
Task 2: 每日/周常任务领取 — G → 一键领取 ×10 → 周常任务 → 一键领取 ×10 → return
Task 3: 公会矩阵补给 — 公会 → 矩阵补给 → 领取 → return
Task 4: 游园街 — 游园街 → 面板 → 自动放置 → 一键投喂 → 领取收益
         → 派遣完成/可委托 → 确定 → 一键派遣 → ESC×2 → return

All coordinates verified from exploration screenshots (2026-04-05).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import cv2
import numpy as np
from loguru import logger

from anime_game_afk.core.types import DeviceConfig, Rect
from anime_game_afk.core.device import DeviceAdapter
from anime_game_afk.games.aether_gazer.knowledge.keys import (
    VK_ENTER, VK_ESCAPE, VK_G,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.games.aether_gazer.ops.navigate.smart_return import ReturnToHubAction
from anime_game_afk.games.aether_gazer.ops.navigate.wake_hub_ui import WakeHubUiAction
from anime_game_afk.vision.ocr import ocr_find, ocr_find_all, ocr_full
from maa.define import MaaWin32InputMethodEnum, MaaWin32ScreencapMethodEnum

OUT_DIR = Path("assets/aether_gazer/screenshots/four_tasks")
snap_counter = 0


def snap(device: DeviceAdapter, label: str) -> np.ndarray:
    global snap_counter
    snap_counter += 1
    img = device.screenshot()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{snap_counter:03d}_{label}.jpg"
    cv2.imwrite(
        str(OUT_DIR / filename),
        cv2.resize(img, (800, 450)),
        [cv2.IMWRITE_JPEG_QUALITY, 90],
    )
    logger.info(f"[snap] #{snap_counter} {label}")
    return img


async def return_to_hub(device: DeviceAdapter, ctx: OpContext) -> None:
    await WakeHubUiAction().run(ctx)
    await asyncio.sleep(0.5)
    await ReturnToHubAction().run(ctx)
    await asyncio.sleep(1.0)


async def rapid_click(device: DeviceAdapter, x: int, y: int, times: int, interval: float = 0.5) -> None:
    """Click a fixed position rapidly."""
    for i in range(times):
        device.click(x, y)
        await asyncio.sleep(interval)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Task 1: 弥弥观测站
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def task1_mimi_station(device: DeviceAdapter, ctx: OpContext) -> None:
    """弥弥观测站: G → 弥弥观测站(110,820) → 一键领取 ×10 → x10 → return."""
    logger.info("\n" + "=" * 60)
    logger.info("TASK 1: 弥弥观测站")
    logger.info("=" * 60)

    await return_to_hub(device, ctx)

    # Step 1: G → daily tasks
    logger.info("[1.1] Press G → daily tasks")
    device.press_key(VK_G)
    await asyncio.sleep(2.0)
    snap(device, "t1_daily_tasks")

    # Step 2: Click 弥弥观测站 (fixed coord from pages.py: 110, 820)
    logger.info("[1.2] Click 弥弥观测站 at (110, 820)")
    device.click(110, 820)
    await asyncio.sleep(2.0)
    snap(device, "t1_mimi_station")

    # Step 3: Click 一键领取 ×10 (right bottom area ~1410, 860)
    logger.info("[1.3] Rapid click 一键领取 at (1410, 860) × 10")
    await rapid_click(device, 1410, 860, 10, 0.5)
    snap(device, "t1_after_claim")

    # Step 4: Look for x10 via OCR and click if found
    logger.info("[1.4] Search for x10 and click if found")
    img = device.screenshot()
    x10 = ocr_find(img, "x10")
    if x10 is None:
        x10 = ocr_find(img, "X10")
    if x10 is None:
        x10 = ocr_find(img, "x8")
    if x10 is None:
        x10 = ocr_find(img, "X8")

    if x10:
        cx = x10.region.x + x10.region.w // 2
        cy = x10.region.y + x10.region.h // 2
        logger.info(f"  Found '{x10.text}' at ({cx},{cy}), rapid clicking ×10")
        await rapid_click(device, cx, cy, 10, 0.5)
        snap(device, "t1_after_x10")
    else:
        logger.info("  x10/x8 not found, skipping")
        # Dump OCR to see what's there
        results = ocr_full(img)
        for r in results:
            if "x" in r.text.lower() or "缩" in r.text:
                cx = r.region.x + r.region.w // 2
                cy = r.region.y + r.region.h // 2
                logger.info(f"  Possible match: '{r.text}' at ({cx},{cy})")

    # Step 5: Return to hub via back button (top-left circle ~35,35)
    logger.info("[1.5] Return to hub via back (35,35)")
    device.click(35, 35)
    await asyncio.sleep(1.5)
    device.press_key(VK_ESCAPE)
    await asyncio.sleep(1.0)
    await return_to_hub(device, ctx)
    snap(device, "t1_done")
    logger.info("TASK 1 COMPLETE")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Task 2: 每日/周常任务领取
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def task2_daily_weekly_claim(device: DeviceAdapter, ctx: OpContext) -> None:
    """每日+周常任务: G → 一键领取 ×10 → 周常任务 → 一键领取 ×10 → return."""
    logger.info("\n" + "=" * 60)
    logger.info("TASK 2: 每日/周常任务领取")
    logger.info("=" * 60)

    await return_to_hub(device, ctx)

    # Step 1: G → daily tasks (already on 每日任务 tab by default)
    logger.info("[2.1] Press G → daily tasks")
    device.press_key(VK_G)
    await asyncio.sleep(2.0)
    snap(device, "t2_daily_tasks")

    # Step 2: Click 一键领取 ×10 (daily rewards, bottom-right ~1480, 860)
    logger.info("[2.2] Rapid click 一键领取 at (1480, 860) × 10 (daily)")
    await rapid_click(device, 1480, 860, 10, 0.5)
    snap(device, "t2_after_daily_claim")

    # Step 3: Click 周常任务 tab (left side ~80, 195)
    logger.info("[2.3] Click 周常任务 tab at (80, 195)")
    device.click(80, 195)
    await asyncio.sleep(1.5)
    snap(device, "t2_weekly_tasks")

    # Step 4: Click 一键领取 ×10 (weekly rewards, same position ~1480, 860)
    logger.info("[2.4] Rapid click 一键领取 at (1480, 860) × 10 (weekly)")
    await rapid_click(device, 1480, 860, 10, 0.5)
    snap(device, "t2_after_weekly_claim")

    # Step 5: Return to hub
    logger.info("[2.5] Return to hub")
    device.press_key(VK_ESCAPE)
    await asyncio.sleep(1.0)
    await return_to_hub(device, ctx)
    snap(device, "t2_done")
    logger.info("TASK 2 COMPLETE")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Task 3: 公会矩阵补给
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def task3_guild_supply(device: DeviceAdapter, ctx: OpContext) -> None:
    """公会矩阵补给: 公会(1025,850) → 矩阵补给(OCR) → 领取(OCR) → return."""
    logger.info("\n" + "=" * 60)
    logger.info("TASK 3: 公会矩阵补给")
    logger.info("=" * 60)

    await return_to_hub(device, ctx)

    # Step 1: Click 公会 (fixed coord 1025, 850)
    logger.info("[3.1] Click 公会 at (1025, 850)")
    device.click(1025, 850)
    await asyncio.sleep(2.0)
    snap(device, "t3_guild")

    # Step 2: Find and click 矩阵补给 (OCR — bottom bar)
    logger.info("[3.2] Find and click '矩阵补给'")
    img = device.screenshot()
    supply = ocr_find(img, "矩阵补给")
    if supply:
        cx = supply.region.x + supply.region.w // 2
        cy = supply.region.y + supply.region.h // 2
        logger.info(f"  Found '矩阵补给' at ({cx},{cy})")
        device.click(cx, cy)
    else:
        # Fallback from exploration: ~(1430, 870)
        logger.warning("  '矩阵补给' not found, using fallback (1430, 870)")
        device.click(1430, 870)
    await asyncio.sleep(2.0)
    snap(device, "t3_supply_page")

    # Step 3: Find and click 领取 button (OCR)
    logger.info("[3.3] Find and click '领取'")
    img = device.screenshot()
    claim = ocr_find(img, "领取")
    if claim:
        cx = claim.region.x + claim.region.w // 2
        cy = claim.region.y + claim.region.h // 2
        logger.info(f"  Found '领取' at ({cx},{cy}), clicking")
        device.click(cx, cy)
        await asyncio.sleep(1.5)

        # Dismiss any reward popup
        device.press_key(VK_ENTER)
        await asyncio.sleep(1.0)
        snap(device, "t3_after_claim")
    else:
        logger.info("  '领取' not found (may already be claimed)")
        snap(device, "t3_no_claim")

    # Step 4: Return to hub
    logger.info("[3.4] Return to hub")
    device.click(35, 35)
    await asyncio.sleep(1.5)
    await return_to_hub(device, ctx)
    snap(device, "t3_done")
    logger.info("TASK 3 COMPLETE")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Task 4: 游园街
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def task4_amusement(device: DeviceAdapter, ctx: OpContext) -> None:
    """游园街: 面板 → 自动放置 → 一键投喂 → 领取收益 → 委托 → 确定 → 一键派遣 → ESC×2."""
    logger.info("\n" + "=" * 60)
    logger.info("TASK 4: 游园街")
    logger.info("=" * 60)

    await return_to_hub(device, ctx)

    # Step 1: Click 游园街 (fixed coord 1257, 850)
    logger.info("[4.1] Click 游园街 at (1257, 850)")
    device.click(1257, 850)
    await asyncio.sleep(2.0)
    snap(device, "t4_amusement")

    # Step 2: Click 游园街面板 (fixed coord ~1240, 860)
    logger.info("[4.2] Click 游园街面板 at (1240, 860)")
    device.click(1240, 860)
    await asyncio.sleep(2.0)
    img = snap(device, "t4_panel")

    # Step 3: Click 自动放置 (fixed coord ~1200, 860 from panel bottom)
    logger.info("[4.3] Click 自动放置 at (1200, 860)")
    device.click(1200, 860)
    await asyncio.sleep(1.5)
    snap(device, "t4_after_auto_place")

    # Step 4: Click 一键投喂 (fixed coord ~1450, 860 from panel bottom)
    logger.info("[4.4] Click 一键投喂 at (1450, 860)")
    device.click(1450, 860)
    await asyncio.sleep(1.5)
    snap(device, "t4_after_feed")

    # Step 5: 领取收益 (OCR — in the 餐厅 section)
    logger.info("[4.5] Find and click '领取收益'")
    img = device.screenshot()
    income = ocr_find(img, "领取收益")
    if income:
        cx = income.region.x + income.region.w // 2
        cy = income.region.y + income.region.h // 2
        logger.info(f"  Found '领取收益' at ({cx},{cy})")
        device.click(cx, cy)
        await asyncio.sleep(1.5)
        # Dismiss reward popup
        device.press_key(VK_ENTER)
        await asyncio.sleep(1.0)
    else:
        logger.info("  '领取收益' not found")
    snap(device, "t4_after_income")

    # Step 6: Find "派遣完成" or "可委托" (OCR) — click first one found
    logger.info("[4.6] Find '派遣完成' or '可委托'")
    img = device.screenshot()
    dispatch = ocr_find(img, "派遣完成")
    if dispatch is None:
        dispatch = ocr_find(img, "可委托")
    if dispatch:
        cx = dispatch.region.x + dispatch.region.w // 2
        cy = dispatch.region.y + dispatch.region.h // 2
        logger.info(f"  Found '{dispatch.text}' at ({cx},{cy})")
        device.click(cx, cy)
        await asyncio.sleep(1.5)
        snap(device, "t4_dispatch_popup")

        # Step 7: Click 确定 (popup, center area ~800, 600)
        logger.info("[4.7] Click 确定 at center (~800, 600)")
        # Use Enter as shortcut for confirm
        device.press_key(VK_ENTER)
        await asyncio.sleep(1.5)
        snap(device, "t4_after_confirm")

        # Step 8: Click 一键派遣 (should appear after confirm)
        logger.info("[4.8] Find and click '一键派遣'")
        img = device.screenshot()
        auto_dispatch = ocr_find(img, "一键派遣")
        if auto_dispatch:
            cx = auto_dispatch.region.x + auto_dispatch.region.w // 2
            cy = auto_dispatch.region.y + auto_dispatch.region.h // 2
            logger.info(f"  Found '一键派遣' at ({cx},{cy})")
            device.click(cx, cy)
            await asyncio.sleep(1.5)
            # Dismiss any popup
            device.press_key(VK_ENTER)
            await asyncio.sleep(1.0)
        else:
            logger.info("  '一键派遣' not found")
        snap(device, "t4_after_dispatch")
    else:
        logger.info("  Neither '派遣完成' nor '可委托' found")

    # Step 9: ESC ×2 to return to hub
    logger.info("[4.9] ESC × 2 to return")
    device.press_key(VK_ESCAPE)
    await asyncio.sleep(1.0)
    device.press_key(VK_ESCAPE)
    await asyncio.sleep(1.0)
    # Ensure back at hub
    await return_to_hub(device, ctx)
    snap(device, "t4_done")
    logger.info("TASK 4 COMPLETE")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def run(device: DeviceAdapter) -> None:
    ctx = OpContext(device=device)

    await task1_mimi_station(device, ctx)
    await task2_daily_weekly_claim(device, ctx)
    await task3_guild_supply(device, ctx)
    await task4_amusement(device, ctx)

    snap(device, "all_done")
    logger.info("\n" + "=" * 60)
    logger.info("ALL 4 TASKS COMPLETE")
    logger.info("=" * 60)


def main() -> None:
    config = DeviceConfig(
        window_title="AetherGazer",
        screencap_method=MaaWin32ScreencapMethodEnum.FramePool,
        mouse_method=MaaWin32InputMethodEnum.SendMessageWithCursorPos,
        keyboard_method=MaaWin32InputMethodEnum.SendMessageWithCursorPos,
    )
    device = DeviceAdapter(config)
    device.connect()
    try:
        asyncio.run(run(device))
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        device.disconnect()


if __name__ == "__main__":
    main()
