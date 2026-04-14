"""test_buy_shards.py — Integration test: navigate to shop and buy character shards.

Tests the full ops chain against the real game:
1. Wake hub UI (if idle)
2. Return to hub from any page
3. Navigate hub → shop → trade area → trade center → radiance shop
4. Buy first 3 character shard items (row 1)
5. Return to hub

Uses Layer 5 ops directly — this is what a Layer 6 task would do.
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import cv2
import numpy as np
from loguru import logger

from anime_game_afk.core.types import DeviceConfig
from anime_game_afk.core.device import DeviceAdapter
from anime_game_afk.games.aether_gazer.knowledge.keys import (
    VK_ENTER, VK_ESCAPE, key_name,
)
from anime_game_afk.games.aether_gazer.knowledge.constants import (
    SCREEN_CENTER_X, SCREEN_CENTER_Y, BACK_BUTTON_X, BACK_BUTTON_Y,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext, GameState
from anime_game_afk.games.aether_gazer.ops.perception.identify_page import identify
from anime_game_afk.games.aether_gazer.ops.perception.detect_game_state import detect_state
from anime_game_afk.games.aether_gazer.ops.navigate.wake_hub_ui import WakeHubUiAction
from anime_game_afk.games.aether_gazer.ops.navigate.smart_return import ReturnToHubAction
from anime_game_afk.games.aether_gazer.ops.navigate.goto_page import GotoPageAction

from maa.define import MaaWin32InputMethodEnum, MaaWin32ScreencapMethodEnum

# ── Verified coordinates from memory/06-ui-mapping-paradigm.md ──

# Shop sub-navigation (these are inside the shop page, not in knowledge/pages.py yet)
SHOP_TRADE_BTN = (89, 817)        # Trade area button
TRADE_CENTER_TAB = (130, 225)     # Trade center tab (left panel)
RADIANCE_SHOP_TAB = (411, 130)    # Radiance shop subtab (top)

# Radiance shop item grid — row 1 buy buttons
ITEM_BUY_BUTTONS_ROW1 = [
    (439, 466),   # Item 1
    (693, 466),   # Item 2
    (947, 466),   # Item 3
]

# Purchase popup
PURCHASE_CONFIRM_BTN = (1234, 623)  # Orange "purchase" button in popup


def snap(device: DeviceAdapter, label: str) -> np.ndarray:
    """Take screenshot, save thumbnail, return image."""
    img = device.screenshot()
    thumb = cv2.resize(img, (800, 450))
    out = Path(f"assets/aether_gazer/screenshots/buy_shards_{label}.jpg")
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), thumb, [cv2.IMWRITE_JPEG_QUALITY, 85])
    logger.info(f"[snap] {label} saved to {out}")
    return img


async def run_test(device: DeviceAdapter) -> None:
    ctx = OpContext(device=device)

    # ── Step 1: Wake UI + identify current page ──
    logger.info("Step 1: Wake UI and identify current page")
    await WakeHubUiAction().run(ctx)
    await asyncio.sleep(1.0)

    img = snap(device, "01_after_wake")
    page_id, conf = identify(img)
    logger.info(f"Current page: {page_id} (conf={conf:.2f})")

    # ── Step 2: Return to hub ──
    logger.info("Step 2: Return to hub")
    result = await ReturnToHubAction().run(ctx)
    logger.info(f"ReturnToHub result: success={result.success}")
    await asyncio.sleep(1.0)

    img = snap(device, "02_at_hub")
    page_id, conf = identify(img)
    logger.info(f"After return_to_hub: page={page_id} (conf={conf:.2f})")

    # ── Step 3: Navigate to shop ──
    logger.info("Step 3: Navigate hub → shop")
    result = await GotoPageAction(target_page_id="shop").run(ctx)
    logger.info(f"GotoPage(shop) result: success={result.success}")
    await asyncio.sleep(1.5)

    img = snap(device, "03_at_shop")
    page_id, conf = identify(img)
    logger.info(f"After goto shop: page={page_id} (conf={conf:.2f})")

    # ── Step 4: Shop → Trade Area ──
    logger.info("Step 4: Click trade area button")
    device.click(*SHOP_TRADE_BTN)
    await asyncio.sleep(1.5)
    img = snap(device, "04_trade_area")

    # ── Step 5: Trade Area → Trade Center tab ──
    logger.info("Step 5: Click trade center tab")
    device.click(*TRADE_CENTER_TAB)
    await asyncio.sleep(1.5)
    img = snap(device, "05_trade_center")

    # ── Step 6: Trade Center → Radiance Shop subtab ──
    logger.info("Step 6: Click radiance shop subtab")
    device.click(*RADIANCE_SHOP_TAB)
    await asyncio.sleep(1.5)
    img = snap(device, "06_radiance_shop")

    # ── Step 7: Buy items ──
    for i, (bx, by) in enumerate(ITEM_BUY_BUTTONS_ROW1):
        item_num = i + 1
        logger.info(f"Step 7.{item_num}: Click item buy button at ({bx}, {by})")
        device.click(bx, by)
        await asyncio.sleep(1.5)
        img = snap(device, f"07_{item_num}_popup")

        # Click purchase confirm
        logger.info(f"Step 7.{item_num}: Confirm purchase at ({PURCHASE_CONFIRM_BTN[0]}, {PURCHASE_CONFIRM_BTN[1]})")
        device.click(*PURCHASE_CONFIRM_BTN)
        await asyncio.sleep(1.0)

        # Close any result popup with Enter
        device.press_key(VK_ENTER)
        await asyncio.sleep(0.5)

        img = snap(device, f"07_{item_num}_done")
        logger.info(f"Item {item_num} purchase attempt complete")

    # ── Step 8: Return to hub ──
    logger.info("Step 8: Return to hub")
    # Back out: ESC or back button multiple times
    device.click(BACK_BUTTON_X, BACK_BUTTON_Y)
    await asyncio.sleep(1.5)
    device.click(BACK_BUTTON_X, BACK_BUTTON_Y)
    await asyncio.sleep(1.5)

    result = await ReturnToHubAction().run(ctx)
    await asyncio.sleep(1.0)
    img = snap(device, "08_final_hub")
    page_id, conf = identify(img)
    logger.info(f"Final state: page={page_id} (conf={conf:.2f})")

    logger.info("Test complete!")


def main() -> None:
    config = DeviceConfig(
        window_title="AetherGazer",
        screencap_method=MaaWin32ScreencapMethodEnum.FramePool,
        mouse_method=MaaWin32InputMethodEnum.SendMessageWithCursorPos,
        keyboard_method=MaaWin32InputMethodEnum.SendMessageWithCursorPos,
    )

    device = DeviceAdapter(config)
    device.connect()
    logger.info(f"Connected: {device.actual_resolution}")

    try:
        asyncio.run(run_test(device))
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        device.disconnect()


if __name__ == "__main__":
    main()
