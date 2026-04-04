"""游戏页面探索工具

提供截图、分析、点击验证等功能，用于系统性地映射游戏页面。

用法:
    python scripts/explore.py screenshot [--name NAME]     截图并保存
    python scripts/explore.py click X Y [--verify]         点击坐标，可选验证
    python scripts/explore.py info                         显示窗口和截图信息
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from loguru import logger

# 添加 src 到 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
from anime_game_afk.core.session import GameSession


# 截图保存的最大宽度（用于展示/上传到 Claude）
# 800px 宽度 + JPEG 压缩，确保每张 < 200KB，避免 20MB 上下文限制
MAX_DISPLAY_WIDTH = 800


def create_session() -> GameSession:
    """创建并连接游戏会话"""
    session = GameSession(AETHER_GAZER_CONFIG)
    session.connect()
    return session


def save_screenshot(
    img: np.ndarray,
    path: Path,
    *,
    resize_for_display: bool = True,
) -> Path:
    """保存截图，自动缩小以避免文件过大

    Args:
        img: BGR 格式的 numpy 数组
        path: 保存路径
        resize_for_display: 是否缩小到展示尺寸

    Returns:
        实际保存的路径
    """
    if resize_for_display:
        h, w = img.shape[:2]
        if w > MAX_DISPLAY_WIDTH:
            scale = MAX_DISPLAY_WIDTH / w
            img = cv2.resize(
                img,
                (MAX_DISPLAY_WIDTH, int(h * scale)),
                interpolation=cv2.INTER_AREA,
            )
            logger.info("缩放截图: {}x{} -> {}x{}", w, h, img.shape[1], img.shape[0])

    path.parent.mkdir(parents=True, exist_ok=True)

    # 对展示用图片使用 JPEG 格式，大幅减小文件体积
    # PNG raw 用于分析精度，JPEG display 用于上传到 Claude
    if resize_for_display and path.suffix.lower() == ".png":
        jpg_path = path.with_suffix(".jpg")
        cv2.imwrite(str(jpg_path), img, [cv2.IMWRITE_JPEG_QUALITY, 70])
        file_size = jpg_path.stat().st_size
        logger.info("截图已保存 (JPEG): {} ({:.1f} KB)", jpg_path, file_size / 1024)
        # 同时保存 PNG 版本作为备份
        cv2.imwrite(str(path), img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        png_size = path.stat().st_size
        logger.info("截图已保存 (PNG): {} ({:.1f} KB)", path, png_size / 1024)
        return jpg_path  # 返回更小的 JPEG 版本
    else:
        cv2.imwrite(str(path), img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        file_size = path.stat().st_size
        logger.info("截图已保存: {} ({:.1f} KB)", path, file_size / 1024)
        return path


def cmd_screenshot(args: argparse.Namespace) -> None:
    """截图命令"""
    session = create_session()
    try:
        img = session.screenshot()
        h, w = img.shape[:2]
        logger.info("原始截图尺寸: {}x{}", w, h)

        # 保存原始尺寸（用于分析）
        name = args.name or f"explore_{int(time.time())}"
        raw_path = Path(f"assets/aether_gazer/screenshots/{name}_raw.png")
        save_screenshot(img, raw_path, resize_for_display=False)

        # 保存缩小版（用于展示/上传）
        display_path = Path(f"assets/aether_gazer/screenshots/{name}.png")
        save_screenshot(img, display_path, resize_for_display=True)

    finally:
        session.disconnect()


def cmd_click(args: argparse.Namespace) -> None:
    """点击命令，可选前后截图验证"""
    session = create_session()
    try:
        x, y = args.x, args.y

        if args.verify:
            # 点击前截图
            before = session.screenshot()
            before_path = Path(f"assets/aether_gazer/screenshots/click_before.png")
            save_screenshot(before, before_path)

        logger.info("点击坐标: ({}, {})", x, y)
        session.click(x, y)

        if args.verify:
            time.sleep(args.wait)
            # 点击后截图
            after = session.screenshot()
            after_path = Path(f"assets/aether_gazer/screenshots/click_after.png")
            save_screenshot(after, after_path)

            # 标记点击位置
            marked = before.copy()
            h, w = marked.shape[:2]
            if w > MAX_DISPLAY_WIDTH:
                scale = MAX_DISPLAY_WIDTH / w
                marked = cv2.resize(
                    marked,
                    (MAX_DISPLAY_WIDTH, int(h * scale)),
                    interpolation=cv2.INTER_AREA,
                )
                # 缩放标记坐标
                mx, my = int(x * scale), int(y * scale)
            else:
                mx, my = x, y

            cv2.circle(marked, (mx, my), 15, (0, 0, 255), 3)
            cv2.circle(marked, (mx, my), 3, (0, 0, 255), -1)
            cv2.putText(
                marked,
                f"({x},{y})",
                (mx + 20, my - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2,
            )
            marked_path = Path(f"assets/aether_gazer/screenshots/click_marked.png")
            cv2.imwrite(str(marked_path), marked, [cv2.IMWRITE_PNG_COMPRESSION, 9])
            logger.info("标记图已保存: {}", marked_path)

    finally:
        session.disconnect()


def cmd_info(args: argparse.Namespace) -> None:
    """显示窗口和截图信息"""
    session = create_session()
    try:
        # 获取分辨率信息
        resolution = session._controller.resolution
        logger.info("窗口分辨率 (MaaFw resolution): {}", resolution)

        # 截图并检查尺寸
        img = session.screenshot()
        h, w = img.shape[:2]
        logger.info("截图尺寸: {}x{}", w, h)
        logger.info("截图与窗口分辨率一致: {}", (w, h) == resolution)

        # 内存大小
        mem_mb = img.nbytes / (1024 * 1024)
        logger.info("截图内存大小: {:.1f} MB", mem_mb)

        # 配置信息
        logger.info("配置:")
        logger.info("  screencap_method: {}", AETHER_GAZER_CONFIG.screencap_method)
        logger.info("  mouse_method: {}", AETHER_GAZER_CONFIG.mouse_method)
        logger.info("  keyboard_method: {}", AETHER_GAZER_CONFIG.keyboard_method)

    finally:
        session.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description="游戏页面探索工具")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # screenshot
    p_ss = sub.add_parser("screenshot", aliases=["ss"], help="截图")
    p_ss.add_argument("--name", "-n", help="截图文件名前缀")

    # click
    p_click = sub.add_parser("click", help="点击坐标")
    p_click.add_argument("x", type=int, help="X 坐标")
    p_click.add_argument("y", type=int, help="Y 坐标")
    p_click.add_argument("--verify", "-v", action="store_true", help="前后截图验证")
    p_click.add_argument("--wait", "-w", type=float, default=1.0, help="点击后等待秒数")

    # info
    sub.add_parser("info", help="显示窗口和截图信息")

    args = parser.parse_args()

    if args.cmd in ("screenshot", "ss"):
        cmd_screenshot(args)
    elif args.cmd == "click":
        cmd_click(args)
    elif args.cmd == "info":
        cmd_info(args)


if __name__ == "__main__":
    main()
