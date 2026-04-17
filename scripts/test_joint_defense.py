"""test_joint_defense.py — Explore 联防协议 (Joint Defense) activity sweep.

Path: hub → activity page (below H mail button) → 联防协议 → 挑战
      → 信息集纳 → 震动 → max multiplier → 扫荡 → confirm → return

This is an exploration script. Screenshots + OCR at every step.
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
from anime_game_afk.games.aether_gazer.ops.navigate.smart_return import ReturnToHubAction
from anime_game_afk.games.aether_gazer.ops.navigate.wake_hub_ui import WakeHubUiAction
from anime_game_afk.vision.ocr import ocr_find, ocr_find_all, ocr_full
OUT_DIR = Path("assets/aether_gazer/screenshots/joint_defense")
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


async def run(device: DeviceAdapter) -> None:
    ctx = OpContext(device=device)

    # ── Step 1: Return to hub ──
    logger.info("=" * 60)
    logger.info("Step 1: Return to hub")
    await WakeHubUiAction().run(ctx)
    await asyncio.sleep(1.0)
    result = await ReturnToHubAction().run(ctx)
    if not result.success:
        logger.error("Cannot return to hub")
        return
    await asyncio.sleep(1.0)
    img = snap(device, "hub")

    # ── Step 2: Find mail (H) button and click below it ──
    logger.info("=" * 60)
    logger.info("Step 2: Find H button, click activity entrance below it")

    # Find H label via OCR in the right side of hub
    h_region = Rect(1300, 100, 200, 100)
    h_results = ocr_full(img, region=h_region)
    logger.info(f"  OCR in H region: {len(h_results)} results")
    for r in h_results:
        cx = r.region.x + r.region.w // 2
        cy = r.region.y + r.region.h // 2
        logger.info(f"    '{r.text}' conf={r.confidence:.2f} center=({cx},{cy})")

    # Find "H" specifically
    h_label = None
    for r in h_results:
        if r.text.strip() == "H":
            h_label = r
            break

    if h_label:
        hx = h_label.region.x + h_label.region.w // 2
        hy = h_label.region.y + h_label.region.h // 2
        logger.info(f"  Found H at ({hx},{hy})")
        # Click ~50px below the H label
        click_x = hx
        click_y = hy + 50
    else:
        # Fallback: H shortcut is at approximately (1374, 140) from previous runs
        # Activity entrance ~50px below
        logger.warning("  H not found via OCR, using fallback (1374, 190)")
        click_x = 1374
        click_y = 190

    logger.info(f"  Clicking activity entrance at ({click_x},{click_y})")
    device.click(click_x, click_y)
    await asyncio.sleep(2.0)
    img = snap(device, "activity_page")
    dump_ocr(img, "activity_page")

    # ── Step 3: Find "联防协议" in left column ──
    logger.info("=" * 60)
    logger.info("Step 3: Find '联防协议' in activity list")

    left_column = Rect(0, 100, 400, 700)
    found_jd = ocr_find(img, "联防协议")
    scroll_attempts = 0
    max_scrolls = 5

    # Scroll down to find it
    while found_jd is None and scroll_attempts < max_scrolls:
        logger.info(f"  '联防协议' not found, scrolling down (attempt {scroll_attempts+1})")
        device.swipe(200, 600, 200, 300, duration=300)
        await asyncio.sleep(1.0)
        img = snap(device, f"scroll_down_{scroll_attempts}")
        found_jd = ocr_find(img, "联防协议")
        scroll_attempts += 1

    # If still not found, scroll back up
    if found_jd is None:
        logger.info("  Not found scrolling down, trying scroll up")
        for i in range(max_scrolls):
            device.swipe(200, 300, 200, 600, duration=300)
            await asyncio.sleep(1.0)
            img = snap(device, f"scroll_up_{i}")
            found_jd = ocr_find(img, "联防协议")
            if found_jd:
                break

    if found_jd is None:
        logger.error("  '联防协议' not found after scrolling!")
        dump_ocr(img, "final_search", region=left_column)
        return

    jdx = found_jd.region.x + found_jd.region.w // 2
    jdy = found_jd.region.y + found_jd.region.h // 2
    logger.info(
        f"  Found '联防协议' at ({jdx},{jdy}) conf={found_jd.confidence:.2f}"
    )

    # ── Step 4: Click 联防协议 ──
    logger.info("=" * 60)
    logger.info("Step 4: Click '联防协议'")
    device.click(jdx, jdy)
    await asyncio.sleep(2.0)
    img = snap(device, "joint_defense_panel")
    dump_ocr(img, "joint_defense_panel")

    # Verify: right panel should show "联防协议"
    verify = ocr_find(img, "联防协议")
    if verify:
        logger.info(f"  Verified: '联防协议' visible in right panel")
    else:
        logger.warning("  Could not verify '联防协议' in right panel")

    # ── Step 5: Find and click 挑战 button ──
    logger.info("=" * 60)
    logger.info("Step 5: Find and click challenge button")

    challenge = ocr_find(img, "挑战")
    if challenge is None:
        # Try other common button texts
        challenge = ocr_find(img, "进入")
        if challenge is None:
            challenge = ocr_find(img, "前往")
    if challenge:
        cx = challenge.region.x + challenge.region.w // 2
        cy = challenge.region.y + challenge.region.h // 2
        logger.info(f"  Clicking '{challenge.text}' at ({cx},{cy})")
        device.click(cx, cy)
    else:
        logger.error("  No challenge button found!")
        dump_ocr(img, "no_challenge")
        return

    await asyncio.sleep(2.0)
    img = snap(device, "after_challenge")
    dump_ocr(img, "after_challenge")

    # ── Step 6: Find and click "信息集纳" ──
    logger.info("=" * 60)
    logger.info("Step 6: Find '信息集纳'")

    info_btn = ocr_find(img, "信息集纳")
    if info_btn is None:
        info_btn = ocr_find(img, "集纳")
    if info_btn:
        cx = info_btn.region.x + info_btn.region.w // 2
        cy = info_btn.region.y + info_btn.region.h // 2
        logger.info(f"  Clicking '{info_btn.text}' at ({cx},{cy})")
        device.click(cx, cy)
    else:
        logger.error("  '信息集纳' not found!")
        return

    await asyncio.sleep(2.0)
    img = snap(device, "info_collection")
    dump_ocr(img, "info_collection")

    # ── Step 7: Find and click "震动" ──
    logger.info("=" * 60)
    logger.info("Step 7: Find '震动'")

    quake = ocr_find(img, "震动")
    if quake:
        cx = quake.region.x + quake.region.w // 2
        cy = quake.region.y + quake.region.h // 2
        logger.info(f"  Clicking '{quake.text}' at ({cx},{cy})")
        device.click(cx, cy)
    else:
        logger.error("  '震动' not found!")
        dump_ocr(img, "no_quake")
        return

    await asyncio.sleep(2.0)
    img = snap(device, "battle_panel")
    dump_ocr(img, "battle_panel")

    # ── Step 8: Max multiplier (>>) and sweep ──
    logger.info("=" * 60)
    logger.info("Step 8: Max multiplier and sweep")

    # Find ">>" button for max multiplier
    max_btn = ocr_find(img, ">>")
    if max_btn is None:
        max_btn = ocr_find(img, "»")
    if max_btn:
        cx = max_btn.region.x + max_btn.region.w // 2
        cy = max_btn.region.y + max_btn.region.h // 2
        logger.info(f"  Clicking max multiplier '>>' at ({cx},{cy})")
        device.click(cx, cy)
        await asyncio.sleep(1.0)
    else:
        logger.warning("  '>>' button not found, looking for multiplier area")
        # Try to find multiplier UI elements
        multi = ocr_find_all(img, "倍")
        for m in multi:
            mx = m.region.x + m.region.w // 2
            my = m.region.y + m.region.h // 2
            logger.info(f"    '倍' related: '{m.text}' at ({mx},{my})")

    img = snap(device, "after_max_multi")
    dump_ocr(img, "after_max_multi")

    # Find and click "扫荡" button
    sweep = ocr_find(img, "扫荡")
    if sweep:
        cx = sweep.region.x + sweep.region.w // 2
        cy = sweep.region.y + sweep.region.h // 2
        logger.info(f"  Clicking '扫荡' at ({cx},{cy})")
        device.click(cx, cy)
    else:
        logger.error("  '扫荡' not found!")
        return

    await asyncio.sleep(1.5)
    img = snap(device, "sweep_confirm")
    dump_ocr(img, "sweep_confirm")

    # ── Step 9: Confirm and dismiss ──
    logger.info("=" * 60)
    logger.info("Step 9: Confirm sweep")
    device.press_key(VK_ENTER)
    await asyncio.sleep(2.0)
    img = snap(device, "sweep_animation")

    # Dismiss result
    logger.info("  Dismissing result")
    device.press_key(VK_ENTER)
    await asyncio.sleep(1.5)
    img = snap(device, "sweep_result")
    dump_ocr(img, "sweep_result")

    # ── Step 10: Return to hub ──
    logger.info("=" * 60)
    logger.info("Step 10: Return to hub")
    # Click back button (top-left)
    device.click(35, 35)
    await asyncio.sleep(1.5)
    await ReturnToHubAction().run(ctx)
    await asyncio.sleep(1.0)
    img = snap(device, "final_hub")

    logger.info("DONE: Joint Defense sweep complete")


def main() -> None:
    config = AETHER_GAZER_CONFIG.to_device_config()
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
