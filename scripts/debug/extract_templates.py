"""从原始截图中提取稳定文字区域作为模板

对每个已知页面，从原始截图裁剪出关键文字区域，
保存为小模板图片供 matchTemplate 使用。

模板选择原则:
1. 只选 STABLE 文字 (不随版本/活动变化)
2. 优先选区分度高的文字 (不要选多个页面共有的)
3. 每个页面 2-3 个模板足够
4. 裁剪区域要紧凑，留最少背景

用法:
    python scripts/extract_templates.py           # 提取所有模板
    python scripts/extract_templates.py --show    # 显示裁剪区域但不保存
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

RAW_DIR = Path("assets/aether_gazer/screenshots/systematic/raw")
TEMPLATE_DIR = Path("assets/aether_gazer/templates")

# ============================================================
# 模板定义: (page_id, screenshot_file, template_name, crop_region)
# crop_region = (x1, y1, x2, y2) in 1600x900 coordinates
#
# 选择标准:
# - 文字必须是 STABLE 的（游戏系统文字，不随活动变化）
# - 背景最好是纯色或半透明，不要选复杂背景上的文字
# - 区分度高：此文字只在该页面出现
# ============================================================

TEMPLATE_DEFS = [
    # All coordinates from pixel scanning (brightness > threshold)
    # Format: (page_id, screenshot_file, template_name, (x1, y1, x2, y2))

    # === MAIN HUB (底部导航栏 — hub独有) ===
    ("main_hub", "hub_initial.png", "nav_xiuzhengzhe", (639, 841, 710, 865)),     # 修正者
    ("main_hub", "hub_initial.png", "nav_shangdian", (884, 828, 932, 865)),        # 商店
    ("main_hub", "hub_initial.png", "nav_qianwangzuozhan", (1392, 828, 1541, 871)),  # 前往作战

    # === CHARACTER (属性/技能标签栏 — 独有组合) ===
    ("character", "page_character.png", "tab_shuxing", (48, 78, 172, 122)),       # 属性
    ("character", "page_character.png", "tab_jineng", (48, 138, 172, 182)),       # 技能
    ("character", "page_character.png", "tab_quanyue", (48, 198, 172, 242)),      # 权钥
    ("character", "page_character.png", "label_zhanli", (648, 158, 792, 202)),    # 战力指数

    # === GACHA (探测页面 — 独有) ===
    ("gacha", "page_gacha.png", "banner_xieyimaoding", (53, 36, 178, 64)),        # 协议锚定探测
    ("gacha", "page_gacha.png", "btn_tanceyici", (1288, 876, 1418, 896)),         # 探测一次

    # === SHOP (交易区/补给区 — 底部独有标签) ===
    # 这些标签背景深色，用低阈值扫描
    ("shop", "page_shop.png", "tab_jiaoyiqu", (83, 848, 190, 882)),              # 交易区
    ("shop", "page_shop.png", "tab_bujiqu", (258, 848, 360, 882)),               # 补给区

    # === GUILD (矩阵公会标题 + 底部栏) ===
    ("guild", "page_guild.png", "title_juzhen", (38, 8, 222, 57)),               # 矩阵公会
    ("guild", "page_guild.png", "nav_gonghui_chengyuan", (862, 855, 972, 890)),   # 公会成员
    ("guild", "page_guild.png", "nav_juzhen_gongying", (1010, 855, 1140, 890)),   # 矩阵供应

    # === INVENTORY (左侧标签 — 独有组合) ===
    ("inventory", "page_inventory.png", "tab_cailiao", (33, 54, 132, 102)),       # 材料
    ("inventory", "page_inventory.png", "tab_qingbao", (33, 124, 132, 170)),      # 情报
    ("inventory", "page_inventory.png", "tab_liwu", (33, 263, 132, 312)),         # 礼物

    # === AMUSEMENT (底部栏 — 独有) ===
    ("amusement", "page_amusement.png", "nav_youyuanjie_mianban", (1172, 850, 1352, 892)), # 游园街面板
    ("amusement", "page_amusement.png", "nav_canguan", (1380, 875, 1418, 892)),   # 参观

    # === BATTLE SELECT (底部标签栏 — 独有组合) ===
    ("battle_select", "page_battle_select.png", "tab_qingbao_battle", (138, 843, 242, 892)), # 情报
    ("battle_select", "page_battle_select.png", "tab_changzhu", (288, 843, 402, 892)),       # 常驻
    ("battle_select", "page_battle_select.png", "tab_wuzi", (438, 843, 572, 892)),            # 物资
    ("battle_select", "page_battle_select.png", "tab_tiaozhan", (788, 843, 902, 892)),        # 挑战

    # === DAILY TASKS (左侧标签 — 独有组合) ===
    ("daily_tasks", "page_daily_tasks.png", "tab_meirirenwu", (13, 68, 152, 117)),     # 每日任务
    ("daily_tasks", "page_daily_tasks.png", "tab_zhouchangrenwu", (13, 128, 152, 177)),# 周常任务
    ("daily_tasks", "page_daily_tasks.png", "label_meiri_pingfen", (98, 60, 242, 98)), # 每日评分

    # === MAIL (标题 — 独有) ===
    ("mail", "page_mail.png", "label_youjian", (38, 34, 122, 80)),                # 邮件
    ("mail", "page_mail.png", "label_shoucanglan", (118, 34, 222, 80)),            # 收藏栏

    # === SETTINGS PANEL (右侧功能网格 — 独有) ===
    ("settings_panel", "page_settings_panel.png", "grid_yuecong", (1155, 208, 1211, 253)),    # 钥从
    ("settings_panel", "page_settings_panel.png", "grid_guanliyuan", (1305, 208, 1363, 248)), # 管理员
    ("settings_panel", "page_settings_panel.png", "grid_tujian", (1457, 208, 1502, 245)),     # 图鉴
    ("settings_panel", "page_settings_panel.png", "grid_qiandao", (1279, 398, 1362, 450)),    # 签到

    # === TACTICS (合约标签 — 独有) ===
    ("tactics", "page_tactics.png", "label_jichu_heyue", (178, 228, 322, 272)),    # 基础合约
    ("tactics", "page_tactics.png", "label_jinjie_heyue", (178, 373, 322, 417)),   # 进阶合约

    # === TRAINING (左侧标签 — 独有组合) ===
    ("training", "page_training.png", "tab_waiqin_yanlian", (18, 42, 172, 92)),    # 外勤演练
    ("training", "page_training.png", "tab_heiqu_jinghua", (18, 86, 172, 134)),    # 黑区净化

    # === EVENTS (左侧标签 — 独有组合) ===
    ("events", "page_events.png", "tab_ruzhi_qiandao", (13, 38, 162, 86)),        # 入职签到
    ("events", "page_events.png", "tab_xinren_kecheng", (13, 98, 162, 146)),       # 新人课程

    # === PLAYER INFO (特征文字) ===
    ("player_info", "page_player_info.png", "label_shezhi_biaoqian", (213, 176, 362, 220)), # 设置标签
]


def extract_templates(show_only: bool = False) -> None:
    """从原始截图中裁剪模板"""
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    errors = []

    for page_id, screenshot, tpl_name, (x1, y1, x2, y2) in TEMPLATE_DEFS:
        img_path = RAW_DIR / screenshot
        if not img_path.exists():
            errors.append(f"截图不存在: {img_path}")
            continue

        img = cv2.imread(str(img_path))
        if img is None:
            errors.append(f"无法读取: {img_path}")
            continue

        h, w = img.shape[:2]
        # 边界检查
        x1c = max(0, min(x1, w))
        y1c = max(0, min(y1, h))
        x2c = max(0, min(x2, w))
        y2c = max(0, min(y2, h))

        crop = img[y1c:y2c, x1c:x2c]
        if crop.size == 0:
            errors.append(f"裁剪区域为空: {tpl_name} ({x1},{y1},{x2},{y2})")
            continue

        ch, cw = crop.shape[:2]

        if show_only:
            print(f"  {page_id:20s} {tpl_name:35s} ({x1},{y1})-({x2},{y2}) = {cw}x{ch}")
            continue

        # 保存模板
        tpl_path = TEMPLATE_DIR / page_id / f"{tpl_name}.png"
        tpl_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(tpl_path), crop, [cv2.IMWRITE_PNG_COMPRESSION, 9])

        if page_id not in results:
            results[page_id] = []
        results[page_id].append({
            "name": tpl_name,
            "path": str(tpl_path),
            "size": f"{cw}x{ch}",
            "crop": [x1, y1, x2, y2],
        })

    if show_only:
        return

    # 保存模板索引
    index_path = TEMPLATE_DIR / "template_index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 统计
    total = sum(len(v) for v in results.values())
    print(f"\n提取完成: {total} 个模板, {len(results)} 个页面")
    print(f"模板目录: {TEMPLATE_DIR}")
    print(f"索引文件: {index_path}")

    if errors:
        print(f"\n错误 ({len(errors)}):")
        for e in errors:
            print(f"  {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="模板提取")
    parser.add_argument("--show", action="store_true", help="仅显示裁剪区域")
    args = parser.parse_args()
    extract_templates(show_only=args.show)


if __name__ == "__main__":
    main()
