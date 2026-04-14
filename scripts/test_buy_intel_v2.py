"""test_buy_intel_v2.py — Buy all available intel shards from daily shop.

Strategy: always buy the FIRST intel item in the row. After each purchase,
the bought item moves to end of row, so the next available one slides to
first position. Repeat until no more available.

Safety:
- OCR verifies "情报" in popup before every purchase
- Scrolls to top before scanning to avoid wrong section
- Stops when first item is sold out or no popup appears
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
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ENTER, VK_ESCAPE
from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.games.aether_gazer.ops.navigate.smart_return import ReturnToHubAction
from anime_game_afk.games.aether_gazer.ops.navigate.goto_page import GotoPageAction
from anime_game_afk.games.aether_gazer.ops.navigate.wake_hub_ui import WakeHubUiAction
from anime_game_afk.vision.ocr import ocr_find, ocr_find_all
from maa.define import MaaWin32InputMethodEnum, MaaWin32ScreencapMethodEnum

OUT_DIR = Path("assets/aether_gazer/screenshots/buy_intel_v2")


def snap(device: DeviceAdapter, label: str) -> np.ndarray:
    img = device.screenshot()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    thumb = cv2.resize(img, (800, 450))
    cv2.imwrite(str(OUT_DIR / f"{label}.jpg"), thumb, [cv2.IMWRITE_JPEG_QUALITY, 90])
    logger.info(f"[snap] {label}")
    return img


async def navigate_to_daily_purchase(device: DeviceAdapter, ctx: OpContext) -> bool:
    """Navigate from anywhere to daily purchase page. Returns success."""
    # Wake + hub
    await WakeHubUiAction().run(ctx)
    await asyncio.sleep(1.0)
    result = await ReturnToHubAction().run(ctx)
    if not result.success:
        logger.error("Cannot return to hub")
        return False
    await asyncio.sleep(1.0)

    # Hub → shop
    result = await GotoPageAction(target_page_id="shop").run(ctx)
    await asyncio.sleep(1.5)

    # Shop → trade area
    device.click(89, 817)
    await asyncio.sleep(2.0)

    # Trade → daily purchase tab
    device.click(130, 125)
    await asyncio.sleep(2.0)

    # Scroll to top to ensure we see the intel section
    device.swipe(800, 200, 800, 600, duration=300)
    await asyncio.sleep(1.0)

    # Verify
    img = snap(device, "nav_daily_purchase")
    result = ocr_find(img, "修正者情报")
    if result:
        logger.info("On daily purchase page, intel section visible")
        return True
    else:
        logger.error("Daily purchase page not showing intel section")
        return False


def find_first_intel(img: np.ndarray) -> tuple[str, int, int] | None:
    """Find the first (leftmost) intel item in the top row.

    Returns (name, center_x, center_y) or None if none found.
    """
    intel_region = Rect(200, 130, 1300, 350)
    items = ocr_find_all(img, "情报", region=intel_region)

    # Filter out section header
    items = [i for i in items if "修正者" not in i.text]
    if not items:
        return None

    # Sort by x position (leftmost first)
    items.sort(key=lambda i: i.region.x)
    first = items[0]
    cx = first.region.x + first.region.w // 2
    cy = first.region.y + first.region.h // 2
    return (first.text, cx, cy)


def is_sold_out_at(img: np.ndarray, item_x: int) -> bool:
    """Check if the item at given x position is sold out."""
    sold = ocr_find_all(img, "售")
    for s in sold:
        sx = s.region.x + s.region.w // 2
        if abs(sx - item_x) < 120:
            return True
    return False


async def buy_loop(device: DeviceAdapter) -> int:
    """Buy intel items one by one. Returns count purchased."""
    purchased = 0
    max_attempts = 10  # Safety cap

    for attempt in range(max_attempts):
        # Fresh screenshot every iteration
        img = snap(device, f"scan_{attempt}")

        # Find first intel item
        first = find_first_intel(img)
        if first is None:
            logger.info("No more intel items found, done")
            break

        name, cx, cy = first
        logger.info(f"[{attempt+1}] First intel: '{name}' at ({cx},{cy})")

        # Check if sold out
        if is_sold_out_at(img, cx):
            logger.info(f"'{name}' is sold out, all done")
            break

        # Click the item
        device.click(cx, cy)
        await asyncio.sleep(1.5)

        # Verify popup
        popup_img = snap(device, f"popup_{attempt}")
        buy_btn = ocr_find(popup_img, "购买")
        has_intel = ocr_find(popup_img, "情报")

        if buy_btn is None:
            logger.warning("No purchase popup appeared, stopping")
            device.press_key(VK_ESCAPE)
            await asyncio.sleep(1.0)
            break

        if has_intel is None:
            logger.error("Popup does NOT contain '情报' — SAFETY STOP")
            device.press_key(VK_ESCAPE)
            await asyncio.sleep(1.0)
            break

        # Click purchase button (OCR-located)
        bx = buy_btn.region.x + buy_btn.region.w // 2
        by = buy_btn.region.y + buy_btn.region.h // 2
        logger.info(f"  Purchasing '{name}' — clicking buy at ({bx},{by})")
        device.click(bx, by)
        await asyncio.sleep(1.5)

        # Dismiss result popup
        device.press_key(VK_ENTER)
        await asyncio.sleep(1.0)

        purchased += 1
        snap(device, f"after_buy_{attempt}")
        logger.info(f"  '{name}' purchased (total: {purchased})")

    return purchased


async def run(device: DeviceAdapter) -> None:
    ctx = OpContext(device=device)

    # Step 1: Navigate to daily purchase
    logger.info("=" * 50)
    logger.info("Step 1: Navigate to daily purchase page")
    if not await navigate_to_daily_purchase(device, ctx):
        return

    # Step 2: Buy loop
    logger.info("=" * 50)
    logger.info("Step 2: Buying intel shards")
    count = await buy_loop(device)

    # Step 3: Return to hub
    logger.info("=" * 50)
    logger.info(f"Step 3: Return to hub (purchased {count} items)")
    await ReturnToHubAction().run(ctx)
    await asyncio.sleep(1.0)
    snap(device, "final_hub")
    logger.info(f"DONE: Purchased {count} intel shards")


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
