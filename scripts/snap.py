"""snap.py — 轻量级截图工具

生成两个文件:
  - raw/{name}.png  — 原始 1600x900 (用于像素级分析)
  - thumb/{name}.jpg — 800x450 缩略图 (~30-50KB, 用于目视确认)

用法:
    python scripts/snap.py                  # 截图当前画面
    python scripts/snap.py --name hub       # 指定名称
    python scripts/snap.py --click 940 855  # 先点击再截图
    python scripts/snap.py --key 0x1B       # 先按键再截图
    python scripts/snap.py --wait 2.0       # 等待后截图
    python scripts/snap.py --crop 0 800 500 900  # 额外裁剪区域的缩略图
    python scripts/snap.py --info 940 855   # 查看某像素的BGR值
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

# Design resolution for pixel→fractional coordinate conversion
_DESIGN_W, _DESIGN_H = 1600, 900

# 输出目录
OUT_DIR = Path("assets/aether_gazer/screenshots/deep")
RAW_DIR = OUT_DIR / "raw"
THUMB_DIR = OUT_DIR / "thumb"

# 缩略图参数
THUMB_WIDTH = 800
THUMB_QUALITY = 65


def snap(
    device: DeviceAdapter,
    name: str,
    crop: tuple[int, int, int, int] | None = None,
) -> tuple[Path, Path]:
    """截图并保存 raw + thumb

    Returns:
        (raw_path, thumb_path)
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    THUMB_DIR.mkdir(parents=True, exist_ok=True)

    # raw 用原始分辨率，thumb 用缩放后截图
    img_raw = device.screenshot_raw()
    img = device.screenshot()
    h, w = img.shape[:2]

    # 保存原始 PNG (实际窗口分辨率)
    raw_path = RAW_DIR / f"{name}.png"
    cv2.imwrite(str(raw_path), img_raw, [cv2.IMWRITE_PNG_COMPRESSION, 9])

    # 生成缩略图
    scale = THUMB_WIDTH / w
    th = int(h * scale)
    thumb = cv2.resize(img, (THUMB_WIDTH, th), interpolation=cv2.INTER_AREA)
    thumb_path = THUMB_DIR / f"{name}.jpg"
    cv2.imwrite(str(thumb_path), thumb, [cv2.IMWRITE_JPEG_QUALITY, THUMB_QUALITY])

    print(f"raw:   {raw_path} ({w}x{h})")
    print(f"thumb: {thumb_path} ({THUMB_WIDTH}x{th}, ~{thumb_path.stat().st_size // 1024}KB)")

    # 可选裁剪区域缩略图
    if crop:
        x1, y1, x2, y2 = crop
        region = img[y1:y2, x1:x2]
        crop_path = THUMB_DIR / f"{name}_crop.jpg"
        cv2.imwrite(str(crop_path), region, [cv2.IMWRITE_JPEG_QUALITY, 80])
        rh, rw = region.shape[:2]
        print(f"crop:  {crop_path} ({rw}x{rh}, ~{crop_path.stat().st_size // 1024}KB)")

    return raw_path, thumb_path


def pixel_info(device: DeviceAdapter, x: int, y: int) -> None:
    """打印指定像素的信息"""
    img = device.screenshot()
    px = img[y, x]
    b, g, r = int(px[0]), int(px[1]), int(px[2])
    brightness = b + g + r
    print(f"({x},{y}): BGR=({b},{g},{r}) RGB=({r},{g},{b}) brightness={brightness}")


def main():
    parser = argparse.ArgumentParser(description="轻量级截图工具")
    parser.add_argument("--name", "-n", default="snap", help="截图名称")
    parser.add_argument("--click", "-c", nargs=2, type=int, metavar=("X", "Y"),
                        help="截图前先点击")
    parser.add_argument("--key", "-k", type=lambda x: int(x, 0),
                        help="截图前先按键 (如 0x1B)")
    parser.add_argument("--wait", "-w", type=float, default=0.5,
                        help="动作后等待秒数")
    parser.add_argument("--crop", nargs=4, type=int, metavar=("X1", "Y1", "X2", "Y2"),
                        help="额外保存裁剪区域")
    parser.add_argument("--info", "-i", nargs=2, type=int, metavar=("X", "Y"),
                        help="查看像素BGR值 (不截图)")
    args = parser.parse_args()

    device = DeviceAdapter(AETHER_GAZER_CONFIG.to_device_config())
    device.connect()

    try:
        if args.info:
            pixel_info(device, args.info[0], args.info[1])
            return

        if args.click:
            x, y = args.click
            fx, fy = x / _DESIGN_W, y / _DESIGN_H
            print(f"click ({x}, {y}) -> fractional ({fx:.4f}, {fy:.4f})")
            device.click(fx, fy)
            time.sleep(args.wait)

        if args.key:
            print(f"key 0x{args.key:02X}")
            device.press_key(args.key)
            time.sleep(args.wait)

        crop = tuple(args.crop) if args.crop else None
        snap(device, args.name, crop=crop)

    finally:
        device.disconnect()


if __name__ == "__main__":
    main()
