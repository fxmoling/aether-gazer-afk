"""页面识别器 — 基于像素特征判断当前页面

使用稳定文字区域的亮色像素集群来识别页面。
不依赖 OCR，而是利用已知的文字区域特征模式匹配。
"""

from __future__ import annotations

import numpy as np
from loguru import logger

from anime_game_afk.games.aether_gazer.pages.definitions import (
    ALL_PAGES,
    BOTTOM_NAV_REGION,
    Coord,
    PageDef,
    Region,
)


def _count_bright_pixels(img: np.ndarray, region: Region,
                          threshold: int = 550) -> int:
    """统计区域内的亮色像素数量

    亮色像素 = R+G+B > threshold (白色文字/UI元素)
    """
    h, w = img.shape[:2]
    y1 = max(0, region.y1)
    y2 = min(h, region.y2)
    x1 = max(0, region.x1)
    x2 = min(w, region.x2)

    roi = img[y1:y2, x1:x2]
    if roi.size == 0:
        return 0

    # 计算 R+G+B 亮度
    brightness = roi.astype(np.int32).sum(axis=2)
    return int(np.sum(brightness > threshold))


def _find_text_clusters_in_region(
    img: np.ndarray,
    region: Region,
    brightness_threshold: int = 550,
    step: int = 3,
    min_cluster_pixels: int = 5,
    cluster_gap: int = 30,
) -> list[dict]:
    """在指定区域内查找亮色像素集群（文字位置）"""
    h, w = img.shape[:2]
    y1 = max(0, region.y1)
    y2 = min(h, region.y2)
    x1 = max(0, region.x1)
    x2 = min(w, region.x2)

    # 收集所有亮色像素的 x 坐标
    all_bright_x = []
    for y in range(y1, y2, 2):
        for x in range(x1, x2, step):
            px = img[y, x]
            brightness = int(px[0]) + int(px[1]) + int(px[2])
            if brightness > brightness_threshold:
                all_bright_x.append(x)

    if not all_bright_x:
        return []

    # 聚类
    all_bright_x.sort()
    clusters = []
    current = [all_bright_x[0]]
    for x in all_bright_x[1:]:
        if x - current[-1] > cluster_gap:
            clusters.append(current)
            current = [x]
        else:
            current.append(x)
    clusters.append(current)

    result = []
    for cluster in clusters:
        if len(cluster) < min_cluster_pixels:
            continue
        result.append({
            "x_center": int(np.median(cluster)),
            "x_range": [min(cluster), max(cluster)],
            "width": max(cluster) - min(cluster),
            "pixel_count": len(cluster),
        })
    return result


def check_bottom_nav_present(img: np.ndarray) -> bool:
    """检查底部导航栏是否存在（hub的决定性特征）

    hub底部栏有 7 个文字集群 (修正者/探测/商店/公会/仓库/游园街/前往作战)
    """
    clusters = _find_text_clusters_in_region(img, BOTTOM_NAV_REGION)
    return len(clusters) >= 5


def identify_page(img: np.ndarray) -> tuple[str, float]:
    """识别当前截图对应的页面

    Returns:
        (page_id, confidence) — confidence 0.0~1.0
        如果无法识别，返回 ("unknown", 0.0)
    """
    h, w = img.shape[:2]

    # 策略1: 检查是否在主大厅 (底部导航栏 7 个按钮)
    hub_clusters = _find_text_clusters_in_region(img, BOTTOM_NAV_REGION)
    if len(hub_clusters) >= 6:
        # 进一步确认: 检查设置面板是否打开 (右侧有功能网格)
        right_bright = _count_bright_pixels(
            img, Region(1100, 150, 1550, 550))
        if right_bright > 5000:
            # 右侧有大量亮色像素 = 可能是设置面板overlay
            # 检查设置面板特征文字区域
            settings_clusters = _find_text_clusters_in_region(
                img, Region(1100, 150, 1550, 600))
            if len(settings_clusters) >= 6:
                return ("settings_panel", 0.85)

        return ("main_hub", 0.95)

    # 策略2: 分析整体亮度分布特征
    # 某些页面有非常鲜明的亮度特征
    top_brightness = _avg_brightness(img, Region(0, 0, w, 80))
    left_brightness = _avg_brightness(img, Region(0, 80, 200, h - 100))
    center_brightness = _avg_brightness(img, Region(200, 80, w - 200, h - 100))
    bottom_brightness = _avg_brightness(img, Region(0, h - 100, w, h))

    # 策略3: 检查每个页面的特征区域
    best_match = "unknown"
    best_score = 0.0

    for page_id, page_def in ALL_PAGES.items():
        if page_id == "main_hub":
            continue  # 已在上面处理

        score = _score_page_match(img, page_def)
        if score > best_score:
            best_score = score
            best_match = page_id

    if best_score < 0.3:
        return ("unknown", best_score)

    return (best_match, best_score)


def _avg_brightness(img: np.ndarray, region: Region) -> float:
    """计算区域平均亮度 (0-255)"""
    h, w = img.shape[:2]
    y1 = max(0, region.y1)
    y2 = min(h, region.y2)
    x1 = max(0, region.x1)
    x2 = min(w, region.x2)
    roi = img[y1:y2, x1:x2]
    if roi.size == 0:
        return 0.0
    import cv2
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray))


def _score_page_match(img: np.ndarray, page_def: PageDef) -> float:
    """给一个页面定义打分：当前截图与该页面的匹配程度

    基于每个 stable_text 对应区域的亮色像素集群存在性。
    每个匹配的文字特征得 1 分，最终归一化到 0-1。
    """
    if not page_def.stable_texts:
        return 0.0

    matches = 0
    total = len(page_def.stable_texts)

    for text_feat in page_def.stable_texts:
        # 检查该区域是否有足够的亮色像素（说明有文字）
        bright_count = _count_bright_pixels(img, text_feat.region)
        if bright_count > 20:
            matches += 1

    return matches / total if total > 0 else 0.0


def is_on_page(img: np.ndarray, page_id: str) -> bool:
    """快速检查是否在指定页面"""
    detected, confidence = identify_page(img)
    return detected == page_id and confidence >= 0.5
