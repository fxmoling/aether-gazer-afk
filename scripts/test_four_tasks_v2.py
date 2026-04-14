"""test_four_tasks_v2.py — Fixed version with improved return-to-hub logic.

Fixes from v1:
- Task 1: Verify one-click claim result with screenshot
- Return-to-hub: back(35,35) → ESC → if no change then Enter → loop
- Task 4: Fresh exploration + execution
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
from anime_game_afk.games.aether_gazer.ops.perception.identify_page import is_on_page
from anime_game_afk.vision.ocr import ocr_find, ocr_find_all, ocr_full
from maa.define import MaaWin32InputMethodEnum, MaaWin32ScreencapMethodEnum

OUT_DIR = Path("assets/aether_gazer/screenshots/four_tasks_v2")
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


def dump_ocr(img: np.ndarray, label: str) -> None:
    results = ocr_full(img)
    logger.info(f"[OCR: {label}] {len(results)} results:")
    for r in sorted(results, key=lambda r: (r.region.y, r.region.x)):
        cx = r.region.x + r.region.w // 2
        cy = r.region.y + r.region.h // 2
        logger.info(
            f"  '{r.text}' conf={r.confidence:.2f} center=({cx},{cy})"
        )


async def smart_return_to_hub(device: DeviceAdapter, ctx: OpContext) -> None:
    """Smart return-to-hub using 3-step cycle:
    1. If back button area visible (top-left), click it
    2. Press ESC
    3. If screen doesn't change after ESC, press Enter (dismiss popup)
    Repeat until hub detected via template matching.
    """
    logger.info("  [smart_return] Starting return to hub")
    prev_img = None

    for attempt in range(10):
        img = device.screenshot()

        # Check if already at hub
        if is_on_page(img, "main_hub"):
            logger.info(f"  [smart_return] Hub reached after {attempt} steps")
            return

        # Step 1: Try back button (35, 35) — most pages have it
        logger.info(f"  [smart_return][{attempt}] Trying back (35,35)")
        device.click(35, 35)
        await asyncio.sleep(1.5)

        img = device.screenshot()
        if is_on_page(img, "main_hub"):
            logger.info(f"  [smart_return] Hub reached after back click")
            return

        # Step 2: Try ESC
        logger.info(f"  [smart_return][{attempt}] Trying ESC")
        prev_img = img
        device.press_key(VK_ESCAPE)
        await asyncio.sleep(1.5)

        img = device.screenshot()
        if is_on_page(img, "main_hub"):
            logger.info(f"  [smart_return] Hub reached after ESC")
            return

        # Step 3: If screen looks the same after ESC, press Enter
        # (popup may need Enter to dismiss, not ESC)
        if prev_img is not None:
            # Simple diff check: mean absolute difference
            diff = np.mean(np.abs(
                img.astype(float) - prev_img.astype(float)
            ))
            if diff < 5.0:  # Very similar = ESC had no effect
                logger.info(
                    f"  [smart_return][{attempt}] "
                    f"Screen unchanged (diff={diff:.1f}), trying Enter"
                )
                device.press_key(VK_ENTER)
                await asyncio.sleep(1.5)

    # Final fallback
    logger.warning("  [smart_return] Fallback to ReturnToHubAction")
    await WakeHubUiAction().run(ctx)
    await asyncio.sleep(0.5)
    await ReturnToHubAction().run(ctx)
    await asyncio.sleep(1.0)


async def ensure_hub(device: DeviceAdapter, ctx: OpContext) -> None:
    """Ensure we're at hub before starting a task."""
    await WakeHubUiAction().run(ctx)
    await asyncio.sleep(0.5)
    await ReturnToHubAction().run(ctx)
    await asyncio.sleep(1.0)


async def rapid_click(device: DeviceAdapter, x: int, y: int, times: int, interval: float = 0.5) -> None:
    for i in range(times):
        device.click(x, y)
        await asyncio.sleep(interval)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Task 1: 弥弥观测站
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def task1_mimi_station(device: DeviceAdapter, ctx: OpContext) -> None:
    logger.info("\n" + "=" * 60)
    logger.info("TASK 1: 弥弥观测站")
    logger.info("=" * 60)

    await ensure_hub(device, ctx)

    # G → daily tasks
    logger.info("[1.1] Press G → daily tasks")
    device.press_key(VK_G)
    await asyncio.sleep(2.0)
    snap(device, "t1_daily_tasks")

    # Click 弥弥观测站 (110, 820)
    logger.info("[1.2] Click 弥弥观测站 at (110, 820)")
    device.click(110, 820)
    await asyncio.sleep(2.0)
    img = snap(device, "t1_mimi_station")

    # Click 一键领取 ×10 (OCR verified: center=(1205, 809))
    logger.info("[1.3] Rapid click 一键领取 at (1205, 809) × 10")
    await rapid_click(device, 1205, 809, 10, 0.5)
    img = snap(device, "t1_after_claim")
    dump_ocr(img, "t1_after_claim")

    # Look for x8/x10 and click if found
    logger.info("[1.4] Search for x8/x10")
    x_btn = ocr_find(img, "x10")
    if x_btn is None:
        x_btn = ocr_find(img, "X10")
    if x_btn is None:
        x_btn = ocr_find(img, "x8")
    if x_btn is None:
        x_btn = ocr_find(img, "X8")
    if x_btn is None:
        # Search for 缩短 (shorten) button
        x_btn = ocr_find(img, "缩短")

    if x_btn:
        cx = x_btn.region.x + x_btn.region.w // 2
        cy = x_btn.region.y + x_btn.region.h // 2
        logger.info(f"  Found '{x_btn.text}' at ({cx},{cy}), clicking ×10")
        await rapid_click(device, cx, cy, 10, 0.5)
        snap(device, "t1_after_x_btn")
    else:
        logger.info("  x8/x10/缩短 not found")

    # Return to hub
    logger.info("[1.5] Return to hub")
    await smart_return_to_hub(device, ctx)
    snap(device, "t1_done")
    logger.info("TASK 1 COMPLETE")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Task 2: 每日/周常任务领取
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def task2_daily_weekly_claim(device: DeviceAdapter, ctx: OpContext) -> None:
    logger.info("\n" + "=" * 60)
    logger.info("TASK 2: 每日/周常任务领取")
    logger.info("=" * 60)

    await ensure_hub(device, ctx)

    # G → daily tasks
    logger.info("[2.1] Press G → daily tasks")
    device.press_key(VK_G)
    await asyncio.sleep(2.0)
    snap(device, "t2_daily_tasks")

    # 一键领取 ×5 (daily)
    logger.info("[2.2] Rapid click 一键领取 at (1480, 860) × 5 (daily)")
    await rapid_click(device, 1480, 860, 5, 0.5)
    snap(device, "t2_after_daily")

    # 周常任务 tab (80, 195)
    logger.info("[2.3] Click 周常任务 at (80, 195)")
    device.click(80, 195)
    await asyncio.sleep(1.5)
    snap(device, "t2_weekly")

    # 一键领取 ×5 (weekly)
    logger.info("[2.4] Rapid click 一键领取 at (1480, 860) × 5 (weekly)")
    await rapid_click(device, 1480, 860, 5, 0.5)
    snap(device, "t2_after_weekly")

    # Return
    logger.info("[2.5] Return to hub")
    device.press_key(VK_ESCAPE)
    await asyncio.sleep(1.0)
    await smart_return_to_hub(device, ctx)
    snap(device, "t2_done")
    logger.info("TASK 2 COMPLETE")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Task 3: 公会矩阵补给
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def task3_guild_supply(device: DeviceAdapter, ctx: OpContext) -> None:
    logger.info("\n" + "=" * 60)
    logger.info("TASK 3: 公会矩阵补给")
    logger.info("=" * 60)

    await ensure_hub(device, ctx)

    # Click 公会 (1025, 850)
    logger.info("[3.1] Click 公会 at (1025, 850)")
    device.click(1025, 850)
    await asyncio.sleep(2.0)
    snap(device, "t3_guild")

    # OCR find 矩阵补给
    logger.info("[3.2] Find and click '矩阵补给'")
    img = device.screenshot()
    supply = ocr_find(img, "矩阵补给")
    if supply:
        cx = supply.region.x + supply.region.w // 2
        cy = supply.region.y + supply.region.h // 2
        logger.info(f"  Found at ({cx},{cy})")
        device.click(cx, cy)
    else:
        logger.warning("  Fallback (1430, 870)")
        device.click(1430, 870)
    await asyncio.sleep(2.0)
    snap(device, "t3_supply")

    # OCR find 领取
    logger.info("[3.3] Find and click '领取'")
    img = device.screenshot()
    claim = ocr_find(img, "领取")
    if claim:
        cx = claim.region.x + claim.region.w // 2
        cy = claim.region.y + claim.region.h // 2
        logger.info(f"  Found '领取' at ({cx},{cy})")
        device.click(cx, cy)
        await asyncio.sleep(1.5)
    else:
        logger.info("  '领取' not found (already claimed?)")

    snap(device, "t3_after_claim")

    # Return — use smart_return which handles popups
    logger.info("[3.4] Return to hub")
    await smart_return_to_hub(device, ctx)
    snap(device, "t3_done")
    logger.info("TASK 3 COMPLETE")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Task 4: 游园街 — with fresh exploration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def task4_amusement(device: DeviceAdapter, ctx: OpContext) -> None:
    logger.info("\n" + "=" * 60)
    logger.info("TASK 4: 游园街")
    logger.info("=" * 60)

    await ensure_hub(device, ctx)

    # Click 游园街 (1257, 850)
    logger.info("[4.1] Click 游园街 at (1257, 850)")
    device.click(1257, 850)
    await asyncio.sleep(2.0)
    img = snap(device, "t4_amusement")

    # Click 游园街面板 (1240, 860)
    logger.info("[4.2] Click 游园街面板 at (1240, 860)")
    device.click(1240, 860)
    await asyncio.sleep(2.0)
    img = snap(device, "t4_panel")
    dump_ocr(img, "t4_panel")

    # Click 自动放置 (OCR verified: center=(1084, 826))
    logger.info("[4.3] Click 自动放置 at (1084, 826)")
    device.click(1084, 826)
    await asyncio.sleep(1.5)
    snap(device, "t4_auto_place")

    # Click 一键投喂 (OCR verified: center=(1368, 826))
    logger.info("[4.4] Click 一键投喂 at (1368, 826)")
    device.click(1368, 826)
    await asyncio.sleep(1.5)
    img = snap(device, "t4_after_feed")
    dump_ocr(img, "t4_after_feed")

    # 领取收益 (OCR)
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

    # 派遣完成 or 可委托 (OCR)
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

        # 确定 (Enter)
        logger.info("[4.7] Confirm (Enter)")
        device.press_key(VK_ENTER)
        await asyncio.sleep(1.5)
        snap(device, "t4_after_confirm")

        # 一键派遣 (OCR)
        logger.info("[4.8] Find '一键派遣'")
        img = device.screenshot()
        auto_d = ocr_find(img, "一键派遣")
        if auto_d:
            cx = auto_d.region.x + auto_d.region.w // 2
            cy = auto_d.region.y + auto_d.region.h // 2
            logger.info(f"  Found '一键派遣' at ({cx},{cy})")
            device.click(cx, cy)
            await asyncio.sleep(1.5)
            device.press_key(VK_ENTER)
            await asyncio.sleep(1.0)
        else:
            logger.info("  '一键派遣' not found")
        snap(device, "t4_after_dispatch")
    else:
        logger.info("  No dispatch targets found")

    # ESC ×2 then smart return
    logger.info("[4.9] ESC ×2 + return to hub")
    device.press_key(VK_ESCAPE)
    await asyncio.sleep(1.0)
    device.press_key(VK_ESCAPE)
    await asyncio.sleep(1.0)
    await smart_return_to_hub(device, ctx)
    snap(device, "t4_done")
    logger.info("TASK 4 COMPLETE")


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
