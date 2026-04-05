"""battle_spam.py — 战斗自动按键

在战斗中循环按攻击/技能键，直到战斗结束。
用法:
    python scripts/battle_spam.py              # 默认60秒
    python scripts/battle_spam.py --duration 120  # 120秒
    python scripts/battle_spam.py --rounds 3      # 截图3次观察进度
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
from anime_game_afk.core.session import GameSession

# 战斗按键: J=普攻, U/I/O=技能, R=大招, 1/2=连携
BATTLE_KEYS = [
    0x4A,  # J - 普通攻击
    0x4A,  # J - 普通攻击 (多按几次作为主要输出)
    0x55,  # U - 技能
    0x4A,  # J - 普通攻击
    0x49,  # I - 技能
    0x4A,  # J - 普通攻击
    0x4F,  # O - 技能
    0x52,  # R - 大招
    0x31,  # 1 - 连携
    0x32,  # 2 - 连携
]

KEY_NAMES = {0x4A: "J", 0x55: "U", 0x49: "I", 0x4F: "O", 0x52: "R", 0x31: "1", 0x32: "2"}


def main():
    parser = argparse.ArgumentParser(description="战斗自动按键")
    parser.add_argument("--duration", "-d", type=int, default=60,
                        help="持续时间(秒)")
    parser.add_argument("--interval", type=float, default=0.3,
                        help="按键间隔(秒)")
    parser.add_argument("--snap-interval", type=int, default=20,
                        help="每N秒截图一次观察进度")
    args = parser.parse_args()

    session = GameSession(AETHER_GAZER_CONFIG)
    session.connect()

    try:
        import cv2
        out_dir = Path("assets/aether_gazer/screenshots/deep/thumb")
        out_dir.mkdir(parents=True, exist_ok=True)

        start = time.time()
        last_snap = start
        snap_count = 0
        key_idx = 0

        print(f"开始战斗按键循环 (持续{args.duration}秒, 间隔{args.interval}秒)")
        print(f"按键序列: {' '.join(KEY_NAMES[k] for k in BATTLE_KEYS)}")

        while time.time() - start < args.duration:
            # 按键
            key = BATTLE_KEYS[key_idx % len(BATTLE_KEYS)]
            session.press_key(key)
            key_idx += 1
            time.sleep(args.interval)

            # 定期截图
            if time.time() - last_snap >= args.snap_interval:
                snap_count += 1
                elapsed = int(time.time() - start)
                img = session.screenshot()
                h, w = img.shape[:2]
                thumb = cv2.resize(img, (800, 450), interpolation=cv2.INTER_AREA)
                snap_path = out_dir / f"battle_{snap_count}_{elapsed}s.jpg"
                cv2.imwrite(str(snap_path), thumb, [cv2.IMWRITE_JPEG_QUALITY, 65])
                print(f"[{elapsed}s] 已按{key_idx}次键, 截图: {snap_path}")
                last_snap = time.time()

        # 最终截图
        elapsed = int(time.time() - start)
        img = session.screenshot()
        thumb = cv2.resize(img, (800, 450), interpolation=cv2.INTER_AREA)
        snap_path = out_dir / f"battle_final_{elapsed}s.jpg"
        cv2.imwrite(str(snap_path), thumb, [cv2.IMWRITE_JPEG_QUALITY, 65])
        print(f"\n战斗结束! 共按{key_idx}次键, 耗时{elapsed}秒")
        print(f"最终截图: {snap_path}")

    finally:
        session.disconnect()


if __name__ == "__main__":
    main()
