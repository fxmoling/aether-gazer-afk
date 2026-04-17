"""ch6_battle.py — 第六章自动战斗 (模板匹配版)

使用cv2.matchTemplate检测游戏状态，每一步详尽log。
从关卡地图的"准备作战"开始，自动处理战斗全流程。

用法:
    python scripts/ch6_battle.py
    python scripts/ch6_battle.py --max-time 600  # 最多运行10分钟
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
from anime_game_afk.core.device import DeviceAdapter

# Design resolution for pixel→fractional coordinate conversion
_DESIGN_W, _DESIGN_H = 1600, 900

# ============================================================
# Logging setup
# ============================================================
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("ch6_battle.log", encoding="utf-8", mode="w"),
    ],
)
log = logging.getLogger("ch6")

# ============================================================
# Paths
# ============================================================
TEMPLATE_DIR = Path("assets/aether_gazer/templates/text")
SNAP_DIR = Path("assets/aether_gazer/screenshots/deep/thumb")
SNAP_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# Template definitions
# ============================================================
@dataclass
class TextTemplate:
    name: str           # human-readable name
    file: str           # template file name in TEMPLATE_DIR
    search_region: tuple[int,int,int,int] | None  # (x1,y1,x2,y2) to limit search, None=full
    threshold: float    # match threshold
    scale: float        # 1.0 for 1600x900 templates, 0.5 for 800x450

TEMPLATES = [
    # Priority order matters! Check most critical first.
    TextTemplate("mission_failed",     "txt_mission_failed.png",     (400,50,1200,250),    0.60, 1.0),
    TextTemplate("revive_prompt",      "txt_revive_800.png",         None,                 0.70, 0.5),  # 800x450 template, raised threshold
    TextTemplate("skip_story_confirm", "txt_skip_story.png",         (500,200,1100,350),   0.70, 1.0),
    TextTemplate("continuous_battle",  "txt_continuous_battle.png",   (400,220,1200,360),   0.70, 1.0),
    TextTemplate("prep_battle",        "txt_prep_battle.png",        (1000,780,1600,900),  0.70, 1.0),
    TextTemplate("battle_hud",         "txt_pause.png",              (0,830,200,900),      0.65, 1.0),
    TextTemplate("stage_map",          "txt_progress.png",           (0,820,300,900),      0.60, 1.0),
]

# ============================================================
# State detection
# ============================================================
class StateDetector:
    def __init__(self):
        self.templates: dict[str, tuple[TextTemplate, np.ndarray]] = {}
        for t in TEMPLATES:
            path = TEMPLATE_DIR / t.file
            img = cv2.imread(str(path))
            if img is None:
                log.warning("Template not found: %s", path)
                continue
            self.templates[t.name] = (t, img)
            log.info("Loaded template: %s (%dx%d, threshold=%.2f)",
                     t.name, img.shape[1], img.shape[0], t.threshold)

    def detect(self, screenshot: np.ndarray) -> tuple[str, float]:
        """Detect game state from screenshot (1600x900).
        Returns (state_name, confidence). state_name='unknown' if nothing matched."""

        # Also make a half-size version for 800x450 templates
        half = cv2.resize(screenshot, (800, 450), interpolation=cv2.INTER_AREA)

        best_state = "unknown"
        best_conf = 0.0
        all_results = []

        for name, (tmpl, tmpl_img) in self.templates.items():
            # Choose image based on template scale
            if tmpl.scale == 0.5:
                img = half
            else:
                img = screenshot

            # Crop search region if specified
            if tmpl.search_region:
                x1, y1, x2, y2 = tmpl.search_region
                if tmpl.scale == 0.5:
                    x1, y1, x2, y2 = x1//2, y1//2, x2//2, y2//2
                roi = img[y1:y2, x1:x2]
            else:
                roi = img

            # Check ROI is large enough for template
            th, tw = tmpl_img.shape[:2]
            rh, rw = roi.shape[:2]
            if tw > rw or th > rh:
                continue

            # Match
            result = cv2.matchTemplate(roi, tmpl_img, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            all_results.append((name, max_val, tmpl.threshold))

            if max_val >= tmpl.threshold and max_val > best_conf:
                best_conf = max_val
                best_state = name

        # Log all match results for debugging
        results_str = " | ".join(f"{n}:{v:.2f}{'*' if v>=t else ''}" for n, v, t in all_results)
        log.debug("Match results: %s", results_str)

        # Check for black screen (loading) -- only reliable non-template check
        if best_state == "unknown" and np.mean(screenshot) < 15:
            best_state = "loading"
            best_conf = 0.99

        # NO brightness-based fallback for cutscene/dialogue!
        # Unknown state will be handled by the main loop with Space presses.

        return best_state, best_conf

# ============================================================
# Actions
# ============================================================
BATTLE_KEYS = [0x4A, 0x4A, 0x55, 0x4A, 0x49, 0x4A, 0x4F, 0x52, 0x31, 0x32]
KEY_NAMES = {0x4A:"J", 0x55:"U", 0x49:"I", 0x4F:"O", 0x52:"R", 0x31:"1", 0x32:"2",
             0x1B:"ESC", 0x0D:"Enter", 0x20:"Space", 0x57:"W"}

def press(device: DeviceAdapter, key: int, reason: str):
    name = KEY_NAMES.get(key, f"0x{key:02X}")
    log.info("ACTION: press [%s] -- %s", name, reason)
    device.press_key(key)

def click(device: DeviceAdapter, x: int, y: int, reason: str):
    fx, fy = x / _DESIGN_W, y / _DESIGN_H
    log.info("ACTION: click (%d, %d) [%.3f, %.3f] -- %s", x, y, fx, fy, reason)
    device.click(fx, fy)

def save_snap(device: DeviceAdapter, label: str) -> np.ndarray:
    img = device.screenshot()
    thumb = cv2.resize(img, (800, 450), interpolation=cv2.INTER_AREA)
    path = SNAP_DIR / f"ch6b_{label}.jpg"
    cv2.imwrite(str(path), thumb, [cv2.IMWRITE_JPEG_QUALITY, 65])
    log.debug("Snapshot saved: %s", path.name)
    return img

# ============================================================
# Main loop
# ============================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-time", type=int, default=600, help="Max runtime in seconds")
    parser.add_argument("--skip-prep", action="store_true", help="Skip initial prep battle click")
    args = parser.parse_args()

    device = DeviceAdapter(AETHER_GAZER_CONFIG.to_device_config())
    device.connect()
    detector = StateDetector()

    try:
        log.info("========================================")
        log.info("Chapter 6 Battle Script Start")
        log.info("Max time: %ds", args.max_time)
        log.info("========================================")

        # Step 0: Click node then prep battle if needed
        if not args.skip_prep:
            log.info("STEP 0a: Clicking stage node 6-10 (1200, 310)")
            click(device, 1200, 310, "Click stage 6-10 node to open detail panel")
            time.sleep(3)
            log.info("STEP 0b: Clicking prep battle button (1350, 840)")
            click(device, 1350, 840, "Click prep battle button on detail panel")
            time.sleep(4)
            img = save_snap(device, "s0_after_prep")
            state, conf = detector.detect(img)
            log.info("STEP 0 result: state=%s conf=%.2f", state, conf)

        # Main state machine loop
        start_time = time.time()
        step = 0
        battle_key_idx = 0
        same_state_count = 0
        last_state = ""

        while time.time() - start_time < args.max_time:
            step += 1
            elapsed = int(time.time() - start_time)

            # Screenshot and detect
            img = device.screenshot()
            state, conf = detector.detect(img)

            # Track same-state count
            if state == last_state:
                same_state_count += 1
            else:
                if last_state:
                    log.info("STATE CHANGE: %s -> %s (was %s for %d steps)",
                             last_state, state, last_state, same_state_count)
                same_state_count = 0
                last_state = state

            # Periodic status log
            if step % 20 == 0:
                log.info("[%ds step=%d] state=%s conf=%.2f same_count=%d",
                         elapsed, step, state, conf, same_state_count)
                save_snap(device, f"periodic_{elapsed}s")

            # Stuck detection
            if same_state_count > 100:
                log.warning("STUCK: state=%s for %d steps. Saving snap and trying recovery.",
                           state, same_state_count)
                save_snap(device, f"stuck_{elapsed}s_{state}")
                # Generic recovery: try ESC
                press(device, 0x1B, "Stuck recovery: try ESC")
                time.sleep(2)
                same_state_count = 0
                continue

            # ========== State handlers ==========

            if state == "loading":
                # Black screen, just wait
                if same_state_count % 10 == 0:
                    log.debug("[%ds] Loading... (waiting)", elapsed)
                time.sleep(0.5)

            elif state == "mission_failed":
                log.info("PAGE: Mission Failed screen detected")
                save_snap(device, f"mission_failed_{elapsed}s")
                press(device, 0x1B, "Close mission failed screen")
                time.sleep(3)

            elif state == "revive_prompt":
                log.info("PAGE: Revive prompt detected -- accepting revival")
                save_snap(device, f"revive_{elapsed}s")
                press(device, 0x0D, "Accept revival (Enter) -- cost acceptable")
                time.sleep(3)

            elif state == "skip_story_confirm":
                log.info("PAGE: Skip story confirmation dialog")
                press(device, 0x0D, "Confirm skip story (Enter)")
                time.sleep(3)

            elif state == "continuous_battle":
                log.info("PAGE: Continuous battle prompt")
                save_snap(device, f"continuous_{elapsed}s")
                press(device, 0x0D, "Accept continuous battle (Enter)")
                time.sleep(4)

            elif state == "prep_battle":
                log.info("PAGE: Stage map with prep battle button visible")
                # This might appear after battle completion or at start
                # If we just completed a battle, this means we're done
                if step > 5:
                    log.info("Prep battle detected after battle -- may be complete or next stage")
                    save_snap(device, f"prep_again_{elapsed}s")
                click(device, 1350, 840, "Click prep battle to start next stage")
                time.sleep(4)

            elif state == "battle_hud":
                # In battle -- press attack keys
                if same_state_count % 30 == 0:
                    log.info("[%ds] IN BATTLE: pressing attack keys (round %d)",
                             elapsed, same_state_count // 10)
                key = BATTLE_KEYS[battle_key_idx % len(BATTLE_KEYS)]
                press_name = KEY_NAMES.get(key, "?")
                if same_state_count % 10 == 0:  # Log every 10th key to avoid spam
                    log.debug("Battle key: %s (idx=%d)", press_name, battle_key_idx)
                device.press_key(key)  # Direct press without full log to reduce noise
                battle_key_idx += 1
                time.sleep(0.25)

            elif state == "stage_map":
                log.info("PAGE: Stage map (progress indicator visible)")
                save_snap(device, f"stage_map_{elapsed}s")
                if step <= 5:
                    # Initial entry: click the node first, then prep
                    log.info("Clicking stage node 6-10 area (1200, 310)")
                    click(device, 1200, 310, "Click stage 6-10 node to open detail panel")
                    time.sleep(3)
                    log.info("Now clicking prep battle (1350, 840)")
                    click(device, 1350, 840, "Click prep battle button")
                    time.sleep(4)
                elif step > 10:
                    log.info("Back at stage map after %d steps -- trying to re-enter battle", step)
                    # Scroll right to find next uncompleted node, click it
                    log.info("Swiping right to find next uncompleted node")
                    device.swipe(400 / _DESIGN_W, 450 / _DESIGN_H, 1200 / _DESIGN_W, 450 / _DESIGN_H)
                    time.sleep(2)
                    # Click rightmost visible node area
                    click(device, 1200, 350, "Click a node on the map")
                    time.sleep(3)
                    click(device, 1350, 840, "Click prep battle button")
                    time.sleep(4)

            elif state == "unknown":
                # Unknown state: use a rotating strategy
                # Space is safe for: dialogue advance, result screen, item display
                # W is safe for: exploration movement
                # ESC+Enter is safe for: skippable cutscenes
                cycle = same_state_count % 30

                if cycle < 5:
                    # First: try Space (dialogue/results)
                    if same_state_count % 3 == 0:
                        log.info("[%ds] Unknown state (cycle %d): pressing Space", elapsed, same_state_count)
                    press(device, 0x20, "Unknown: Space (dialogue/result/advance)")
                    time.sleep(0.4)

                elif cycle < 10:
                    # Then: try attack keys (might be in battle without HUD detected)
                    key = BATTLE_KEYS[battle_key_idx % len(BATTLE_KEYS)]
                    if same_state_count % 5 == 0:
                        log.info("[%ds] Unknown state (cycle %d): trying battle keys", elapsed, same_state_count)
                    device.press_key(key)
                    battle_key_idx += 1
                    time.sleep(0.25)

                elif cycle < 20:
                    # Then: try walking forward (exploration)
                    if same_state_count % 10 == 0:
                        log.info("[%ds] Unknown state (cycle %d): walking W", elapsed, same_state_count)
                    device.press_key(0x57)  # W
                    time.sleep(0.2)

                elif cycle < 25:
                    # Then: try ESC+Enter combo (skippable cutscene)
                    if cycle == 20:
                        log.info("[%ds] Unknown state (cycle %d): trying ESC->Enter skip", elapsed, same_state_count)
                        press(device, 0x1B, "Unknown: ESC (try cutscene skip)")
                        time.sleep(1.5)
                        press(device, 0x0D, "Unknown: Enter (confirm skip if dialog appeared)")
                        time.sleep(2)
                    else:
                        time.sleep(0.3)

                else:
                    # Brief pause before cycling again
                    time.sleep(0.3)

            else:
                log.warning("Unhandled state: %s", state)
                time.sleep(0.5)

        log.info("========================================")
        log.info("TIME LIMIT REACHED (%ds)", args.max_time)
        log.info("Total steps: %d, battle keys: %d", step, battle_key_idx)
        log.info("========================================")

    finally:
        save_snap(device, "final")
        device.disconnect()
        log.info("Disconnected. Log saved to ch6_battle.log")


if __name__ == "__main__":
    main()
