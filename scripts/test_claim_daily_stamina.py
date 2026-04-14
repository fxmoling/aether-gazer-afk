"""test_claim_daily_stamina.py — Explore and claim daily stamina packs.

Path: hub → click stamina display (top-right) → stamina panel → 每日补给 tab
      → click 吨吨值福利包 items (up to 2).

This is an exploration/test script. Screenshots saved at every step
for coordinate verification.
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
from anime_game_afk.games.aether_gazer.ops.navigate.wake_hub_ui import WakeHubUiAction
from anime_game_afk.vision.ocr import ocr_find, ocr_find_all, ocr_full
from maa.define import MaaWin32InputMethodEnum, MaaWin32ScreencapMethodEnum

OUT_DIR = Path("assets/aether_gazer/screenshots/claim_daily_stamina")
snap_counter = 0


def snap(device: DeviceAdapter, label: str) -> np.ndarray:
    """Screenshot + save thumbnail + return full image."""
    global snap_counter
    snap_counter += 1
    img = device.screenshot()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    thumb = cv2.resize(img, (800, 450))
    filename = f"{snap_counter:03d}_{label}.jpg"
    cv2.imwrite(str(OUT_DIR / filename), thumb, [cv2.IMWRITE_JPEG_QUALITY, 90])
    logger.info(f"[snap] #{snap_counter} {label}")
    return img


def dump_ocr(img: np.ndarray, label: str) -> None:
    """Run full OCR and log all detected text with positions."""
    results = ocr_full(img)
    logger.info(f"[OCR dump: {label}] Found {len(results)} text regions:")
    for r in sorted(results, key=lambda r: (r.region.y, r.region.x)):
        cx = r.region.x + r.region.w // 2
        cy = r.region.y + r.region.h // 2
        logger.info(
            f"  '{r.text}' conf={r.confidence:.2f} "
            f"at ({r.region.x},{r.region.y}) size=({r.region.w}x{r.region.h}) "
            f"center=({cx},{cy})"
        )


async def run(device: DeviceAdapter) -> None:
    ctx = OpContext(device=device)

    # ── Step 1: Return to hub ──
    logger.info("=" * 60)
    logger.info("Step 1: Wake UI + Return to hub")
    await WakeHubUiAction().run(ctx)
    await asyncio.sleep(1.0)
    result = await ReturnToHubAction().run(ctx)
    if not result.success:
        logger.error("Cannot return to hub, aborting")
        return
    await asyncio.sleep(1.0)
    img = snap(device, "hub")
    dump_ocr(img, "hub")

    # ── Step 2: Find and click stamina display (top-right area) ──
    logger.info("=" * 60)
    logger.info("Step 2: Look for stamina display in top-right")

    # The stamina/体力 display is usually in the top-right area of hub
    # Let's OCR the top-right region to find it
    top_right_region = Rect(1100, 0, 500, 100)
    top_right_results = ocr_find_all(img, "体力", region=top_right_region)
    logger.info(f"  Found '体力' in top-right: {len(top_right_results)} matches")
    for r in top_right_results:
        cx = r.region.x + r.region.w // 2
        cy = r.region.y + r.region.h // 2
        logger.info(f"    '{r.text}' at center=({cx},{cy})")

    # Also search for numbers that look like stamina (e.g. "120/200")
    # The stamina icon is typically a lightning bolt or similar icon
    # Let's try clicking the stamina area — usually around top-right
    # We'll use OCR to find the exact position

    # If we can't find "体力" text, try broader search for stamina-like numbers
    if not top_right_results:
        logger.info("  '体力' not found, trying broader OCR of top area")
        top_area = Rect(800, 0, 800, 80)
        results = ocr_full(img, region=top_area)
        for r in results:
            cx = r.region.x + r.region.w // 2
            cy = r.region.y + r.region.h // 2
            logger.info(
                f"  top-area: '{r.text}' conf={r.confidence:.2f} center=({cx},{cy})"
            )

    # Try clicking the stamina area
    # Stamina "173/240" is the leftmost resource in the top bar
    # From OCR: center=(907,44). Click on the number, NOT the "+" button.
    # The "+" buttons open currency exchange dialogs, not the stamina panel.
    # Look for the "NNN/NNN" pattern which is the stamina display
    import re
    top_area = Rect(800, 0, 800, 80)
    all_top = ocr_full(img, region=top_area)
    stamina_match = None
    for r in all_top:
        if re.match(r"\d+/\d+", r.text.replace(" ", "")):
            stamina_match = r
            logger.info(f"  Found stamina display: '{r.text}' at center="
                        f"({r.region.x + r.region.w // 2},{r.region.y + r.region.h // 2})")
            break

    if stamina_match:
        # Click slightly LEFT of the text center to hit the stamina icon/number,
        # not the "+" button that may be concatenated with the OCR text
        click_x = stamina_match.region.x  # Left edge of the text
        click_y = stamina_match.region.y + stamina_match.region.h // 2
        logger.info(f"  Clicking stamina LEFT edge at ({click_x},{click_y})")
    elif top_right_results:
        target = top_right_results[0]
        click_x = target.region.x + target.region.w // 2
        click_y = target.region.y + target.region.h // 2
        logger.info(f"  Clicking stamina text at ({click_x},{click_y})")
    else:
        # Fallback: stamina display is at ~(870, 35) based on screenshot analysis
        click_x, click_y = 870, 35
        logger.info(f"  Using fallback position ({click_x},{click_y})")

    device.click(click_x, click_y)
    await asyncio.sleep(2.0)
    img = snap(device, "after_stamina_click")
    dump_ocr(img, "after_stamina_click")

    # ── Step 3: Look for the stamina panel ──
    logger.info("=" * 60)
    logger.info("Step 3: Check stamina panel")

    # Look for tab labels: 冷却剂, 移转之辉, 每日补给
    coolant = ocr_find(img, "冷却剂")
    transfer = ocr_find(img, "移转之辉")
    daily = ocr_find(img, "每日补给")

    if coolant:
        cx = coolant.region.x + coolant.region.w // 2
        cy = coolant.region.y + coolant.region.h // 2
        logger.info(f"  Found '冷却剂' tab at ({cx},{cy})")
    if transfer:
        cx = transfer.region.x + transfer.region.w // 2
        cy = transfer.region.y + transfer.region.h // 2
        logger.info(f"  Found '移转之辉' tab at ({cx},{cy})")
    if daily:
        cx = daily.region.x + daily.region.w // 2
        cy = daily.region.y + daily.region.h // 2
        logger.info(f"  Found '每日补给' tab at ({cx},{cy})")

    if not (coolant or transfer or daily):
        logger.warning("  No stamina panel tabs found! May need different approach")
        logger.info("  Let's try clicking in a different position")
        # Try escaping and re-approaching
        device.press_key(VK_ESCAPE)
        await asyncio.sleep(1.0)
        img = snap(device, "after_escape")
        dump_ocr(img, "after_escape")
        # Return early — we'll need to figure out the right click target
        return

    # ── Step 4: Click "每日补给" tab ──
    logger.info("=" * 60)
    logger.info("Step 4: Click '每日补给' tab")

    if daily:
        dx = daily.region.x + daily.region.w // 2
        dy = daily.region.y + daily.region.h // 2
        logger.info(f"  Clicking '每日补给' at ({dx},{dy})")
        device.click(dx, dy)
    else:
        logger.warning("  '每日补给' tab not found, trying rightmost tab position")
        # If we found coolant at left, daily should be to the right
        if coolant:
            base_x = coolant.region.x + coolant.region.w // 2
            # Tabs are usually evenly spaced
            device.click(base_x + 400, coolant.region.y + coolant.region.h // 2)
        else:
            logger.error("  Cannot locate any tab, aborting")
            return

    await asyncio.sleep(2.0)
    img = snap(device, "daily_supply_tab")
    dump_ocr(img, "daily_supply_tab")

    # ── Step 5: Find 吨吨值福利包 items ──
    logger.info("=" * 60)
    logger.info("Step 5: Look for 吨吨值福利包 items")

    # Search for "吨吨" or "福利" text
    tonton_items = ocr_find_all(img, "吨吨")
    logger.info(f"  Found '吨吨' items: {len(tonton_items)}")
    for r in tonton_items:
        cx = r.region.x + r.region.w // 2
        cy = r.region.y + r.region.h // 2
        logger.info(
            f"    '{r.text}' conf={r.confidence:.2f} center=({cx},{cy})"
        )

    fuli_items = ocr_find_all(img, "福利")
    logger.info(f"  Found '福利' items: {len(fuli_items)}")
    for r in fuli_items:
        cx = r.region.x + r.region.w // 2
        cy = r.region.y + r.region.h // 2
        logger.info(
            f"    '{r.text}' conf={r.confidence:.2f} center=({cx},{cy})"
        )

    # Also look for "领取" (claim) buttons
    claim_btns = ocr_find_all(img, "领取")
    logger.info(f"  Found '领取' buttons: {len(claim_btns)}")
    for r in claim_btns:
        cx = r.region.x + r.region.w // 2
        cy = r.region.y + r.region.h // 2
        logger.info(
            f"    '{r.text}' conf={r.confidence:.2f} center=({cx},{cy})"
        )

    # Also look for "免费" (free) text
    free_items = ocr_find_all(img, "免费")
    logger.info(f"  Found '免费' items: {len(free_items)}")
    for r in free_items:
        cx = r.region.x + r.region.w // 2
        cy = r.region.y + r.region.h // 2
        logger.info(
            f"    '{r.text}' conf={r.confidence:.2f} center=({cx},{cy})"
        )

    # ── Step 6: Try clicking the first claimable item ──
    logger.info("=" * 60)
    logger.info("Step 6: Try claiming items")

    # Strategy: click each "吨吨" item or "领取" button
    claimed = 0
    targets = tonton_items if tonton_items else fuli_items

    for i, item in enumerate(targets[:2]):  # Max 2 items
        cx = item.region.x + item.region.w // 2
        cy = item.region.y + item.region.h // 2
        logger.info(f"  [{i+1}] Clicking '{item.text}' at ({cx},{cy})")
        device.click(cx, cy)
        await asyncio.sleep(1.5)

        # Check for popup
        popup_img = snap(device, f"claim_popup_{i}")
        dump_ocr(popup_img, f"claim_popup_{i}")

        # Look for confirm/claim button
        confirm = ocr_find(popup_img, "领取")
        if confirm is None:
            confirm = ocr_find(popup_img, "确认")
        if confirm is None:
            confirm = ocr_find(popup_img, "购买")

        if confirm:
            bx = confirm.region.x + confirm.region.w // 2
            by = confirm.region.y + confirm.region.h // 2
            logger.info(f"  [{i+1}] Clicking confirm '{confirm.text}' at ({bx},{by})")
            device.click(bx, by)
            await asyncio.sleep(1.5)
        else:
            logger.info(f"  [{i+1}] No confirm button, trying Enter key")
            device.press_key(VK_ENTER)
            await asyncio.sleep(1.0)

        # Dismiss result
        device.press_key(VK_ENTER)
        await asyncio.sleep(1.0)

        after_img = snap(device, f"after_claim_{i}")
        claimed += 1
        logger.info(f"  [{i+1}] Claimed (total: {claimed})")

    # ── Step 7: Close and return ──
    logger.info("=" * 60)
    logger.info(f"Step 7: Close stamina panel and return (claimed {claimed})")
    device.press_key(VK_ESCAPE)
    await asyncio.sleep(1.0)
    img = snap(device, "after_close_panel")

    await ReturnToHubAction().run(ctx)
    await asyncio.sleep(1.0)
    img = snap(device, "final_hub")

    logger.info(f"DONE: Claimed {claimed} daily stamina packs")


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
