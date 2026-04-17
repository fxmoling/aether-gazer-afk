"""系统化页面探索 — 从主大厅出发，逐页截图并记录特征

每个页面：截图(raw+小JPEG) → 分析像素特征 → 写结构化JSON → 返回hub

注意安全规则：
- 探测页面只截图，不做操作，立即退出
- 仓库页面只截图表面，不点击任何物品
- 每步操作间有合理等待

用法:
    python scripts/explore_systematic.py                # 完整探索
    python scripts/explore_systematic.py --page X       # 探索单个页面
    python scripts/explore_systematic.py --keys-only    # 只探索键盘快捷键页面
    python scripts/explore_systematic.py --from-hub     # 先回到hub再探索
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime

import cv2
import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
from anime_game_afk.core.device import DeviceAdapter

# Design resolution for pixel→fractional coordinate conversion
_DESIGN_W, _DESIGN_H = 1600, 900

# === 常量 ===
DISPLAY_WIDTH = 800
JPEG_QUALITY = 65
BASE_DIR = Path("assets/aether_gazer/screenshots/systematic")
RAW_DIR = BASE_DIR / "raw"
RESULTS_FILE = BASE_DIR / "exploration_results.json"

# 已验证坐标 (1600×900)
# 从 hub 出发的所有导航目标
NAVIGATION_MAP = {
    # --- 底部导航栏 (y≈850) ---
    "character": {
        "name": "修正者",
        "name_en": "Character (Modifier)",
        "nav_method": "click",
        "coord": (675, 850),
        "back_method": "click",
        "back_coord": (35, 35),
        "wait_after_click": 2.0,
        "wait_after_back": 1.5,
        "safe": True,
        "explore_depth": "surface",  # 只看表面
    },
    "gacha": {
        "name": "探测",
        "name_en": "Gacha (Detect)",
        "nav_method": "click",
        "coord": (790, 850),
        "back_method": "key",
        "back_key": 0x1B,  # ESC
        "wait_after_click": 2.0,
        "wait_after_back": 1.5,
        "safe": False,  # ⚠️ 禁止深入操作
        "explore_depth": "screenshot_only",
    },
    "shop": {
        "name": "商店",
        "name_en": "Shop",
        "nav_method": "click",
        "coord": (910, 850),
        "back_method": "click",
        "back_coord": (35, 35),
        "wait_after_click": 2.0,
        "wait_after_back": 1.5,
        "safe": True,
        "explore_depth": "surface",
    },
    "guild": {
        "name": "公会",
        "name_en": "Guild",
        "nav_method": "click",
        "coord": (1025, 850),
        "back_method": "click",
        "back_coord": (35, 35),
        "wait_after_click": 2.0,
        "wait_after_back": 1.5,
        "safe": True,
        "explore_depth": "surface",
    },
    "inventory": {
        "name": "仓库",
        "name_en": "Inventory",
        "nav_method": "click",
        "coord": (1140, 850),
        "back_method": "click",
        "back_coord": (35, 35),
        "wait_after_click": 2.0,
        "wait_after_back": 1.5,
        "safe": False,  # 不要深入，避免影响物品
        "explore_depth": "screenshot_only",
    },
    "amusement": {
        "name": "游园街",
        "name_en": "Amusement Street",
        "nav_method": "click",
        "coord": (1257, 850),
        "back_method": "click",
        "back_coord": (48, 48),
        "wait_after_click": 2.0,
        "wait_after_back": 1.5,
        "safe": True,
        "explore_depth": "surface",
    },
    "battle_select": {
        "name": "前往作战",
        "name_en": "Battle Select",
        "nav_method": "click",
        "coord": (1465, 850),
        "back_method": "click",
        "back_coord": (35, 35),
        "wait_after_click": 2.0,
        "wait_after_back": 1.5,
        "safe": True,
        "explore_depth": "detailed",
    },
    # --- 键盘快捷键 ---
    "daily_tasks": {
        "name": "每日任务",
        "name_en": "Daily Tasks",
        "nav_method": "key",
        "key_code": 0x47,  # G
        "back_method": "key",
        "back_key": 0x1B,  # ESC
        "wait_after_click": 2.0,
        "wait_after_back": 1.5,
        "safe": True,
        "explore_depth": "detailed",
    },
    "mail": {
        "name": "邮件",
        "name_en": "Mail",
        "nav_method": "key",
        "key_code": 0x48,  # H
        "back_method": "key",
        "back_key": 0x1B,  # ESC
        "wait_after_click": 2.0,
        "wait_after_back": 1.5,
        "safe": True,
        "explore_depth": "surface",
    },
    "settings_panel": {
        "name": "设置面板",
        "name_en": "Settings Panel",
        "nav_method": "key",
        "key_code": 0x09,  # Tab
        "back_method": "key",
        "back_key": 0x1B,  # ESC
        "wait_after_click": 2.0,
        "wait_after_back": 1.5,
        "safe": True,
        "explore_depth": "detailed",
    },
    # --- 左侧面板 ---
    "tactics": {
        "name": "对策协议",
        "name_en": "Tactics Protocol",
        "nav_method": "click",
        "coord": (100, 170),
        "back_method": "click",
        "back_coord": (35, 35),
        "wait_after_click": 2.0,
        "wait_after_back": 1.5,
        "safe": True,
        "explore_depth": "surface",
    },
    "training": {
        "name": "进修企划",
        "name_en": "Training Plan",
        "nav_method": "click",
        "coord": (100, 260),
        "back_method": "click",
        "back_coord": (35, 35),
        "wait_after_click": 2.0,
        "wait_after_back": 1.5,
        "safe": True,
        "explore_depth": "surface",
    },
    "events": {
        "name": "入职活动",
        "name_en": "Events (Newbie)",
        "nav_method": "click",
        "coord": (100, 370),
        "back_method": "click",
        "back_coord": (35, 35),
        "wait_after_click": 2.0,
        "wait_after_back": 1.5,
        "safe": True,
        "explore_depth": "surface",
    },
    # --- 顶部栏 ---
    "player_info": {
        "name": "玩家信息",
        "name_en": "Player Info",
        "nav_method": "click",
        "coord": (50, 40),
        "back_method": "key",
        "back_key": 0x1B,  # ESC
        "wait_after_click": 2.0,
        "wait_after_back": 1.5,
        "safe": True,
        "explore_depth": "surface",
    },
}


def save_jpg(img: np.ndarray, path: Path) -> Path:
    """保存小尺寸 JPEG"""
    h, w = img.shape[:2]
    if w > DISPLAY_WIDTH:
        scale = DISPLAY_WIDTH / w
        img = cv2.resize(img, (DISPLAY_WIDTH, int(h * scale)), interpolation=cv2.INTER_AREA)
    path = path.with_suffix(".jpg")
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    size_kb = path.stat().st_size / 1024
    logger.info("保存: {} ({:.0f} KB)", path.name, size_kb)
    return path


def save_raw(img: np.ndarray, path: Path) -> Path:
    """保存原始 PNG"""
    path = path.with_suffix(".png")
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    return path


def analyze_regions(img: np.ndarray) -> dict:
    """分析截图的多个区域的像素特征

    返回每个区域的亮色像素分布，用于后续页面识别
    """
    h, w = img.shape[:2]
    regions = {
        "top_bar": (0, 0, w, 80),           # 顶部栏
        "left_panel": (0, 80, 200, h - 100), # 左侧面板
        "bottom_bar": (0, h - 100, w, h),    # 底部栏
        "center": (200, 80, w - 200, h - 100), # 中央区域
        "right_panel": (w - 200, 80, w, h - 100), # 右侧面板
        "title_area": (w // 4, 0, 3 * w // 4, 80), # 标题区域
    }

    result = {}
    for name, (x1, y1, x2, y2) in regions.items():
        roi = img[y1:y2, x1:x2]
        if roi.size == 0:
            continue
        # 计算平均亮度
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        avg_brightness = float(np.mean(gray))
        # 计算亮色像素占比 (brightness > 180 → 白色文字/UI)
        bright_ratio = float(np.sum(gray > 180) / gray.size)
        # 主色调
        avg_color = [int(x) for x in np.mean(roi.reshape(-1, 3), axis=0)]
        result[name] = {
            "avg_brightness": round(avg_brightness, 1),
            "bright_ratio": round(bright_ratio, 4),
            "avg_color_bgr": avg_color,
        }

    return result


def find_text_clusters(img: np.ndarray, y_start: int, y_end: int,
                        x_start: int = 0, x_end: int | None = None,
                        brightness_threshold: int = 550) -> list[dict]:
    """在指定行范围内扫描亮色像素集群（文字位置）

    返回每个集群的 x_center 和宽度估计
    """
    h, w = img.shape[:2]
    if x_end is None:
        x_end = w

    clusters_by_row = {}
    for y in range(max(0, y_start), min(h, y_end)):
        bright_xs = []
        for x in range(x_start, min(w, x_end), 3):
            px = img[y, x]
            brightness = int(px[0]) + int(px[1]) + int(px[2])
            if brightness > brightness_threshold:
                bright_xs.append(x)
        if bright_xs:
            clusters_by_row[y] = bright_xs

    # 合并所有行的亮色像素
    all_bright = []
    for xs in clusters_by_row.values():
        all_bright.extend(xs)

    if not all_bright:
        return []

    # 简单聚类：按 x 排序后找间隔
    all_bright.sort()
    clusters = []
    current = [all_bright[0]]

    for x in all_bright[1:]:
        if x - current[-1] > 30:  # 间隔 > 30px 视为新集群
            clusters.append(current)
            current = [x]
        else:
            current.append(x)
    clusters.append(current)

    result = []
    for cluster in clusters:
        if len(cluster) < 5:  # 忽略噪点
            continue
        x_center = int(np.median(cluster))
        x_min = min(cluster)
        x_max = max(cluster)
        result.append({
            "x_center": x_center,
            "x_range": [x_min, x_max],
            "width": x_max - x_min,
            "pixel_count": len(cluster),
        })

    return result


def check_bottom_nav_present(img: np.ndarray) -> bool:
    """检查底部导航栏是否存在（hub特征）"""
    clusters = find_text_clusters(img, 830, 870, 600, 1500)
    # hub底部栏应该有 6-7 个文字集群
    return len(clusters) >= 5


def ensure_hub(device: DeviceAdapter) -> bool:
    """确保当前在主大厅

    通过检查底部导航栏来判断。如果不在hub，尝试按ESC回到hub。
    最多尝试5次。
    """
    for attempt in range(5):
        img = device.screenshot()
        if check_bottom_nav_present(img):
            logger.info("✅ 当前在主大厅 (attempt {})", attempt)
            return True

        logger.warning("⚠️ 不在主大厅，尝试 ESC 返回 (attempt {})", attempt)
        device.press_key(0x1B)  # ESC
        time.sleep(1.5)

    # 最后一次检查
    img = device.screenshot()
    if check_bottom_nav_present(img):
        return True

    logger.error("❌ 无法返回主大厅")
    return False


def wake_ui(device: DeviceAdapter) -> None:
    """唤醒UI（某些页面UI会自动隐藏）"""
    device.click(800 / _DESIGN_W, 450 / _DESIGN_H)
    time.sleep(0.5)


def explore_page(device: DeviceAdapter, page_id: str, nav_info: dict) -> dict:
    """探索单个页面

    1. 从hub出发
    2. 导航到目标页面
    3. 截图并分析
    4. 返回hub
    """
    result = {
        "page_id": page_id,
        "name": nav_info["name"],
        "name_en": nav_info["name_en"],
        "timestamp": datetime.now().isoformat(),
        "success": False,
    }

    # 唤醒UI
    wake_ui(device)
    time.sleep(0.3)

    # 导航到目标
    if nav_info["nav_method"] == "click":
        x, y = nav_info["coord"]
        logger.info("→ 点击 ({}, {}) → {}", x, y, nav_info["name"])
        device.click(x / _DESIGN_W, y / _DESIGN_H)
    elif nav_info["nav_method"] == "key":
        key = nav_info["key_code"]
        logger.info("→ 按键 0x{:02X} → {}", key, nav_info["name"])
        device.press_key(key)

    time.sleep(nav_info["wait_after_click"])

    # 截图
    img = device.screenshot()
    h, w = img.shape[:2]

    # 保存截图
    jpg_path = save_jpg(img, BASE_DIR / f"page_{page_id}")
    raw_path = save_raw(img, RAW_DIR / f"page_{page_id}")

    # 分析像素特征
    regions = analyze_regions(img)

    # 分析底部栏文字集群（如果有）
    bottom_clusters = find_text_clusters(img, h - 100, h, 0, w)

    # 分析顶部栏
    top_clusters = find_text_clusters(img, 0, 80, 0, w)

    # 分析标题区域 (通常在顶部居中或靠左)
    title_clusters = find_text_clusters(img, 10, 60, 50, w // 2)

    result.update({
        "success": True,
        "resolution": f"{w}x{h}",
        "screenshot_jpg": str(jpg_path),
        "screenshot_raw": str(raw_path),
        "regions": regions,
        "bottom_clusters": bottom_clusters,
        "top_clusters": top_clusters,
        "title_clusters": title_clusters,
        "has_bottom_nav": len(bottom_clusters) >= 5,
    })

    # 返回 hub
    if nav_info["back_method"] == "click":
        bx, by = nav_info["back_coord"]
        logger.info("← 返回: 点击 ({}, {})", bx, by)
        device.click(bx / _DESIGN_W, by / _DESIGN_H)
    elif nav_info["back_method"] == "key":
        key = nav_info["back_key"]
        logger.info("← 返回: 按键 0x{:02X}", key)
        device.press_key(key)

    time.sleep(nav_info["wait_after_back"])

    return result


def explore_all(pages: list[str] | None = None, from_hub: bool = True) -> None:
    """系统化探索所有页面"""
    device = DeviceAdapter(AETHER_GAZER_CONFIG.to_device_config())
    device.connect()

    # 确定要探索的页面
    if pages:
        targets = {k: v for k, v in NAVIGATION_MAP.items() if k in pages}
    else:
        targets = NAVIGATION_MAP

    results = {}
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    try:
        # 确保在 hub
        if from_hub:
            if not ensure_hub(device):
                logger.error("无法定位到主大厅，中止探索")
                return

        # 截图 hub 初始状态
        wake_ui(device)
        time.sleep(0.5)
        hub_img = device.screenshot()
        save_jpg(hub_img, BASE_DIR / "hub_initial")
        save_raw(hub_img, RAW_DIR / "hub_initial")

        # 分析 hub
        hub_regions = analyze_regions(hub_img)
        hub_bottom = find_text_clusters(hub_img, 830, 870, 600, 1500)
        results["hub"] = {
            "page_id": "hub",
            "name": "主大厅",
            "name_en": "Main Hub",
            "regions": hub_regions,
            "bottom_clusters": hub_bottom,
            "has_bottom_nav": True,
        }

        # 逐个探索
        total = len(targets)
        for idx, (page_id, nav_info) in enumerate(targets.items(), 1):
            logger.info("\n{'='*60}")
            logger.info("[{}/{}] 探索: {} ({})", idx, total, page_id, nav_info["name"])
            logger.info("{'='*60}")

            # 确保在 hub
            if not ensure_hub(device):
                logger.error("无法返回主大厅，尝试多次ESC")
                for _ in range(3):
                    device.press_key(0x1B)
                    time.sleep(1.0)
                if not ensure_hub(device):
                    logger.error("放弃页面: {}", page_id)
                    results[page_id] = {"page_id": page_id, "success": False, "error": "无法返回hub"}
                    continue

            # 探索页面
            try:
                page_result = explore_page(device, page_id, nav_info)
                results[page_id] = page_result
                logger.info("✅ {} 探索完成", page_id)
            except Exception as e:
                logger.error("❌ {} 探索失败: {}", page_id, e)
                results[page_id] = {"page_id": page_id, "success": False, "error": str(e)}
                # 尝试恢复
                for _ in range(3):
                    device.press_key(0x1B)
                    time.sleep(1.0)

            # 每次探索后保存结果（防止中途崩溃丢失数据）
            save_results(results)

        # 最终回到 hub
        ensure_hub(device)
        final_img = device.screenshot()
        save_jpg(final_img, BASE_DIR / "hub_final")

        logger.info("\n{'='*60}")
        logger.info("探索完成! 共 {} 页面, 成功 {}",
                    len(results) - 1,  # 减去hub
                    sum(1 for r in results.values() if r.get("success", False)))
        logger.info("结果: {}", RESULTS_FILE)

    finally:
        device.disconnect()


def save_results(results: dict) -> None:
    """保存探索结果到JSON"""
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)


def main() -> None:
    parser = argparse.ArgumentParser(description="系统化页面探索")
    parser.add_argument("--page", "-p", nargs="+", help="指定探索的页面ID")
    parser.add_argument("--keys-only", action="store_true", help="只探索键盘快捷键页面")
    parser.add_argument("--from-hub", action="store_true", default=True, help="先确保在hub")
    parser.add_argument("--list", action="store_true", help="列出所有可探索页面")
    args = parser.parse_args()

    if args.list:
        for pid, info in NAVIGATION_MAP.items():
            safe_mark = "[OK]" if info["safe"] else "[!!]"
            logger.info("  {} {:20s} {:8s} ({})", safe_mark, pid, info["name"], info["name_en"])
        return

    pages = args.page
    if args.keys_only:
        pages = ["daily_tasks", "mail", "settings_panel"]

    explore_all(pages=pages, from_hub=True)


if __name__ == "__main__":
    main()
