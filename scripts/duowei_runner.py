"""多维变量 (Multidimensional Variable) — autonomous roguelike runner.

Standalone script that runs the full 多维变量 loop:
  1. Navigate from hub to 多维变量 entry
  2. Select difficulty, characters, beacons
  3. Loop: walk to portal → fight → pick treasure → next floor
  4. On death/timeout → exit and collect score rewards

Usage:
    python scripts/duowei_runner.py              # Full run from hub
    python scripts/duowei_runner.py --resume     # Resume mid-run (already in arena)
    python scripts/duowei_runner.py --max-floors 5  # Stop after N floors

Requires: game running, at main hub (or --resume if already in 多维变量)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
from anime_game_afk.core.device import DeviceAdapter
from anime_game_afk.vision.ocr import ocr_once

# ── Key codes ──
VK_J, VK_U, VK_I, VK_O, VK_R = 0x4A, 0x55, 0x49, 0x4F, 0x52
VK_1, VK_2 = 0x31, 0x32
VK_W, VK_A, VK_S, VK_D = 0x57, 0x41, 0x53, 0x44
VK_SPACE, VK_ENTER, VK_ESC = 0x20, 0x0D, 0x1B
VK_TAB = 0x09
VK_H = 0x48
VK_F = 0x46
VK_Q, VK_E = 0x51, 0x45

ATTACK_KEYS = [VK_J, VK_J, VK_U, VK_J, VK_I, VK_J, VK_O, VK_R, VK_1, VK_2]

# ── Portal button template for fast detection ──
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "assets" / "templates"
PORTAL_BTN_TEMPLATE = cv2.imread(str(_TEMPLATE_DIR / "portal_button.png"))
PORTAL_BTN_THRESHOLD = 0.55  # Lower threshold since arena lighting varies

# ── Output directory ──
OUT_DIR = Path(".tmp/duowei_run")
OUT_DIR.mkdir(parents=True, exist_ok=True)


class DuoweiRunner:
    """Autonomous 多维变量 roguelike runner."""

    def __init__(self, device: DeviceAdapter, max_floors: int = 20):
        self.device = device
        self.max_floors = max_floors
        self.floor = 0
        self.screenshot_idx = 0

    # ── Helpers ──

    def log(self, msg: str) -> None:
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] {msg}")

    def snap(self, label: str = "screen"):
        """Take screenshot, save to .tmp, return (ocr_text, img)."""
        img = self.device.screenshot()
        self.screenshot_idx += 1
        path = OUT_DIR / f"{self.screenshot_idx:03d}_{label}.jpg"
        cv2.imwrite(str(path), img, [cv2.IMWRITE_JPEG_QUALITY, 70])
        return img

    def ocr_screen(self):
        """Take screenshot + OCR, return (full_text, ocr_result, img)."""
        img = self.snap("ocr")
        ocr = ocr_once(img)
        texts = [r.text for r in ocr._items]
        full = " ".join(texts)
        return full, ocr, img

    def press(self, vk: int, wait: float = 0.15):
        self.device.press_key(vk)
        time.sleep(wait)

    def click_frac(self, fx: float, fy: float, wait: float = 1.0):
        self.device.click(fx, fy)
        time.sleep(wait)

    def click_px(self, x: int, y: int, wait: float = 1.0):
        """Click pixel coords in 1280x720 space."""
        self.device.click(x / 1280, y / 720)
        time.sleep(wait)

    def hold(self, vk: int, duration: float):
        self.device.hold_key(vk, duration)

    def attack_cycle(self, n: int = 1):
        """Run n full attack rotations: J J U J I J O R 1 2."""
        for _ in range(n):
            for vk in ATTACK_KEYS:
                self.press(vk, 0.12)
            time.sleep(0.2)

    def dismiss_dialog(self) -> bool:
        """Try to dismiss any generic dialog (reward, confirmation, etc).

        Returns True if a dialog was found and dismissed.
        """
        full, ocr, _ = self.ocr_screen()

        # Generic 确认 button (reward popups, notifications)
        if "确认" in full and "击退" not in full and "珍宝选择" not in full:
            pos = self.find_ocr_center(ocr, "确认")
            if pos:
                self.log(f"  Dismissing dialog: clicking 确认 at {pos}")
                self.click_px(pos[0], pos[1], 2.0)
                return True
            # Fallback: press Enter
            self.press(VK_ENTER, 1.0)
            return True

        return False

    def find_ocr_center(self, ocr, target: str):
        """Find OCR text and return its (px_x, px_y) center in 1280x720."""
        match = ocr.find(target)
        if match:
            r = match.region
            return (r.x + r.w // 2, r.y + r.h // 2)
        return None

    # ── Navigation: Hub → 多维变量 ──

    def navigate_to_duowei(self) -> bool:
        """From hub, navigate to 多维变量 entry and click 开始挑战."""
        self.log("Navigating: Hub → 挑战 tab")

        # Click 挑战 tab (bottom-right of hub)
        # First check if we're at hub by looking for common hub elements
        full, ocr, _ = self.ocr_screen()
        if "挑战" not in full and "多维" not in full:
            self.log("Not at hub or challenge page, pressing ESC first")
            self.press(VK_ESC, 1.0)
            self.press(VK_ESC, 1.0)
            time.sleep(1.0)

        # Click 挑战 tab at bottom nav
        self.click_frac(0.95, 0.92, 2.0)  # 挑战 tab

        # Look for 多维变量 node on challenge page
        full, ocr, _ = self.ocr_screen()
        pos = self.find_ocr_center(ocr, "多维变量")
        if pos:
            self.log(f"Found 多维变量 at ({pos[0]}, {pos[1]})")
            self.click_px(pos[0], pos[1], 2.0)
        else:
            self.log("Cannot find 多维变量 on challenge page")
            return False

        # Now on 多维变量 main page, click 开始挑战
        full, ocr, _ = self.ocr_screen()
        pos = self.find_ocr_center(ocr, "开始挑战")
        if pos:
            self.log(f"Clicking 开始挑战 at ({pos[0]}, {pos[1]})")
            self.click_px(pos[0], pos[1], 2.0)
        else:
            self.log("Cannot find 开始挑战")
            return False

        return True

    def complete_setup_wizard(self) -> bool:
        """Go through difficulty → character → beacon → start."""
        # Step 1: Difficulty selection → 下一步
        self.log("Setup: Difficulty selection")
        full, ocr, _ = self.ocr_screen()
        if "难度选择" in full or "难度" in full:
            pos = self.find_ocr_center(ocr, "下一步")
            if pos:
                self.click_px(pos[0], pos[1], 2.0)

        # Step 2: Character selection → 下一步
        self.log("Setup: Character selection")
        full, ocr, _ = self.ocr_screen()
        if "修正者选择" in full or "修正者" in full:
            pos = self.find_ocr_center(ocr, "下一步")
            if pos:
                self.click_px(pos[0], pos[1], 2.0)

        # Step 3: Beacon selection → 开始挑战
        self.log("Setup: Beacon selection")
        full, ocr, _ = self.ocr_screen()
        if "信标选择" in full or "信标" in full:
            pos = self.find_ocr_center(ocr, "开始挑战")
            if pos:
                self.click_px(pos[0], pos[1], 5.0)

        # Wait for loading
        self.log("Waiting for arena to load...")
        time.sleep(8.0)
        return True

    # ── Arena navigation ──

    def detect_portal_button(self) -> bool:
        """Fast portal button detection using template matching (~10ms).

        Checks for the "≪ 前往..." button that appears when near a portal.
        Much faster than OCR (~2000ms).
        """
        if PORTAL_BTN_TEMPLATE is None:
            return False
        img = self.device.screenshot()
        # Only search in the region where the button appears (center-right, y 350-550)
        roi = img[350:550, 600:1050]
        result = cv2.matchTemplate(roi, PORTAL_BTN_TEMPLATE, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        return max_val > PORTAL_BTN_THRESHOLD

    def walk_to_portal(self) -> bool:
        """Walk to find and enter a battle portal.

        Strategy: rotate camera with Q/E to scan for portals,
        walk W (forward) toward them, detect the interaction button
        via fast template matching. All done via MaaFramework (background).
        """
        self.log("Walking to portal...")

        # Try 6 camera angles (rotate Q ~60° each time), walk W each angle
        for angle_idx in range(6):
            if angle_idx > 0:
                self.log(f"  Rotating camera (angle {angle_idx}/6)...")
                self.hold(VK_Q, 1.5)  # ~60° rotation
                time.sleep(0.3)

            # Walk W toward whatever is ahead
            self.log(f"  Walk forward (angle {angle_idx})...")
            for step in range(20):
                self.hold(VK_W, 0.5)
                time.sleep(0.05)

                # Fast template check every 2 steps
                if step % 2 == 1:
                    if self.detect_portal_button():
                        self.log(f"  PORTAL BUTTON at angle {angle_idx} step {step}!")
                        self.press(VK_J, 5.0)
                        return True

            # Walk back to roughly center after each angle
            self.hold(VK_S, 3.0)
            time.sleep(0.2)

            # OCR check for battle/treasure (may have auto-entered)
            full, ocr, _ = self.ocr_screen()
            state = self._check_arena_state(full)
            if state:
                return self._handle_arena_state(state)

            # Also check for character reward / upgrade screens
            if "角色奖励" in full or "近战" in full or "远程" in full:
                return True  # Handled by main loop dismiss_dialog

        self.log("  Could not find portal after all angles")
        return False

    def _check_arena_state(self, full: str) -> str | None:
        """Check OCR text for known arena states. Returns state name or None."""
        if "前往" in full:
            return "portal_prompt"
        if "珍宝选择" in full or "珍宝" in full:
            return "treasure"
        if "击退" in full or "剩余敌人" in full:
            return "battle"
        if "结束挑战" in full or "挑战结束" in full:
            return "run_complete"
        if "失败" in full or "复活" in full:
            return "defeat"
        if "角色奖励" in full:
            return "character_reward"
        return None

    def _handle_arena_state(self, state: str) -> bool:
        """Handle detected arena state during portal search."""
        if state == "portal_prompt":
            self.log("  Portal found! Pressing J to enter...")
            self.press(VK_J, 5.0)
            return True
        elif state == "treasure":
            self.log("  Treasure selection showing")
            return True
        elif state == "battle":
            self.log("  Battle started!")
            return True
        elif state == "character_reward":
            self.log("  Character reward screen")
            return True
        elif state in ("run_complete", "defeat"):
            self.log(f"  Run ended ({state})")
            return True
        return False

    # ── Combat ──

    def fight_battle(self) -> str:
        """Run combat until battle ends. Returns: 'won', 'died', 'timeout'."""
        self.log(f"=== BATTLE START (floor {self.floor}) ===")

        # Wait for battle to actually start (loading transition)
        time.sleep(3.0)

        max_checks = 30  # ~5 minutes max
        for check in range(max_checks):
            # Attack for ~10 seconds (5 cycles)
            self.attack_cycle(5)

            # Check state
            full, ocr, _ = self.ocr_screen()

            # Battle still ongoing
            if "击退" in full or "剩余敌人" in full:
                self.log(f"  Combat ongoing (check {check + 1}/{max_checks})")
                continue

            # Battle won → treasure selection
            if "珍宝选择" in full or "珍宝" in full:
                self.log("  Battle WON → Treasure selection")
                return "won"

            # Back to arena (navigation between floors)
            if "当前关卡" in full and "击退" not in full:
                self.log("  Back to arena navigation")
                return "won"

            # Battle end / settlement
            if "结算" in full or "评价" in full or "任务完成" in full:
                self.log("  Battle END → Settlement")
                return "won"

            # Defeat
            if "失败" in full or "复活" in full:
                self.log("  DEFEAT detected")
                return "died"

            # Run complete
            if "结束挑战" in full or "挑战结束" in full:
                self.log("  Challenge complete")
                return "won"

            # Loading screen (very sparse OCR, just ID)
            if len(ocr._items) <= 2:
                self.log(f"  Loading screen detected, waiting...")
                time.sleep(3.0)
                continue

            # Generic dialog (reward popup, etc.) — try to dismiss
            if "确认" in full:
                self.log("  Dialog detected, dismissing...")
                pos = self.find_ocr_center(ocr, "确认")
                if pos:
                    self.click_px(pos[0], pos[1], 2.0)
                else:
                    self.press(VK_ENTER, 1.0)
                continue

            # Unknown state - keep attacking
            self.log(f"  Unknown state (check {check + 1}), continuing combat...")

        self.log("  Combat TIMEOUT")
        return "timeout"

    # ── Treasure selection ──

    def handle_treasure(self) -> bool:
        """Select first treasure card and confirm."""
        self.log("Handling treasure selection...")
        full, ocr, _ = self.ocr_screen()

        if "珍宝选择" not in full:
            self.log("  Not on treasure screen, skipping")
            return True

        # Click first card (leftmost, ~25% from left, ~40% from top)
        self.click_frac(0.20, 0.40, 1.0)

        # Click 确认
        pos = None
        full, ocr, _ = self.ocr_screen()
        pos = self.find_ocr_center(ocr, "确认")
        if pos:
            self.log(f"  Clicking 确认 at ({pos[0]}, {pos[1]})")
            self.click_px(pos[0], pos[1], 2.0)
        else:
            # Fallback position for 确认
            self.click_frac(0.667, 0.846, 2.0)

        return True

    # ── End-of-run handling ──

    def handle_run_end(self):
        """Handle end of run: settlement screen, rewards, return to hub."""
        self.log("Handling run end...")

        # Try ESC → pause menu → H (退出并结算)
        self.press(VK_ESC, 1.5)
        full, ocr, _ = self.ocr_screen()

        if "退出" in full or "结算" in full:
            self.log("  Pause menu detected, pressing H to exit")
            self.press(VK_H, 2.0)

        for attempt in range(15):
            full, ocr, _ = self.ocr_screen()

            # Confirm exit dialog
            if "确认" in full:
                pos = self.find_ocr_center(ocr, "确认")
                if pos:
                    self.click_px(pos[0], pos[1], 2.0)
                    continue

            # Score/reward settlement screens — just keep clicking
            if "结算" in full or "评价" in full or "获得" in full or "奖励" in full:
                self.log(f"  Settlement screen (attempt {attempt + 1})")
                self.press(VK_ENTER, 1.0)
                self.click_frac(0.5, 0.5, 1.0)
                continue

            # Back at 多维变量 main page
            if "多维变量" in full and ("开始挑战" in full or "维度偏移" in full):
                self.log("  Back at 多维变量 main page")
                return

            # Back at hub
            if "情报" in full or "常驻" in full:
                self.log("  Back at hub")
                return

            # Unknown — try Enter/click to dismiss
            self.press(VK_ENTER, 0.5)
            self.click_frac(0.5, 0.8, 1.0)

        self.log("  Force ESC to get out")
        for _ in range(5):
            self.press(VK_ESC, 1.0)

    # ── Main loop ──

    def run(self, resume: bool = False) -> None:
        """Run the full 多维变量 automation loop."""
        self.log("=" * 50)
        self.log("  多维变量 Autonomous Runner")
        self.log(f"  Max floors: {self.max_floors}")
        self.log(f"  Resume mode: {resume}")
        self.log("=" * 50)

        if not resume:
            if not self.navigate_to_duowei():
                self.log("FAILED: Cannot navigate to 多维变量")
                return
            if not self.complete_setup_wizard():
                self.log("FAILED: Cannot complete setup wizard")
                return

        # Main roguelike loop
        consecutive_fails = 0
        while self.floor < self.max_floors:
            self.floor += 1
            self.log(f"\n--- Floor {self.floor}/{self.max_floors} ---")

            # Detect current state
            full, ocr, _ = self.ocr_screen()

            # Dismiss any generic dialogs (reward popups etc.)
            while "确认" in full and "击退" not in full and "珍宝选择" not in full:
                self.log("Dismissing dialog...")
                pos = self.find_ocr_center(ocr, "确认")
                if pos:
                    self.click_px(pos[0], pos[1], 2.0)
                else:
                    self.press(VK_ENTER, 1.0)
                time.sleep(1.0)
                full, ocr, _ = self.ocr_screen()

            # Handle treasure if showing
            if "珍宝选择" in full or "珍宝" in full:
                self.handle_treasure()
                time.sleep(3.0)
                full, ocr, _ = self.ocr_screen()

            # Already in battle?
            if "击退" in full or "剩余敌人" in full:
                result = self.fight_battle()
            # In arena? walk to portal
            elif "当前关卡" in full or ("击退" not in full and "珍宝" not in full):
                if not self.walk_to_portal():
                    consecutive_fails += 1
                    self.log(f"Portal not found ({consecutive_fails} consecutive)")
                    if consecutive_fails >= 3:
                        self.log("Too many portal failures, exiting run")
                        self.handle_run_end()
                        break
                    self.floor -= 1  # Don't count failed floor
                    continue
                consecutive_fails = 0

                # Re-check state after portal navigation
                time.sleep(3.0)
                full, ocr, _ = self.ocr_screen()

                if "击退" in full or "剩余敌人" in full:
                    result = self.fight_battle()
                elif "珍宝选择" in full or "珍宝" in full:
                    result = "won"  # Non-combat portal
                elif "结束挑战" in full or "挑战结束" in full:
                    self.log("Challenge complete!")
                    self.handle_run_end()
                    break
                elif "失败" in full or "复活" in full:
                    self.log("Defeat detected after portal")
                    self.handle_run_end()
                    break
                elif "角色奖励" in full or ("确认" in full and "当前关卡" not in full):
                    # Character reward / upgrade screen — dismiss and continue
                    self.log("Character reward screen, dismissing...")
                    pos = self.find_ocr_center(ocr, "确认")
                    if pos:
                        self.click_px(pos[0], pos[1], 2.0)
                    else:
                        self.press(VK_ENTER, 1.0)
                    result = "won"
                elif "当前关卡" in full:
                    # New arena — loop will walk to next portal
                    self.log("  New arena detected, continuing...")
                    result = "won"
                else:
                    # Might be loading or new arena — wait and re-check
                    self.log("Waiting for state transition...")
                    time.sleep(5.0)
                    full, ocr, _ = self.ocr_screen()
                    if "击退" in full or "剩余" in full:
                        result = self.fight_battle()
                    elif "珍宝" in full:
                        result = "won"
                    elif "当前关卡" in full:
                        # New arena after portal — need another portal walk
                        self.log("  New arena detected, continuing to next portal...")
                        result = "won"  # Count as progress
                    else:
                        self.log(f"Unexpected state: {full[:100]}")
                        result = "timeout"
            else:
                self.log(f"Unknown state at loop start: {full[:100]}")
                result = "timeout"

            # Handle result
            if result == "won":
                self.log(f"Floor {self.floor} CLEARED!")
                time.sleep(2.0)
            elif result == "died":
                self.log(f"DIED on floor {self.floor}")
                self.handle_run_end()
                break
            elif result == "timeout":
                self.log(f"TIMEOUT on floor {self.floor}, trying to exit")
                self.handle_run_end()
                break

        self.log(f"\n=== Run complete! Cleared {self.floor} floors ===")


def main():
    parser = argparse.ArgumentParser(description="多维变量 autonomous runner")
    parser.add_argument("--resume", action="store_true",
                        help="Resume mid-run (already in 多维变量 arena)")
    parser.add_argument("--max-floors", type=int, default=20,
                        help="Max floors to attempt (default: 20)")
    args = parser.parse_args()

    device = DeviceAdapter(AETHER_GAZER_CONFIG.to_device_config())
    device.connect()

    try:
        runner = DuoweiRunner(device, max_floors=args.max_floors)
        runner.run(resume=args.resume)
    finally:
        device.disconnect()


if __name__ == "__main__":
    main()
