"""批量页面探索 — 一次性截图所有可达页面

从主大厅出发，依次点击每个导航按钮，截图后返回。
所有截图保存为小尺寸 JPEG（< 150KB），避免 Claude 20MB 限制。

用法:
    python scripts/explore_all_pages.py              # 执行完整探索
    python scripts/explore_all_pages.py --dry-run    # 仅打印计划
    python scripts/explore_all_pages.py --convert     # 仅转换现有截图为小尺寸 JPEG
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from loguru import logger

# 添加 src 到 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
from anime_game_afk.core.device import DeviceAdapter

# Design resolution for pixel→fractional coordinate conversion
_DESIGN_W, _DESIGN_H = 1600, 900

# === 配置 ===

# Claude 安全的截图参数: 800px 宽 + JPEG quality 65 → 每张约 80-150KB
# 一次对话最多看 ~50 张 = ~5-7.5MB，远低于 20MB 限制
DISPLAY_WIDTH = 800
JPEG_QUALITY = 65

SCREENSHOT_DIR = Path("assets/aether_gazer/screenshots/pages")
RAW_DIR = Path("assets/aether_gazer/screenshots/raw")

# 底部导航栏按钮（从 00_main_hub.md 中提取，1600x900 坐标）
BOTTOM_NAV_BUTTONS = {
    "character": {"name": "修正者", "coord": (540, 860), "back_coord": (48, 48)},
    "gacha": {"name": "探测", "coord": (650, 850), "back_coord": (48, 48)},
    "shop": {"name": "商店", "coord": (760, 860), "back_coord": (48, 48)},
    "guild": {"name": "公会", "coord": (870, 860), "back_coord": (48, 48)},
    "inventory": {"name": "仓库", "coord": (960, 860), "back_coord": (48, 48)},
    "amusement": {"name": "游园街", "coord": (1060, 860), "back_coord": (48, 48)},
}

# 右侧重要按钮
RIGHT_BUTTONS = {
    "battle_select": {"name": "前往作战", "coord": (1500, 860), "back_coord": (48, 48)},
}

# 左侧面板按钮
LEFT_PANEL_BUTTONS = {
    "tactics": {"name": "对策协议", "coord": (100, 170), "back_coord": (48, 48)},
    "training": {"name": "进修企划", "coord": (100, 260), "back_coord": (48, 48)},
    "events": {"name": "入职活动", "coord": (100, 370), "back_coord": (48, 48)},
}


def save_small_jpg(img: np.ndarray, path: Path) -> Path:
    """保存为小尺寸 JPEG，Claude 安全

    Returns:
        保存的路径
    """
    h, w = img.shape[:2]
    if w > DISPLAY_WIDTH:
        scale = DISPLAY_WIDTH / w
        img = cv2.resize(
            img,
            (DISPLAY_WIDTH, int(h * scale)),
            interpolation=cv2.INTER_AREA,
        )

    path = path.with_suffix(".jpg")
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    size_kb = path.stat().st_size / 1024
    logger.info("保存: {} ({:.0f} KB, {}x{})", path.name, size_kb, img.shape[1], img.shape[0])
    return path


def save_raw_png(img: np.ndarray, path: Path) -> Path:
    """保存原始分辨率 PNG（用于精确坐标分析）"""
    path = path.with_suffix(".png")
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    size_kb = path.stat().st_size / 1024
    logger.info("保存 (raw): {} ({:.0f} KB)", path.name, size_kb)
    return path


def explore_all(dry_run: bool = False) -> None:
    """从主大厅出发，探索所有可达页面"""

    all_buttons = {}
    all_buttons.update(BOTTOM_NAV_BUTTONS)
    all_buttons.update(RIGHT_BUTTONS)
    all_buttons.update(LEFT_PANEL_BUTTONS)

    if dry_run:
        logger.info("=== 探索计划 (dry run) ===")
        for page_id, btn in all_buttons.items():
            logger.info("  {} → 点击 {} at {}", page_id, btn["name"], btn["coord"])
        logger.info("共 {} 个页面", len(all_buttons))
        return

    device = DeviceAdapter(AETHER_GAZER_CONFIG.to_device_config())
    device.connect()

    results = {}

    try:
        # 0. 先截图当前状态
        logger.info("=== 开始探索 ===")
        img = device.screenshot()
        save_small_jpg(img, SCREENSHOT_DIR / "00_current_state")
        save_raw_png(img, RAW_DIR / "00_current_state")

        # 逐个探索
        for idx, (page_id, btn) in enumerate(all_buttons.items(), 1):
            logger.info("\n--- [{}/{}] 探索: {} ({}) ---", idx, len(all_buttons), page_id, btn["name"])

            # 点击唤醒UI（某些页面UI会隐藏）
            device.click(800 / _DESIGN_W, 450 / _DESIGN_H)
            time.sleep(0.5)

            # 点击目标按钮
            x, y = btn["coord"]
            logger.info("点击 ({}, {}) → {}", x, y, btn["name"])
            device.click(x / _DESIGN_W, y / _DESIGN_H)
            time.sleep(2.0)  # 等待页面加载

            # 截图新页面
            img = device.screenshot()
            h, w = img.shape[:2]
            jpg_path = save_small_jpg(img, SCREENSHOT_DIR / f"{idx:02d}_{page_id}")
            raw_path = save_raw_png(img, RAW_DIR / f"{idx:02d}_{page_id}")

            results[page_id] = {
                "name": btn["name"],
                "click_coord": btn["coord"],
                "screenshot": str(jpg_path),
                "raw_screenshot": str(raw_path),
                "resolution": f"{w}x{h}",
            }

            # 返回主大厅
            bx, by = btn["back_coord"]
            logger.info("返回: 点击 ({}, {})", bx, by)
            device.click(bx / _DESIGN_W, by / _DESIGN_H)
            time.sleep(1.5)

        # 最终状态
        img = device.screenshot()
        save_small_jpg(img, SCREENSHOT_DIR / "99_final_state")

        # 保存探索结果
        results_path = SCREENSHOT_DIR / "exploration_results.json"
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info("\n=== 探索完成 ===")
        logger.info("结果保存至: {}", results_path)
        logger.info("截图目录: {}", SCREENSHOT_DIR)

    finally:
        device.disconnect()


def convert_existing() -> None:
    """将现有的大截图转换为小尺寸 JPEG"""
    src_dir = Path("assets/aether_gazer/screenshots")
    out_dir = SCREENSHOT_DIR / "converted"

    png_files = sorted(src_dir.glob("*.png"))
    logger.info("找到 {} 个 PNG 文件", len(png_files))

    total_before = 0
    total_after = 0

    for f in png_files:
        img = cv2.imread(str(f))
        if img is None:
            logger.warning("无法读取: {}", f.name)
            continue

        size_before = f.stat().st_size
        total_before += size_before

        out_path = save_small_jpg(img, out_dir / f.stem)
        size_after = out_path.stat().st_size
        total_after += size_after

        ratio = size_after / size_before * 100
        logger.info("  {}: {:.0f} KB → {:.0f} KB ({:.0f}%)", f.name, size_before/1024, size_after/1024, ratio)

    logger.info("\n总计: {:.1f} MB → {:.1f} MB ({:.0f}% 压缩率)",
                total_before/1024/1024, total_after/1024/1024,
                total_after/total_before*100 if total_before else 0)


def main() -> None:
    parser = argparse.ArgumentParser(description="批量页面探索")
    parser.add_argument("--dry-run", action="store_true", help="仅打印计划")
    parser.add_argument("--convert", action="store_true", help="转换现有截图为小JPEG")
    args = parser.parse_args()

    if args.convert:
        convert_existing()
    else:
        explore_all(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
