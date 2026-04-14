"""explore_daily_tasks.py — Explore 每日任务, 弥弥观测站, 公会, 游园街 pages.

Pure exploration: screenshot + OCR dump at each page, no destructive clicks.
Goal: collect coordinates for all UI elements needed by tasks 1-4.
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
    VK_ENTER, VK_ESCAPE, VK_G, VK_H,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.games.aether_gazer.ops.navigate.smart_return import ReturnToHubAction
from anime_game_afk.games.aether_gazer.ops.navigate.wake_hub_ui import WakeHubUiAction
from anime_game_afk.vision.ocr import ocr_find, ocr_find_all, ocr_full
from maa.define import MaaWin32InputMethodEnum, MaaWin32ScreencapMethodEnum

OUT_DIR = Path("assets/aether_gazer/screenshots/explore_tasks")
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


def dump_ocr(img: np.ndarray, label: str, region: Rect | None = None) -> None:
    results = ocr_full(img, region=region)
    logger.info(f"[OCR: {label}] {len(results)} results:")
    for r in sorted(results, key=lambda r: (r.region.y, r.region.x)):
        cx = r.region.x + r.region.w // 2
        cy = r.region.y + r.region.h // 2
        logger.info(
            f"  '{r.text}' conf={r.confidence:.2f} "
            f"at ({r.region.x},{r.region.y}) size=({r.region.w}x{r.region.h}) "
            f"center=({cx},{cy})"
        )


async def return_to_hub(device: DeviceAdapter, ctx: OpContext) -> None:
    """Reliable return to hub."""
    await WakeHubUiAction().run(ctx)
    await asyncio.sleep(0.5)
    await ReturnToHubAction().run(ctx)
    await asyncio.sleep(1.0)


async def explore_daily_tasks(device: DeviceAdapter, ctx: OpContext) -> None:
    """Explore 1: G → 每日任务页面 (daily + weekly tabs, 一键领取)."""
    logger.info("\n" + "=" * 60)
    logger.info("EXPLORE 1: 每日任务页面 (G shortcut)")
    logger.info("=" * 60)

    await return_to_hub(device, ctx)
    snap(device, "hub_before_G")

    # Press G to open daily tasks
    logger.info("Pressing G to open daily tasks")
    device.press_key(VK_G)
    await asyncio.sleep(2.0)
    img = snap(device, "daily_tasks_page")
    dump_ocr(img, "daily_tasks_page")

    # Look for key elements:
    # - 弥弥观测站 button (bottom-left)
    # - 一键领取 button (bottom-right)
    # - 每日任务 / 周常任务 / 剧情任务 tabs (left side)
    logger.info("\n--- Key elements search ---")
    for target in ["弥弥观测站", "一键领取", "每日任务", "周常任务", "剧情任务"]:
        found = ocr_find(img, target)
        if found:
            cx = found.region.x + found.region.w // 2
            cy = found.region.y + found.region.h // 2
            logger.info(f"  '{target}' → center=({cx},{cy})")
        else:
            logger.warning(f"  '{target}' → NOT FOUND")

    # Return
    device.press_key(VK_ESCAPE)
    await asyncio.sleep(1.0)


async def explore_mimi_station(device: DeviceAdapter, ctx: OpContext) -> None:
    """Explore 2: G → 每日任务 → 弥弥观测站."""
    logger.info("\n" + "=" * 60)
    logger.info("EXPLORE 2: 弥弥观测站")
    logger.info("=" * 60)

    await return_to_hub(device, ctx)

    # Press G to open daily tasks
    device.press_key(VK_G)
    await asyncio.sleep(2.0)
    img = snap(device, "daily_before_mimi")

    # Find and click 弥弥观测站
    mimi = ocr_find(img, "弥弥观测站")
    if mimi:
        cx = mimi.region.x + mimi.region.w // 2
        cy = mimi.region.y + mimi.region.h // 2
        logger.info(f"  Clicking '弥弥观测站' at ({cx},{cy})")
        device.click(cx, cy)
    else:
        # Use known coord from pages.py: (110, 820)
        logger.warning("  '弥弥观测站' not found, using fallback (110, 820)")
        device.click(110, 820)

    await asyncio.sleep(2.0)
    img = snap(device, "mimi_station_page")
    dump_ocr(img, "mimi_station_page")

    # Look for key elements:
    # - 一键领取 button
    # - x10 or similar multiplier
    logger.info("\n--- Key elements search ---")
    for target in ["一键领取", "领取", "x10", "X10", "返回"]:
        found = ocr_find(img, target)
        if found:
            cx = found.region.x + found.region.w // 2
            cy = found.region.y + found.region.h // 2
            logger.info(f"  '{target}' → center=({cx},{cy})")
        else:
            logger.warning(f"  '{target}' → NOT FOUND")

    # Return without clicking anything destructive
    device.press_key(VK_ESCAPE)
    await asyncio.sleep(1.0)
    device.press_key(VK_ESCAPE)
    await asyncio.sleep(1.0)


async def explore_guild(device: DeviceAdapter, ctx: OpContext) -> None:
    """Explore 3: Hub bottom → 公会 → 矩阵补给."""
    logger.info("\n" + "=" * 60)
    logger.info("EXPLORE 3: 公会 + 矩阵补给")
    logger.info("=" * 60)

    await return_to_hub(device, ctx)

    # Click guild button (fixed coord from pages.py: 1025, 850)
    logger.info("Clicking 公会 at (1025, 850)")
    device.click(1025, 850)
    await asyncio.sleep(2.0)
    img = snap(device, "guild_page")
    dump_ocr(img, "guild_page")

    # Look for key elements
    logger.info("\n--- Key elements search ---")
    for target in ["矩阵补给", "矩阵供应", "公会成员", "公会任务", "领取"]:
        found = ocr_find(img, target)
        if found:
            cx = found.region.x + found.region.w // 2
            cy = found.region.y + found.region.h // 2
            logger.info(f"  '{target}' → center=({cx},{cy})")
        else:
            logger.warning(f"  '{target}' → NOT FOUND")

    # Click 矩阵补给 if found
    supply = ocr_find(img, "矩阵补给")
    if supply is None:
        supply = ocr_find(img, "补给")
    if supply:
        cx = supply.region.x + supply.region.w // 2
        cy = supply.region.y + supply.region.h // 2
        logger.info(f"  Clicking '{supply.text}' at ({cx},{cy})")
        device.click(cx, cy)
        await asyncio.sleep(2.0)
        img = snap(device, "guild_supply_page")
        dump_ocr(img, "guild_supply_page")

        # Look for 领取 button
        for target in ["领取", "一键领取", "全部领取"]:
            found = ocr_find(img, target)
            if found:
                cx2 = found.region.x + found.region.w // 2
                cy2 = found.region.y + found.region.h // 2
                logger.info(f"  '{target}' → center=({cx2},{cy2})")
    else:
        logger.warning("  矩阵补给 not found in guild page")

    # Return
    device.click(35, 35)
    await asyncio.sleep(1.5)


async def explore_amusement(device: DeviceAdapter, ctx: OpContext) -> None:
    """Explore 4: Hub bottom → 游园街 → panel → various buttons."""
    logger.info("\n" + "=" * 60)
    logger.info("EXPLORE 4: 游园街")
    logger.info("=" * 60)

    await return_to_hub(device, ctx)

    # Click amusement button (fixed coord from pages.py: 1257, 850)
    logger.info("Clicking 游园街 at (1257, 850)")
    device.click(1257, 850)
    await asyncio.sleep(2.0)
    img = snap(device, "amusement_page")
    dump_ocr(img, "amusement_page")

    # Look for key elements
    logger.info("\n--- Key elements search ---")
    for target in ["游园街面板", "面板", "游园任务", "参观", "入住", "导航"]:
        found = ocr_find(img, target)
        if found:
            cx = found.region.x + found.region.w // 2
            cy = found.region.y + found.region.h // 2
            logger.info(f"  '{target}' → center=({cx},{cy})")
        else:
            logger.warning(f"  '{target}' → NOT FOUND")

    # Click 游园街面板 (should be at bottom bar)
    panel_btn = ocr_find(img, "面板")
    if panel_btn is None:
        # Use known coord from pages.py: (1260, 860)
        logger.warning("  '面板' not found, using fallback (1260, 860)")
        device.click(1260, 860)
    else:
        cx = panel_btn.region.x + panel_btn.region.w // 2
        cy = panel_btn.region.y + panel_btn.region.h // 2
        logger.info(f"  Clicking '{panel_btn.text}' at ({cx},{cy})")
        device.click(cx, cy)

    await asyncio.sleep(2.0)
    img = snap(device, "amusement_panel")
    dump_ocr(img, "amusement_panel")

    # Look for key elements in the panel
    logger.info("\n--- Panel elements search ---")
    for target in [
        "自动放置", "一键投喂", "领取收益", "派遣完成",
        "可委托", "一键派遣", "确定", "返回",
    ]:
        found = ocr_find(img, target)
        if found:
            cx = found.region.x + found.region.w // 2
            cy = found.region.y + found.region.h // 2
            logger.info(f"  '{target}' → center=({cx},{cy})")
        else:
            logger.warning(f"  '{target}' → NOT FOUND")

    # Return
    device.press_key(VK_ESCAPE)
    await asyncio.sleep(1.0)
    device.press_key(VK_ESCAPE)
    await asyncio.sleep(1.0)


async def run(device: DeviceAdapter) -> None:
    ctx = OpContext(device=device)

    # Run all explorations in sequence
    await explore_daily_tasks(device, ctx)
    await explore_mimi_station(device, ctx)
    await explore_guild(device, ctx)
    await explore_amusement(device, ctx)

    # Final return to hub
    await return_to_hub(device, ctx)
    snap(device, "final_hub")

    logger.info("\n" + "=" * 60)
    logger.info("ALL EXPLORATIONS COMPLETE")
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
