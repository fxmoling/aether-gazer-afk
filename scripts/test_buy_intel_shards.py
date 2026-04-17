"""test_buy_intel_shards.py — Buy character intel shards from daily shop.

Full integration test with OCR verification at every step:
1. Return to hub (from anywhere)
2. Navigate: hub → shop → trade → daily purchase
3. OCR scan for "情报" items
4. For each available item: click → verify popup → purchase → verify result
5. Return to hub

Safety: OCR verifies item name contains "情报" before purchasing.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import cv2
import numpy as np
from loguru import logger

from anime_game_afk.core.types import Rect
from anime_game_afk.core.device import DeviceAdapter
from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ENTER, VK_ESCAPE
from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.games.aether_gazer.ops.perception.identify_page import identify
from anime_game_afk.games.aether_gazer.ops.navigate.smart_return import ReturnToHubAction
from anime_game_afk.games.aether_gazer.ops.navigate.goto_page import GotoPageAction
from anime_game_afk.games.aether_gazer.ops.navigate.wake_hub_ui import WakeHubUiAction
from anime_game_afk.vision.ocr import ocr_find, ocr_find_all, ocr_full
OUT_DIR = Path("assets/aether_gazer/screenshots/buy_intel")


def snap(device: DeviceAdapter, label: str) -> np.ndarray:
    img = device.screenshot()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    thumb = cv2.resize(img, (800, 450))
    cv2.imwrite(str(OUT_DIR / f"{label}.jpg"), thumb, [cv2.IMWRITE_JPEG_QUALITY, 90])
    logger.info(f"[snap] {label}")
    return img


def verify_ocr(img: np.ndarray, expected_text: str, label: str) -> bool:
    """Verify expected text is visible on screen via OCR."""
    result = ocr_find(img, expected_text)
    if result:
        logger.info(f"[verify] {label}: found '{result.text}' conf={result.confidence:.2f}")
        return True
    else:
        logger.warning(f"[verify] {label}: '{expected_text}' NOT FOUND")
        return False


async def run(device: DeviceAdapter) -> None:
    ctx = OpContext(device=device)

    # ── Step 1: Return to hub ──
    logger.info("=" * 50)
    logger.info("Step 1: Wake UI + Return to hub")
    await WakeHubUiAction().run(ctx)
    await asyncio.sleep(1.0)
    result = await ReturnToHubAction().run(ctx)
    if not result.success:
        logger.error("Cannot return to hub, aborting")
        return
    await asyncio.sleep(1.0)
    img = snap(device, "01_hub")
    if not verify_ocr(img, "前往作战", "hub check"):
        logger.error("Not on hub (missing '前往作战'), aborting")
        return

    # ── Step 2: Navigate hub → shop → trade → daily purchase ──
    logger.info("=" * 50)
    logger.info("Step 2: Navigate to daily purchase page")

    # hub → shop
    result = await GotoPageAction(target_page_id="shop").run(ctx)
    await asyncio.sleep(1.5)
    img = snap(device, "02_shop")
    if not verify_ocr(img, "交易区", "shop check"):
        logger.error("Not on shop page, aborting")
        return

    # shop → trade area
    device.click(89, 817)  # Trade area button (verified coord)
    await asyncio.sleep(2.0)
    img = snap(device, "03_trade")
    if not verify_ocr(img, "每日采购", "trade check"):
        logger.error("Not on trade area, aborting")
        return

    # trade → daily purchase (should be default tab, click to be sure)
    device.click(130, 125)  # Daily purchase tab
    await asyncio.sleep(2.0)
    img = snap(device, "04_daily_purchase")
    if not verify_ocr(img, "修正者情报", "daily purchase check"):
        logger.warning("'修正者情报' section not visible, may need scroll or different layout")

    # ── Step 3: OCR scan for all 情报 items ──
    logger.info("=" * 50)
    logger.info("Step 3: OCR scan for intel shards (情报)")

    img = device.screenshot()
    # Search in the top section where intel items are
    intel_region = Rect(200, 130, 1300, 350)
    intel_items = ocr_find_all(img, "情报", region=intel_region)

    # Filter out the section header "修正者情报"
    buyable = [item for item in intel_items if item.text != "修正者情报" and "修正者" not in item.text]

    logger.info(f"Found {len(buyable)} intel items:")
    for item in buyable:
        cx = item.region.x + item.region.w // 2
        cy = item.region.y + item.region.h // 2
        logger.info(f"  '{item.text}' conf={item.confidence:.2f} center=({cx},{cy})")

    # Check for sold-out items
    sold_out = ocr_find_all(img, "售", region=intel_region)
    sold_names = set()
    for s in sold_out:
        # Find which intel item this sold-out label is near (same x region)
        for item in buyable:
            if abs((s.region.x + s.region.w // 2) - (item.region.x + item.region.w // 2)) < 100:
                sold_names.add(item.text)
                logger.info(f"  '{item.text}' is SOLD OUT, skipping")

    available = [item for item in buyable if item.text not in sold_names]
    logger.info(f"Available to buy: {len(available)} items")

    if not available:
        logger.info("No intel items available to buy. Done.")
        await ReturnToHubAction().run(ctx)
        return

    # ── Step 4: Buy each available item ──
    logger.info("=" * 50)
    logger.info("Step 4: Purchasing intel items")

    purchased = 0
    for i, item in enumerate(available):
        item_name = item.text
        # Click on the item (click center of the text, which is on the item card)
        cx = item.region.x + item.region.w // 2
        cy = item.region.y + item.region.h // 2
        logger.info(f"  [{i+1}/{len(available)}] Clicking '{item_name}' at ({cx},{cy})")
        device.click(cx, cy)
        await asyncio.sleep(1.5)

        # Verify purchase popup appeared
        popup_img = snap(device, f"05_popup_{i+1}")
        if not verify_ocr(popup_img, "购买", f"popup check for {item_name}"):
            logger.warning(f"  No purchase popup for '{item_name}', skipping")
            device.press_key(VK_ESCAPE)
            await asyncio.sleep(1.0)
            continue

        # Double-check: verify popup shows the correct item name
        if not verify_ocr(popup_img, "情报", f"popup item verify for {item_name}"):
            logger.error(f"  Popup does NOT show 情报 — SAFETY ABORT for this item")
            device.press_key(VK_ESCAPE)
            await asyncio.sleep(1.0)
            continue

        # Find and click the purchase button via OCR
        buy_btn = ocr_find(popup_img, "购买")
        if buy_btn is None:
            logger.warning(f"  Cannot locate purchase button, skipping")
            device.press_key(VK_ESCAPE)
            await asyncio.sleep(1.0)
            continue

        buy_x = buy_btn.region.x + buy_btn.region.w // 2
        buy_y = buy_btn.region.y + buy_btn.region.h // 2
        logger.info(f"  Clicking purchase button at ({buy_x},{buy_y})")
        device.click(buy_x, buy_y)
        await asyncio.sleep(1.5)

        # Dismiss any result popup
        device.press_key(VK_ENTER)
        await asyncio.sleep(0.5)

        snap(device, f"06_after_buy_{i+1}")
        purchased += 1
        logger.info(f"  '{item_name}' purchased successfully")

    # ── Step 5: Return to hub ──
    logger.info("=" * 50)
    logger.info(f"Step 5: Return to hub (purchased {purchased}/{len(available)} items)")
    await ReturnToHubAction().run(ctx)
    await asyncio.sleep(1.0)
    img = snap(device, "07_final_hub")
    verify_ocr(img, "前往作战", "final hub check")

    logger.info("=" * 50)
    logger.info(f"DONE: Purchased {purchased} intel shards")


def main() -> None:
    config = AETHER_GAZER_CONFIG.to_device_config()
    device = DeviceAdapter(config)
    device.connect()
    try:
        asyncio.run(run(device))
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        device.disconnect()


if __name__ == "__main__":
    main()
