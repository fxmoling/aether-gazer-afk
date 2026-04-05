"""深度页面探索 V2 — 进入子页面的子页面

一级: hub → 各页面
二级: 各页面 → 其子标签/子面板
每步截图保存为原始PNG + 小JPEG

安全规则:
- gacha: 只截图，不操作，立即退出
- inventory: 只截图表面，不点击物品
- 不点击任何 "购买"/"使用"/"探测" 按钮

用法:
    python scripts/explore_deep.py                # 完整深度探索
    python scripts/explore_deep.py --page X       # 只探索某页面
    python scripts/explore_deep.py --level1-only  # 只做一级探索
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
from anime_game_afk.core.session import GameSession

# === 输出目录 ===
OUT_DIR = Path("assets/aether_gazer/screenshots/deep")
RAW_DIR = OUT_DIR / "raw"
JPEG_QUALITY = 65
DISPLAY_WIDTH = 800

# === VK Codes ===
VK_ESC = 0x1B
VK_TAB = 0x09
VK_G = 0x47
VK_H = 0x48
VK_J = 0x4A


def save(img: np.ndarray, name: str) -> tuple[Path, Path]:
    """保存 raw PNG + 小 JPEG"""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = RAW_DIR / f"{name}.png"
    cv2.imwrite(str(raw_path), img, [cv2.IMWRITE_PNG_COMPRESSION, 9])

    h, w = img.shape[:2]
    if w > DISPLAY_WIDTH:
        scale = DISPLAY_WIDTH / w
        small = cv2.resize(img, (DISPLAY_WIDTH, int(h * scale)), interpolation=cv2.INTER_AREA)
    else:
        small = img
    jpg_path = OUT_DIR / f"{name}.jpg"
    cv2.imwrite(str(jpg_path), small, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])

    return raw_path, jpg_path


class DeepExplorer:
    def __init__(self, session: GameSession):
        self.s = session
        self.results = {}

    def click(self, x: int, y: int, wait: float = 1.5):
        self.s.click(x, y)
        time.sleep(wait)

    def key(self, code: int, wait: float = 1.5):
        self.s.press_key(code)
        time.sleep(wait)

    def screenshot(self, name: str) -> np.ndarray:
        img = self.s.screenshot()
        raw_p, jpg_p = save(img, name)
        self.results[name] = {"raw": str(raw_p), "jpg": str(jpg_p)}
        logger.info("截图: {} ({}x{})", name, img.shape[1], img.shape[0])
        return img

    def wake(self):
        """唤醒UI"""
        self.click(800, 450, 0.5)

    def back_click(self, wait: float = 1.5):
        """点击左上角返回"""
        self.click(35, 35, wait)

    def back_esc(self, wait: float = 1.5):
        """ESC返回"""
        self.key(VK_ESC, wait)

    def ensure_hub(self):
        """确保在hub"""
        for _ in range(5):
            self.wake()
            time.sleep(0.3)
            img = self.s.screenshot()
            # 检查底部导航栏
            bright_count = 0
            for y in range(835, 865):
                for x in range(650, 1500, 10):
                    px = img[y, x]
                    if int(px[0]) + int(px[1]) + int(px[2]) > 550:
                        bright_count += 1
            if bright_count > 50:
                logger.info("已在hub")
                return True
            self.back_esc(1.0)
        return False

    def explore_hub(self):
        """截图hub"""
        self.ensure_hub()
        self.wake()
        time.sleep(0.5)
        self.screenshot("L0_hub")

    def explore_character(self):
        """修正者页面 — 进入各子标签"""
        self.ensure_hub()
        self.wake()
        self.click(675, 850, 2.0)  # 修正者
        self.screenshot("L1_character")

        # 子标签: 右侧圆形图标从上到下
        # 属性(默认) → 技能 → 权钥 → 刻印 → 跃迁 → 神格 → 芯片
        tabs = [
            ("shuxing", 210, 100),   # 属性 (默认选中)
            ("jineng", 210, 162),    # 技能
            ("quanyue", 210, 222),   # 权钥
            ("keyin", 210, 282),     # 刻印
            ("yuechian", 210, 342),  # 跃迁
            ("shenge", 210, 402),    # 神格
            ("xinpian", 210, 462),   # 芯片
        ]
        for tab_name, x, y in tabs:
            self.click(x, y, 1.0)
            self.screenshot(f"L2_character_{tab_name}")

        self.back_click()

    def explore_gacha(self):
        """探测页面 — 只截图，不操作"""
        self.ensure_hub()
        self.wake()
        self.click(790, 850, 2.0)  # 探测
        self.screenshot("L1_gacha")
        # 不做任何子页面操作，立即退出
        self.back_esc()

    def explore_shop(self):
        """商店页面"""
        self.ensure_hub()
        self.wake()
        self.click(910, 850, 2.0)  # 商店
        self.screenshot("L1_shop")

        # 底部标签: 交易区 / 补给区
        self.click(170, 860, 1.5)  # 交易区
        self.screenshot("L2_shop_trade")
        self.click(350, 860, 1.5)  # 补给区
        self.screenshot("L2_shop_supply")

        self.back_click()

    def explore_guild(self):
        """公会页面"""
        self.ensure_hub()
        self.wake()
        self.click(1025, 850, 2.0)  # 公会
        self.screenshot("L1_guild")

        # 底部标签: 公会成员 / 矩阵供应 / 公会任务 / 矩阵补给
        for name, x in [("members", 920), ("supply", 1080), ("tasks", 1240), ("rewards", 1430)]:
            self.click(x, 870, 1.5)
            self.screenshot(f"L2_guild_{name}")

        self.back_click()

    def explore_inventory(self):
        """仓库 — 只浏览标签，不点击物品"""
        self.ensure_hub()
        self.wake()
        self.click(1140, 850, 2.0)  # 仓库
        self.screenshot("L1_inventory")

        # 左侧标签: 材料/情报/刻印/礼物/回忆
        for name, y in [("cailiao", 75), ("qingbao", 148), ("keyin", 220), ("liwu", 290), ("huiyi", 360)]:
            self.click(80, y, 1.0)
            self.screenshot(f"L2_inventory_{name}")

        self.back_click()

    def explore_amusement(self):
        """游园街"""
        self.ensure_hub()
        self.wake()
        self.click(1257, 850, 2.0)  # 游园街
        self.screenshot("L1_amusement")

        # 底部: 游园任务 / 游园街面板 / 参观
        for name, x in [("tasks", 1080), ("panel", 1260), ("visit", 1430)]:
            self.click(x, 860, 1.5)
            self.screenshot(f"L2_amusement_{name}")
            self.back_esc(1.0)  # 子面板可能是弹窗

        # 回hub (游园街返回键在48,48)
        self.click(48, 48, 1.5)

    def explore_battle_select(self):
        """作战选择 — 进入各标签"""
        self.ensure_hub()
        self.wake()
        self.click(1465, 850, 2.0)  # 前往作战
        self.screenshot("L1_battle_select")

        # 底部标签: 情报/常驻/物资/刻印/挑战
        for name, x in [("intel", 195), ("permanent", 360), ("resource", 530), ("engrave", 700), ("challenge", 870)]:
            self.click(x, 860, 1.5)
            self.screenshot(f"L2_battle_{name}")

        self.back_click()

    def explore_daily_tasks(self):
        """每日任务"""
        self.ensure_hub()
        self.wake()
        self.key(VK_G, 2.0)  # G键
        self.screenshot("L1_daily_tasks")

        # 左侧标签: 每日任务/周常任务/剧情任务
        for name, y in [("daily", 95), ("weekly", 155), ("story", 210)]:
            self.click(80, y, 1.0)
            self.screenshot(f"L2_daily_{name}")

        self.back_esc()

    def explore_mail(self):
        """邮件"""
        self.ensure_hub()
        self.wake()
        self.key(VK_H, 2.0)  # H键
        self.screenshot("L1_mail")

        # 点击修正者信件标签
        self.click(110, 830, 1.5)
        self.screenshot("L2_mail_modifier")

        self.back_esc()

    def explore_settings_panel(self):
        """设置面板 — 进入各子功能"""
        self.ensure_hub()
        self.wake()
        self.key(VK_TAB, 2.0)  # Tab键
        self.screenshot("L1_settings_panel")

        # 右侧网格: 钥从/管理员/图鉴/成就/弥弥观测站/心链事件/好友/签到/公告
        grid_items = [
            ("yuecong", 1180, 200),
            ("guanliyuan", 1320, 200),
            ("tujian", 1460, 200),
            ("chengjiu", 1180, 300),
            ("mimi", 1320, 300),
            ("xinlian", 1460, 300),
            ("haoyou", 1180, 400),
            ("qiandao", 1320, 400),
            ("gonggao", 1460, 400),
        ]
        for name, x, y in grid_items:
            self.click(x, y, 2.0)
            self.screenshot(f"L2_settings_{name}")
            # 返回设置面板 — 大部分子页面用ESC或返回按钮
            self.back_esc(1.0)
            # 重新打开设置面板
            self.key(VK_TAB, 1.5)

        # 最后关闭设置面板
        self.back_esc()

    def explore_tactics(self):
        """对策协议"""
        self.ensure_hub()
        self.wake()
        self.click(100, 170, 2.0)  # 对策协议
        self.screenshot("L1_tactics")

        # 底部标签: 任务 / 商店
        self.click(120, 870, 1.5)  # 任务
        self.screenshot("L2_tactics_tasks")
        self.click(280, 870, 1.5)  # 商店
        self.screenshot("L2_tactics_shop")

        self.back_click()

    def explore_training(self):
        """进修企划"""
        self.ensure_hub()
        self.wake()
        self.click(100, 260, 2.0)  # 进修企划
        self.screenshot("L1_training")

        # 左侧标签
        tabs = [
            ("waiqin", 90, 65),
            ("heiqu", 90, 110),
            ("mengjing", 90, 155),
            ("duowei", 90, 200),
            ("yinguo", 90, 245),
            ("lizhan", 90, 290),
            ("lianhe", 90, 335),
            ("xiezuo", 90, 380),
        ]
        for name, x, y in tabs:
            self.click(x, y, 1.0)
            self.screenshot(f"L2_training_{name}")

        self.back_click()

    def explore_events(self):
        """入职活动"""
        self.ensure_hub()
        self.wake()
        self.click(100, 370, 2.0)  # 入职活动
        self.screenshot("L1_events")

        # 左侧标签
        for name, y in [("signup", 60), ("course", 130), ("levelup", 200), ("commission", 270)]:
            self.click(80, y, 1.0)
            self.screenshot(f"L2_events_{name}")

        self.back_click()

    def explore_player_info(self):
        """玩家信息"""
        self.ensure_hub()
        self.wake()
        self.click(50, 40, 2.0)  # 头像
        self.screenshot("L1_player_info")
        self.back_esc()

    def run_all(self, pages: list[str] | None = None):
        """执行全部探索"""
        all_explorers = {
            "hub": self.explore_hub,
            "character": self.explore_character,
            "gacha": self.explore_gacha,
            "shop": self.explore_shop,
            "guild": self.explore_guild,
            "inventory": self.explore_inventory,
            "amusement": self.explore_amusement,
            "battle_select": self.explore_battle_select,
            "daily_tasks": self.explore_daily_tasks,
            "mail": self.explore_mail,
            "settings_panel": self.explore_settings_panel,
            "tactics": self.explore_tactics,
            "training": self.explore_training,
            "events": self.explore_events,
            "player_info": self.explore_player_info,
        }

        targets = {k: v for k, v in all_explorers.items() if pages is None or k in pages}
        total = len(targets)

        for idx, (name, func) in enumerate(targets.items(), 1):
            logger.info("\n=== [{}/{}] 探索: {} ===", idx, total, name)
            try:
                func()
                logger.info("OK: {}", name)
            except Exception as e:
                logger.error("FAIL: {} - {}", name, e)
                # 尝试恢复
                for _ in range(3):
                    self.back_esc(1.0)
                self.ensure_hub()

            # 保存中间结果
            self._save_results()

        self._save_results()
        logger.info("\n=== 探索完成: {} 张截图 ===", len(self.results))

    def _save_results(self):
        results_path = OUT_DIR / "results.json"
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="深度页面探索")
    parser.add_argument("--page", "-p", nargs="+", help="只探索指定页面")
    parser.add_argument("--level1-only", action="store_true", help="只做一级探索")
    args = parser.parse_args()

    session = GameSession(AETHER_GAZER_CONFIG)
    session.connect()

    try:
        explorer = DeepExplorer(session)
        if args.level1_only:
            # 只截一级页面
            explorer.run_all(pages=args.page)
        else:
            explorer.run_all(pages=args.page)
    finally:
        session.disconnect()


if __name__ == "__main__":
    main()
