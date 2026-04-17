"""explore_daily_shop.py — Explore daily shop to find character shards.

READ-ONLY exploration: navigate to daily shop, take screenshots at each step.
No purchasing. Identifies what's available via screenshots for human review.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import cv2
import numpy as np
from loguru import logger

from anime_game_afk.core.device import DeviceAdapter
from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.games.aether_gazer.ops.perception.identify_page import identify
from anime_game_afk.games.aether_gazer.ops.navigate.smart_return import ReturnToHubAction
from anime_game_afk.games.aether_gazer.ops.navigate.goto_page import GotoPageAction
from anime_game_afk.games.aether_gazer.ops.navigate.wake_hub_ui import WakeHubUiAction
OUT_DIR = Path("assets/aether_gazer/screenshots/explore_daily_shop")


def snap(device: DeviceAdapter, label: str) -> np.ndarray:
    img = device.screenshot()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    thumb = cv2.resize(img, (800, 450))
    cv2.imwrite(str(OUT_DIR / f"{label}.jpg"), thumb, [cv2.IMWRITE_JPEG_QUALITY, 90])
    # Also save full res for OCR testing later
    cv2.imwrite(str(OUT_DIR / f"{label}_full.png"), img)
    logger.info(f"[snap] {label}")
    return img


def verify_page(img: np.ndarray, expected: str) -> bool:
    page_id, conf = identify(img)
    ok = page_id == expected
    status = "OK" if ok else "MISMATCH"
    logger.info(f"[verify] expected={expected}, got={page_id} conf={conf:.2f} — {status}")
    return ok


async def explore(device: DeviceAdapter) -> None:
    ctx = OpContext(device=device)

    # Step 1: Wake + Hub
    logger.info("=== Step 1: Wake + Return to Hub ===")
    await WakeHubUiAction().run(ctx)
    await asyncio.sleep(1.0)
    await ReturnToHubAction().run(ctx)
    await asyncio.sleep(1.0)
    img = snap(device, "01_hub")
    verify_page(img, "main_hub")

    # Step 2: Hub → Shop
    logger.info("=== Step 2: Hub → Shop ===")
    await GotoPageAction(target_page_id="shop").run(ctx)
    await asyncio.sleep(1.5)
    img = snap(device, "02_shop")
    verify_page(img, "shop")

    # Step 3: Shop → Trade Area
    logger.info("=== Step 3: Click Trade Area (89, 817) ===")
    device.click(89, 817)
    await asyncio.sleep(2.0)
    img = snap(device, "03_trade_area")

    # Step 4: Trade Area → Daily Purchase tab (should be default or first tab)
    logger.info("=== Step 4: Click Daily Purchase tab (130, 125) ===")
    device.click(130, 125)
    await asyncio.sleep(2.0)
    img = snap(device, "04_daily_purchase")

    # Step 5: Scroll down or check if there are more items
    logger.info("=== Step 5: Take full page screenshot for OCR analysis ===")
    img = snap(device, "05_daily_purchase_full")

    # Step 6: Try scrolling down to see more items
    logger.info("=== Step 6: Scroll down to see more items ===")
    device.swipe(800, 600, 800, 300, duration=500)
    await asyncio.sleep(1.5)
    img = snap(device, "06_daily_purchase_scrolled")

    # Step 7: Back to hub (read-only, no purchases)
    logger.info("=== Step 7: Return to Hub ===")
    await ReturnToHubAction().run(ctx)
    await asyncio.sleep(1.0)
    img = snap(device, "07_back_to_hub")
    verify_page(img, "main_hub")

    logger.info("=== Exploration complete. Review screenshots in: {} ===".format(OUT_DIR))


def main() -> None:
    config = AETHER_GAZER_CONFIG.to_device_config()
    device = DeviceAdapter(config)
    device.connect()
    try:
        asyncio.run(explore(device))
    finally:
        device.disconnect()


if __name__ == "__main__":
    main()
