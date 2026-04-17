"""integration_test.py — Validate new architecture against real game.

Bottom-up test: L1 (device) → L2 (vision) → L4 (knowledge) → L5 (ops).
Connects to the game window, takes a screenshot, runs page identification
and game state detection, and reports results.

Usage:
    python scripts/integration_test.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import cv2
import numpy as np
from loguru import logger

# ── L1: Device ──
from anime_game_afk.core.device import DeviceAdapter
from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG

# ── L2: Vision ──
from anime_game_afk.vision.matcher import match_template

# ── L4: Knowledge ──
from anime_game_afk.games.aether_gazer.knowledge.constants import (
    MATCH_THRESHOLD,
)
from anime_game_afk.games.aether_gazer.knowledge.resources import (
    STATE_TEMPLATES,
    TEXT_TEMPLATE_DIR,
    TEMPLATE_DIR,
    TEMPLATE_INDEX,
)
from anime_game_afk.games.aether_gazer.knowledge.pages import ALL_PAGES

# ── L5: Perception ──
from anime_game_afk.games.aether_gazer.ops.perception.identify_page import (
    identify,
)
from anime_game_afk.games.aether_gazer.ops.perception.detect_game_state import (
    detect_state,
)


def separator(title: str) -> None:
    logger.info("=" * 60)
    logger.info(f"  {title}")
    logger.info("=" * 60)


def test_layer1_device() -> DeviceAdapter:
    """L1: Connect to game window, take screenshot."""
    separator("L1: Device Adapter")

    config = AETHER_GAZER_CONFIG.to_device_config()

    device = DeviceAdapter(config)

    # Connect
    logger.info("Connecting to game window...")
    device.connect()
    logger.info(f"Connected! actual_resolution={device.actual_resolution}")

    # Screenshot (design resolution)
    img = device.screenshot()
    h, w = img.shape[:2]
    logger.info(f"Screenshot: {w}x{h}")
    assert h <= 720, f"Screenshot height exceeds MAX_HEIGHT: got {h}"
    logger.info("L1 PASS: screenshot at expected resolution")

    # Save for visual inspection
    out_path = Path("assets/aether_gazer/screenshots/integration_test.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), img)
    logger.info(f"Screenshot saved to: {out_path}")

    # Also save a thumbnail for quick viewing
    thumb = cv2.resize(img, (800, 450))
    thumb_path = out_path.with_name("integration_test_thumb.jpg")
    cv2.imwrite(str(thumb_path), thumb, [cv2.IMWRITE_JPEG_QUALITY, 85])
    logger.info(f"Thumbnail saved to: {thumb_path}")

    return device


def test_layer2_vision(img: np.ndarray) -> None:
    """L2: Verify template matching works with real templates."""
    separator("L2: Vision — Template Matching")

    # Check template index exists
    logger.info(f"Template index: {TEMPLATE_INDEX} exists={TEMPLATE_INDEX.exists()}")

    # Check text templates exist
    loaded_count = 0
    for tdef in STATE_TEMPLATES:
        path = TEXT_TEMPLATE_DIR / tdef.filename
        exists = path.exists()
        if exists:
            tpl = cv2.imread(str(path))
            if tpl is not None:
                loaded_count += 1
                logger.info(f"  {tdef.name}: {tdef.filename} ({tpl.shape[1]}x{tpl.shape[0]}) OK")
            else:
                logger.warning(f"  {tdef.name}: {tdef.filename} exists but cv2.imread failed")
        else:
            logger.warning(f"  {tdef.name}: {tdef.filename} NOT FOUND at {path}")

    logger.info(f"State templates loaded: {loaded_count}/{len(STATE_TEMPLATES)}")

    if loaded_count == 0:
        logger.error("L2 FAIL: no templates found — check assets/ paths")
    else:
        logger.info("L2 PASS: templates loadable")


def test_layer4_knowledge() -> None:
    """L4: Verify knowledge data is complete."""
    separator("L4: Knowledge — Pages & Navigation")

    logger.info(f"Total pages defined: {len(ALL_PAGES)}")
    for pid, page in ALL_PAGES.items():
        elem_count = len(page.elements)
        logger.info(f"  {pid} ({page.name_en}): {elem_count} elements, safe={page.safe}")

    from anime_game_afk.games.aether_gazer.knowledge.navigation import NAV_GRAPH
    logger.info(f"Navigation edges: {NAV_GRAPH.edge_count}")
    logger.info("L4 PASS: knowledge loaded")


def test_layer5_perception(img: np.ndarray) -> None:
    """L5: Run identify_page and detect_game_state on real screenshot."""
    separator("L5: Perception — Page ID & Game State")

    # Identify page
    page_id, confidence = identify(img)
    logger.info(f"identify_page: page={page_id}, confidence={confidence:.3f}")
    if page_id != "unknown":
        logger.info(f"L5 PAGE ID PASS: recognized as '{page_id}'")
    else:
        logger.warning(f"L5 PAGE ID: unknown (confidence={confidence:.3f}) — may be normal if on non-mapped screen")

    # Detect game state
    from anime_game_afk.games.aether_gazer.ops.base import GameState
    state, state_conf = detect_state(img)
    logger.info(f"detect_game_state: state={state.value}, confidence={state_conf:.3f}")
    if state != GameState.UNKNOWN:
        logger.info(f"L5 STATE PASS: detected '{state.value}'")
    else:
        logger.info("L5 STATE: unknown — normal if on hub/menu (no battle state template matches)")


def main() -> None:
    logger.info("Integration test starting...")
    logger.info(f"Working directory: {Path.cwd()}")
    start = time.monotonic()

    try:
        # L1: Device
        device = test_layer1_device()
        img = device.screenshot()

        # L2: Vision
        test_layer2_vision(img)

        # L4: Knowledge
        test_layer4_knowledge()

        # L5: Perception
        test_layer5_perception(img)

        elapsed = time.monotonic() - start
        separator(f"ALL TESTS COMPLETE in {elapsed:.1f}s")
        logger.info("Next step: verify the screenshot visually and confirm page/state detection is correct")

        device.disconnect()

    except Exception as e:
        logger.error(f"Integration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
