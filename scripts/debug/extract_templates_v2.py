"""模板提取 + 页面识别器 V2

核心思路: 不裁小文字，而是裁大区域签名(icon+text+bg一起)
用 cv2.matchTemplate TM_CCOEFF_NORMED 匹配

每个签名包含:
- page_id: 所属页面
- name: 签名名称
- crop: (x1,y1,x2,y2) 从原始截图裁剪区域
- search: (x1,y1,x2,y2) 在新截图中搜索的区域(限制范围加速+减少误判)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

RAW_DIR = Path("assets/aether_gazer/screenshots/systematic/raw")
TEMPLATE_DIR = Path("assets/aether_gazer/templates")

# (page_id, screenshot, name, crop_region, search_region)
# crop_region: 从截图中裁出模板 (x1,y1,x2,y2)
# search_region: 匹配时只在这个范围搜索 (x1,y1,x2,y2), None=全图
SIGNATURES = [
    # HUB: 底部导航栏 "修正者 探测 商店 公会 仓库 游园街 前往作战"
    ("main_hub", "hub_initial.png",
     "hub_navbar",
     (620, 825, 1560, 875),    # 整个底部导航栏
     (500, 800, 1600, 900)),   # 搜索范围

    # CHARACTER: 右侧竖排功能图标 (属性/技能/权钥/刻印 旁的圆形icon列)
    ("character", "page_character.png",
     "char_right_icons",
     (185, 82, 240, 460),      # 右侧圆形图标列
     (150, 50, 300, 500)),

    # CHARACTER: 底部栏 "培养攻略 超越 突破"
    ("character", "page_character.png",
     "char_bottom_bar",
     (130, 852, 850, 892),
     (100, 830, 900, 900)),

    # GACHA: 左侧卡池列表 (协议锚定探测, 莫道奈何, 行侠已道...)
    ("gacha", "page_gacha.png",
     "gacha_banner_list",
     (10, 30, 190, 300),
     (0, 0, 250, 400)),

    # SHOP: 底部 "交易区 | 补给区" 标签
    ("shop", "page_shop.png",
     "shop_bottom_tabs",
     (60, 840, 450, 892),
     (0, 810, 500, 900)),

    # GUILD: 左侧公会信息面板头部 "矩阵公会" + 编辑图标
    ("guild", "page_guild.png",
     "guild_info_header",
     (30, 5, 275, 100),
     (0, 0, 350, 150)),

    # GUILD: 底部导航 "公会成员 矩阵供应 公会任务 矩阵补给"
    ("guild", "page_guild.png",
     "guild_bottom_nav",
     (850, 848, 1520, 898),
     (800, 830, 1600, 900)),

    # INVENTORY: 左侧标签 (材料/情报/刻印/礼物/回忆) 带图标
    ("inventory", "page_inventory.png",
     "inv_left_tabs",
     (25, 48, 140, 320),
     (0, 20, 200, 400)),

    # AMUSEMENT: 底部栏 "游园任务 游园街面板 参观"
    ("amusement", "page_amusement.png",
     "amuse_bottom_bar",
     (1020, 845, 1500, 898),
     (900, 820, 1600, 900)),

    # BATTLE SELECT: 底部标签栏 "情报 常驻 物资 刻印 挑战" 含图标
    ("battle_select", "page_battle_select.png",
     "battle_tab_bar",
     (110, 835, 920, 900),
     (50, 810, 1000, 900)),

    # DAILY TASKS: 左侧标签 "每日任务/周常任务/剧情任务" + 图标
    ("daily_tasks", "page_daily_tasks.png",
     "daily_left_tabs",
     (5, 58, 210, 230),
     (0, 30, 260, 280)),

    # DAILY TASKS: 评分进度条区域
    ("daily_tasks", "page_daily_tasks.png",
     "daily_score_bar",
     (95, 55, 780, 100),
     (50, 30, 850, 130)),

    # MAIL: 标题区域 "邮件 21/100 收藏栏 0/30"
    ("mail", "page_mail.png",
     "mail_header",
     (28, 28, 235, 88),
     (0, 0, 300, 120)),

    # SETTINGS PANEL: 右侧3x3功能图标网格 (钥从/管理员/图鉴/成就/弥弥观测站/心链事件)
    ("settings_panel", "page_settings_panel.png",
     "settings_grid",
     (1100, 170, 1530, 470),
     (1000, 100, 1600, 550)),

    # TACTICS: 等级+经验条 区域
    ("tactics", "page_tactics.png",
     "tactics_level_bar",
     (145, 82, 600, 135),
     (100, 50, 700, 170)),

    # TACTICS: 基础合约/进阶合约 标签
    ("tactics", "page_tactics.png",
     "tactics_contract_labels",
     (170, 225, 330, 420),
     (100, 180, 400, 480)),

    # TRAINING: 左侧标签列表 — 包含 '>' 展开符号区域 (独有!)
    # 与 daily_tasks 区分: training 有 '>' 符号 + 竖排模式名, daily 有图标+文字
    ("training", "page_training.png",
     "training_left_tabs",
     (0, 35, 180, 350),
     (0, 10, 220, 400)),

    # TRAINING: 右侧任务列表含 reward icons (crystal+coin) — 独有布局
    ("training", "page_training.png",
     "training_reward_area",
     (600, 80, 810, 380),
     (500, 50, 900, 420)),

    # EVENTS: 左侧标签 (入职签到/新人课程/升级奖励/日常委托)
    ("events", "page_events.png",
     "events_left_tabs",
     (5, 30, 175, 290),
     (0, 10, 220, 350)),

    # PLAYER INFO: 收藏进度条 (修正者53%/钥从21%/贴纸15%/成就43%)
    ("player_info", "page_player_info.png",
     "player_collection_stats",
     (175, 388, 575, 475),
     (100, 350, 650, 520)),
]


def extract_all() -> dict:
    """提取所有签名模板"""
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    index = {}

    for page_id, screenshot, name, crop, search in SIGNATURES:
        img_path = RAW_DIR / screenshot
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"MISSING: {img_path}")
            continue

        x1, y1, x2, y2 = crop
        template = img[y1:y2, x1:x2]
        if template.size == 0:
            print(f"EMPTY CROP: {name}")
            continue

        out_path = TEMPLATE_DIR / f"{page_id}__{name}.png"
        cv2.imwrite(str(out_path), template, [cv2.IMWRITE_PNG_COMPRESSION, 9])

        th, tw = template.shape[:2]
        if page_id not in index:
            index[page_id] = []
        index[page_id].append({
            "name": name,
            "path": str(out_path),
            "size": [tw, th],
            "crop": list(crop),
            "search": list(search) if search else None,
        })
        print(f"  {page_id:18s} {name:30s} {tw}x{th}")

    # 保存索引
    idx_path = TEMPLATE_DIR / "index.json"
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in index.values())
    print(f"\nTotal: {total} templates for {len(index)} pages")
    return index


if __name__ == "__main__":
    extract_all()
