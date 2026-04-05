"""裁剪模板图片工具

从 assets/aether_gazer/screenshots/ 下的原始截图中裁剪 UI 元素，
保存到 assets/aether_gazer/resource/image/ 用于 MaaFw 模板匹配。

用法:
    python scripts/crop_templates.py
    python scripts/crop_templates.py --source assets/aether_gazer/screenshots/systematic/page_battle_select.jpg
    python scripts/crop_templates.py --list
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 默认路径
SCREENSHOTS_DIR = PROJECT_ROOT / "assets" / "aether_gazer" / "screenshots"
SYSTEMATIC_DIR = SCREENSHOTS_DIR / "systematic"
PAGES_DIR = SCREENSHOTS_DIR / "pages"
OUTPUT_DIR = PROJECT_ROOT / "assets" / "aether_gazer" / "resource" / "image"


@dataclass(frozen=True)
class CropRegion:
    """裁剪区域定义"""
    name: str           # 输出文件名 (不含扩展名)
    x1: int             # 左上角 x
    y1: int             # 左上角 y
    x2: int             # 右下角 x
    y2: int             # 右下角 y
    source: str         # 源截图文件名 (在 screenshots/ 下的相对路径)
    description: str    # 描述


# ============================================================
# 裁剪区域定义
# 坐标基于 1600x900 分辨率
# ============================================================

# --- 源截图说明 ---
# systematic/raw/*.png — 1600x900 全分辨率原始截图 (explore_systematic.py 生成)
# hub_raw_for_mapping.png — 1600x900 hub 完整截图 (专门为坐标映射拍摄)
# pages/*.jpg — 800x450 缩略图 (不用于裁剪，尺寸太小)

CROP_DEFINITIONS: list[CropRegion] = [
    # === 底部导航栏按钮 (从 hub 1600x900 截图裁剪) ===
    # 每个按钮区域约 100x60 像素，以文字中心为基准
    CropRegion(
        "nav_xiuzhengzhe", 625, 820, 725, 880,
        "hub_raw_for_mapping.png",
        "底部导航 - 修正者按钮",
    ),
    CropRegion(
        "nav_tance", 740, 820, 840, 880,
        "hub_raw_for_mapping.png",
        "底部导航 - 探测按钮",
    ),
    CropRegion(
        "nav_shangdian", 860, 820, 960, 880,
        "hub_raw_for_mapping.png",
        "底部导航 - 商店按钮",
    ),
    CropRegion(
        "nav_gonghui", 975, 820, 1075, 880,
        "hub_raw_for_mapping.png",
        "底部导航 - 公会按钮",
    ),
    CropRegion(
        "nav_cangku", 1090, 820, 1190, 880,
        "hub_raw_for_mapping.png",
        "底部导航 - 仓库按钮",
    ),
    CropRegion(
        "nav_youyuanjie", 1207, 820, 1307, 880,
        "hub_raw_for_mapping.png",
        "底部导航 - 游园街按钮",
    ),
    CropRegion(
        "nav_qianwangzuozhan", 1390, 820, 1540, 880,
        "hub_raw_for_mapping.png",
        "底部导航 - 前往作战按钮",
    ),

    # === 返回按钮 (多个页面都有) ===
    CropRegion(
        "btn_back_arrow", 10, 10, 60, 60,
        "systematic/raw/page_character.png",
        "返回箭头按钮 (大多数页面左上角)",
    ),
    CropRegion(
        "btn_back_arrow_large", 20, 20, 76, 76,
        "systematic/raw/page_amusement.png",
        "返回箭头按钮 (宿舍/游园街较大版本)",
    ),

    # === 作战选择页底部标签 ===
    CropRegion(
        "battle_tab_qingbao", 145, 835, 245, 885,
        "systematic/raw/page_battle_select.png",
        "作战选择 - 情报标签",
    ),
    CropRegion(
        "battle_tab_changzhu", 310, 835, 410, 885,
        "systematic/raw/page_battle_select.png",
        "作战选择 - 常驻标签",
    ),
    CropRegion(
        "battle_tab_wuzi", 480, 835, 580, 885,
        "systematic/raw/page_battle_select.png",
        "作战选择 - 物资标签",
    ),
    CropRegion(
        "battle_tab_keyin", 650, 835, 750, 885,
        "systematic/raw/page_battle_select.png",
        "作战选择 - 刻印标签",
    ),
    CropRegion(
        "battle_tab_tiaozhan", 820, 835, 920, 885,
        "systematic/raw/page_battle_select.png",
        "作战选择 - 挑战标签",
    ),

    # === 设置面板元素 ===
    CropRegion(
        "settings_qiandao", 1270, 370, 1370, 430,
        "systematic/raw/page_settings_panel.png",
        "设置面板 - 签到入口",
    ),

    # === 公会页面元素 ===
    CropRegion(
        "guild_juzhen_buji", 1370, 840, 1500, 890,
        "systematic/raw/page_guild.png",
        "公会 - 矩阵补给按钮",
    ),

    # === 页面识别特征区域 ===
    # 底部导航栏完整条 (用于 hub 识别)
    CropRegion(
        "feature_bottom_nav_bar", 600, 820, 1550, 880,
        "hub_raw_for_mapping.png",
        "主界面底部导航栏完整条 (用于 hub 识别)",
    ),
]


def find_source_image(source_rel: str) -> Path | None:
    """查找源截图文件"""
    path = SCREENSHOTS_DIR / source_rel
    if path.exists():
        return path

    # 尝试不同扩展名
    for ext in [".jpg", ".jpeg", ".png"]:
        alt = path.with_suffix(ext)
        if alt.exists():
            return alt

    return None


def crop_single(
    region: CropRegion,
    output_dir: Path,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> bool:
    """裁剪单个区域

    Returns:
        True if cropped successfully, False otherwise.
    """
    output_path = output_dir / f"{region.name}.png"

    if output_path.exists() and not force:
        print(f"  SKIP {region.name} (already exists, use --force to overwrite)")
        return True

    source_path = find_source_image(region.source)
    if source_path is None:
        print(f"  MISS {region.name} - source not found: {region.source}")
        return False

    if dry_run:
        print(f"  PLAN {region.name} <- {region.source} "
              f"[{region.x1},{region.y1} -> {region.x2},{region.y2}]")
        return True

    # 读取源图
    img = cv2.imread(str(source_path))
    if img is None:
        print(f"  FAIL {region.name} - cannot read: {source_path}")
        return False

    h, w = img.shape[:2]

    # 验证坐标范围
    x1 = max(0, min(region.x1, w))
    y1 = max(0, min(region.y1, h))
    x2 = max(0, min(region.x2, w))
    y2 = max(0, min(region.y2, h))

    if x2 <= x1 or y2 <= y1:
        print(f"  FAIL {region.name} - invalid crop region: "
              f"[{x1},{y1} -> {x2},{y2}] (image: {w}x{h})")
        return False

    cropped = img[y1:y2, x1:x2]

    # 保存为 PNG (MaaFw 模板匹配用 PNG 无损格式)
    cv2.imwrite(str(output_path), cropped)
    crop_h, crop_w = cropped.shape[:2]
    print(f"  OK   {region.name}.png ({crop_w}x{crop_h}px) <- {region.source}")
    return True


def list_definitions() -> None:
    """列出所有裁剪定义"""
    print(f"Total {len(CROP_DEFINITIONS)} crop definitions:\n")
    print(f"{'Name':<30} {'Region':<25} {'Source':<45} Description")
    print("-" * 130)
    for r in CROP_DEFINITIONS:
        region_str = f"[{r.x1},{r.y1} -> {r.x2},{r.y2}]"
        print(f"{r.name:<30} {region_str:<25} {r.source:<45} {r.description}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crop UI template images from game screenshots",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List all crop definitions without processing",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite existing output files",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be done without actually cropping",
    )
    parser.add_argument(
        "--output", type=Path, default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--only", type=str, nargs="*",
        help="Only process these template names (space separated)",
    )
    args = parser.parse_args()

    if args.list:
        list_definitions()
        return

    output_dir: Path = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Output directory: {output_dir}")
    print(f"Screenshots root: {SCREENSHOTS_DIR}")
    print()

    # 过滤定义
    definitions = CROP_DEFINITIONS
    if args.only:
        only_set = set(args.only)
        definitions = [d for d in definitions if d.name in only_set]
        if not definitions:
            print(f"No matching definitions for: {args.only}")
            sys.exit(1)

    success_count = 0
    fail_count = 0
    skip_count = 0

    for region in definitions:
        result = crop_single(
            region, output_dir,
            force=args.force,
            dry_run=args.dry_run,
        )
        if result:
            success_count += 1
        else:
            fail_count += 1

    print(f"\nDone: {success_count} ok, {fail_count} failed")

    if fail_count > 0 and not args.dry_run:
        print("\nNote: Some source screenshots were not found.")
        print("Run explore_systematic.py first to capture page screenshots.")
        sys.exit(1)


if __name__ == "__main__":
    main()
