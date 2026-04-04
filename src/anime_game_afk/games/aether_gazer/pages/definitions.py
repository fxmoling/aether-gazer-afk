"""页面定义和识别系统

每个页面由以下属性定义:
1. page_id — 唯一标识符
2. stable_texts — 稳定文字列表(用于识别)
3. text_regions — 在哪些区域查找文字
4. nav_from_hub — 从主大厅如何到达
5. back_to_hub — 如何返回主大厅
6. interactive_elements — 可交互元素坐标
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import NamedTuple


class Coord(NamedTuple):
    """屏幕坐标 (1600x900)"""
    x: int
    y: int


class Region(NamedTuple):
    """屏幕区域 (x1, y1, x2, y2)"""
    x1: int
    y1: int
    x2: int
    y2: int


class NavMethod(Enum):
    """导航方法"""
    CLICK = "click"
    KEY = "key"
    ESC = "esc"


class TextReliability(Enum):
    """文字可靠性"""
    STABLE = "stable"      # 不随版本变化，可用于识别
    FLAKY = "flaky"        # 随活动/版本变化，不可用于识别


@dataclass(frozen=True)
class NavAction:
    """导航动作"""
    method: NavMethod
    coord: Coord | None = None   # CLICK 时使用
    key_code: int | None = None  # KEY 时使用
    wait_after: float = 1.5      # 动作后等待秒数


@dataclass(frozen=True)
class InteractiveElement:
    """可交互元素"""
    name: str
    name_en: str
    coord: Coord
    action: str = ""          # 描述这个元素做什么
    target_page: str = ""     # 点击后跳转到的页面ID
    safe: bool = True         # 是否安全（不消耗资源）


@dataclass(frozen=True)
class TextFeature:
    """文字特征 — 用于页面识别"""
    text: str
    region: Region              # 期望出现的区域
    reliability: TextReliability = TextReliability.STABLE


@dataclass(frozen=True)
class PageDef:
    """页面定义"""
    page_id: str
    name: str
    name_en: str

    # 从hub导航到此页面
    nav_from_hub: NavAction | None = None
    # 从此页面返回hub
    back_to_hub: NavAction | None = None

    # 页面识别文字 (仅 STABLE 的)
    stable_texts: tuple[TextFeature, ...] = ()

    # 可交互元素
    elements: tuple[InteractiveElement, ...] = ()

    # 是否安全（可自由操作）
    safe: bool = True
    # 是否是叠加层（overlay on hub）
    is_overlay: bool = False

    # 父页面ID
    parent_page: str = "main_hub"


# ============================================================
# 常用区域定义
# ============================================================

# 底部导航栏区域
BOTTOM_NAV_REGION = Region(600, 820, 1550, 880)
# 顶部栏
TOP_BAR_REGION = Region(0, 0, 1600, 80)
# 左侧面板
LEFT_PANEL_REGION = Region(0, 80, 200, 800)
# 标题区域 (左上)
TITLE_REGION = Region(30, 10, 400, 60)
# 右侧面板
RIGHT_PANEL_REGION = Region(1100, 80, 1600, 600)
# 中央区域
CENTER_REGION = Region(200, 80, 1400, 800)


# ============================================================
# VK Codes
# ============================================================

VK_ESCAPE = 0x1B
VK_TAB = 0x09
VK_J = 0x4A
VK_G = 0x47
VK_H = 0x48


# ============================================================
# 页面定义
# ============================================================

MAIN_HUB = PageDef(
    page_id="main_hub",
    name="主大厅",
    name_en="Main Hub",
    nav_from_hub=None,  # 已经在hub
    back_to_hub=None,
    stable_texts=(
        TextFeature("修正者", BOTTOM_NAV_REGION),
        TextFeature("探测", BOTTOM_NAV_REGION),
        TextFeature("商店", BOTTOM_NAV_REGION),
        TextFeature("公会", BOTTOM_NAV_REGION),
        TextFeature("仓库", BOTTOM_NAV_REGION),
        TextFeature("游园街", BOTTOM_NAV_REGION),
        TextFeature("前往作战", BOTTOM_NAV_REGION),
    ),
    elements=(
        InteractiveElement("修正者", "Character", Coord(675, 850), "角色管理", "character"),
        InteractiveElement("探测", "Gacha", Coord(790, 850), "抽卡", "gacha", safe=False),
        InteractiveElement("商店", "Shop", Coord(910, 850), "商店", "shop"),
        InteractiveElement("公会", "Guild", Coord(1025, 850), "矩阵公会", "guild"),
        InteractiveElement("仓库", "Inventory", Coord(1140, 850), "仓库", "inventory", safe=False),
        InteractiveElement("游园街", "Amusement", Coord(1257, 850), "游园街", "amusement"),
        InteractiveElement("前往作战", "Battle", Coord(1465, 850), "作战选择", "battle_select"),
        InteractiveElement("对策协议", "Tactics", Coord(100, 170), "对策协议", "tactics"),
        InteractiveElement("进修企划", "Training", Coord(100, 260), "进修企划", "training"),
        InteractiveElement("入职活动", "Events", Coord(100, 370), "入职活动", "events"),
        InteractiveElement("头像", "Avatar", Coord(50, 40), "玩家信息", "player_info"),
    ),
    parent_page="",
)

CHARACTER = PageDef(
    page_id="character",
    name="修正者",
    name_en="Character",
    nav_from_hub=NavAction(NavMethod.CLICK, Coord(675, 850), wait_after=2.0),
    back_to_hub=NavAction(NavMethod.CLICK, Coord(35, 35), wait_after=1.5),
    stable_texts=(
        TextFeature("属性", LEFT_PANEL_REGION),
        TextFeature("技能", LEFT_PANEL_REGION),
        TextFeature("权钥", LEFT_PANEL_REGION),
        TextFeature("刻印", LEFT_PANEL_REGION),
        TextFeature("战力指数", RIGHT_PANEL_REGION),
    ),
    elements=(
        InteractiveElement("返回", "Back", Coord(35, 35), "返回主大厅", "main_hub"),
        InteractiveElement("属性", "Properties", Coord(100, 100), "属性面板"),
        InteractiveElement("技能", "Skills", Coord(100, 160), "技能面板"),
        InteractiveElement("权钥", "Keys", Coord(100, 220), "权钥面板"),
        InteractiveElement("刻印", "Engravings", Coord(100, 280), "刻印面板"),
        InteractiveElement("跃迁", "Ascension", Coord(100, 340), "跃迁面板"),
        InteractiveElement("神格", "Divinity", Coord(100, 400), "神格面板"),
        InteractiveElement("芯片", "Chips", Coord(100, 460), "芯片面板"),
        InteractiveElement("培养攻略", "Guide", Coord(200, 870), "培养攻略"),
        InteractiveElement("超越", "Transcend", Coord(680, 870), "超越系统"),
        InteractiveElement("突破", "Breakthrough", Coord(810, 870), "突破升级"),
    ),
)

GACHA = PageDef(
    page_id="gacha",
    name="探测",
    name_en="Gacha",
    nav_from_hub=NavAction(NavMethod.CLICK, Coord(790, 850), wait_after=2.0),
    back_to_hub=NavAction(NavMethod.ESC, wait_after=1.5),
    stable_texts=(
        TextFeature("协议锚定探测", LEFT_PANEL_REGION),
        TextFeature("修正者标准探测", LEFT_PANEL_REGION),
        TextFeature("钥从探测", LEFT_PANEL_REGION),
        TextFeature("探测一次", Region(1200, 850, 1500, 890)),
        TextFeature("探测十次", Region(1400, 850, 1600, 890)),
    ),
    elements=(
        InteractiveElement("返回", "Back", Coord(35, 35), "返回主大厅", "main_hub"),
        # 所有其他元素标记为不安全
    ),
    safe=False,
)

SHOP = PageDef(
    page_id="shop",
    name="商店",
    name_en="Shop",
    nav_from_hub=NavAction(NavMethod.CLICK, Coord(910, 850), wait_after=2.0),
    back_to_hub=NavAction(NavMethod.CLICK, Coord(35, 35), wait_after=1.5),
    stable_texts=(
        TextFeature("交易区", Region(0, 800, 400, 900)),
        TextFeature("补给区", Region(200, 800, 600, 900)),
        TextFeature("前往查看", Region(1200, 850, 1600, 900)),
    ),
    elements=(
        InteractiveElement("返回", "Back", Coord(35, 35), "返回主大厅", "main_hub"),
        InteractiveElement("交易区", "Trade", Coord(170, 860), "交易区商品"),
        InteractiveElement("补给区", "Supply", Coord(350, 860), "补给区商品"),
        InteractiveElement("前往查看", "View", Coord(1450, 870), "查看当前活动商品"),
    ),
)

GUILD = PageDef(
    page_id="guild",
    name="公会",
    name_en="Guild",
    nav_from_hub=NavAction(NavMethod.CLICK, Coord(1025, 850), wait_after=2.0),
    back_to_hub=NavAction(NavMethod.CLICK, Coord(35, 35), wait_after=1.5),
    stable_texts=(
        TextFeature("矩阵公会", TITLE_REGION),
        TextFeature("公会成员", BOTTOM_NAV_REGION),
        TextFeature("矩阵供应", BOTTOM_NAV_REGION),
        TextFeature("公会任务", BOTTOM_NAV_REGION),
        TextFeature("矩阵补给", BOTTOM_NAV_REGION),
    ),
    elements=(
        InteractiveElement("返回", "Back", Coord(35, 35), "返回主大厅", "main_hub"),
        InteractiveElement("公会成员", "Members", Coord(920, 870), "查看成员"),
        InteractiveElement("矩阵供应", "Supply", Coord(1080, 870), "矩阵供应"),
        InteractiveElement("公会任务", "Tasks", Coord(1240, 870), "公会任务"),
        InteractiveElement("矩阵补给", "Rewards", Coord(1430, 870), "矩阵补给"),
    ),
)

INVENTORY = PageDef(
    page_id="inventory",
    name="仓库",
    name_en="Inventory",
    nav_from_hub=NavAction(NavMethod.CLICK, Coord(1140, 850), wait_after=2.0),
    back_to_hub=NavAction(NavMethod.CLICK, Coord(35, 35), wait_after=1.5),
    stable_texts=(
        TextFeature("材料", LEFT_PANEL_REGION),
        TextFeature("情报", LEFT_PANEL_REGION),
        TextFeature("刻印", LEFT_PANEL_REGION),
        TextFeature("礼物", LEFT_PANEL_REGION),
        TextFeature("回忆", LEFT_PANEL_REGION),
    ),
    elements=(
        InteractiveElement("返回", "Back", Coord(35, 35), "返回主大厅", "main_hub"),
        # 不列出物品操作按钮 — 不安全
    ),
    safe=False,
)

AMUSEMENT = PageDef(
    page_id="amusement",
    name="游园街",
    name_en="Amusement Street",
    nav_from_hub=NavAction(NavMethod.CLICK, Coord(1257, 850), wait_after=2.0),
    back_to_hub=NavAction(NavMethod.CLICK, Coord(48, 48), wait_after=1.5),
    stable_texts=(
        TextFeature("导航", Region(0, 700, 200, 850)),
        TextFeature("游园任务", Region(900, 830, 1200, 890)),
        TextFeature("游园街面板", Region(1100, 830, 1400, 890)),
        TextFeature("参观", Region(1350, 830, 1550, 890)),
        TextFeature("大厅", CENTER_REGION),
    ),
    elements=(
        InteractiveElement("返回", "Back", Coord(48, 48), "返回主大厅", "main_hub"),
        InteractiveElement("导航", "Navigate", Coord(100, 780), "导航系统"),
        InteractiveElement("入住", "Move In", Coord(660, 770), "角色入住"),
        InteractiveElement("游园任务", "Tasks", Coord(1080, 860), "游园任务"),
        InteractiveElement("游园街面板", "Panel", Coord(1260, 860), "面板管理"),
        InteractiveElement("参观", "Visit", Coord(1430, 860), "参观宿舍"),
    ),
)

BATTLE_SELECT = PageDef(
    page_id="battle_select",
    name="作战选择",
    name_en="Battle Select",
    nav_from_hub=NavAction(NavMethod.CLICK, Coord(1465, 850), wait_after=2.0),
    back_to_hub=NavAction(NavMethod.CLICK, Coord(35, 35), wait_after=1.5),
    stable_texts=(
        TextFeature("情报", Region(100, 830, 300, 890)),
        TextFeature("常驻", Region(280, 830, 450, 890)),
        TextFeature("物资", Region(440, 830, 620, 890)),
        TextFeature("刻印", Region(600, 830, 780, 890)),
        TextFeature("挑战", Region(780, 830, 960, 890)),
        TextFeature("主线剧情", Region(0, 200, 300, 500)),
    ),
    elements=(
        InteractiveElement("返回", "Back", Coord(35, 35), "返回主大厅", "main_hub"),
        InteractiveElement("情报", "Intel", Coord(195, 860), "情报(活动)"),
        InteractiveElement("常驻", "Permanent", Coord(360, 860), "常驻关卡"),
        InteractiveElement("物资", "Resources", Coord(530, 860), "物资关卡"),
        InteractiveElement("刻印", "Engravings", Coord(700, 860), "刻印关卡"),
        InteractiveElement("挑战", "Challenge", Coord(870, 860), "挑战关卡"),
    ),
)

DAILY_TASKS = PageDef(
    page_id="daily_tasks",
    name="每日任务",
    name_en="Daily Tasks",
    nav_from_hub=NavAction(NavMethod.KEY, key_code=VK_G, wait_after=2.0),
    back_to_hub=NavAction(NavMethod.ESC, wait_after=1.5),
    stable_texts=(
        TextFeature("每日任务", LEFT_PANEL_REGION),
        TextFeature("周常任务", LEFT_PANEL_REGION),
        TextFeature("剧情任务", LEFT_PANEL_REGION),
        TextFeature("每日评分", Region(100, 60, 400, 100)),
    ),
    elements=(
        InteractiveElement("返回", "Back", Coord(35, 35), "返回主大厅", "main_hub"),
        InteractiveElement("每日任务", "Daily", Coord(80, 95), "每日任务标签"),
        InteractiveElement("周常任务", "Weekly", Coord(80, 155), "周常任务标签"),
        InteractiveElement("剧情任务", "Story", Coord(80, 210), "剧情任务标签"),
        InteractiveElement("弥弥观测站", "Observatory", Coord(110, 820), "弥弥观测站"),
    ),
)

MAIL = PageDef(
    page_id="mail",
    name="邮件",
    name_en="Mail",
    nav_from_hub=NavAction(NavMethod.KEY, key_code=VK_H, wait_after=2.0),
    back_to_hub=NavAction(NavMethod.ESC, wait_after=1.5),
    stable_texts=(
        TextFeature("邮件", Region(0, 30, 200, 80)),
        TextFeature("收藏栏", Region(100, 30, 300, 80)),
        TextFeature("修正者信件", Region(0, 800, 250, 870)),
    ),
    elements=(
        InteractiveElement("返回", "Back", Coord(35, 35), "返回主大厅", "main_hub"),
        InteractiveElement("修正者信件", "Modifier Mail", Coord(110, 830), "修正者信件"),
        InteractiveElement("收藏", "Favorite", Coord(420, 830), "收藏邮件"),
    ),
)

SETTINGS_PANEL = PageDef(
    page_id="settings_panel",
    name="设置面板",
    name_en="Settings Panel",
    nav_from_hub=NavAction(NavMethod.KEY, key_code=VK_TAB, wait_after=2.0),
    back_to_hub=NavAction(NavMethod.ESC, wait_after=1.5),
    stable_texts=(
        TextFeature("钥从", RIGHT_PANEL_REGION),
        TextFeature("管理员", RIGHT_PANEL_REGION),
        TextFeature("图鉴", RIGHT_PANEL_REGION),
        TextFeature("成就", RIGHT_PANEL_REGION),
        TextFeature("签到", RIGHT_PANEL_REGION),
        TextFeature("设置", Region(1200, 540, 1400, 600)),
        TextFeature("用户中心", Region(1350, 540, 1550, 600)),
    ),
    elements=(
        InteractiveElement("钥从", "Keys", Coord(1180, 200), "钥从管理"),
        InteractiveElement("管理员", "Manager", Coord(1320, 200), "管理员系统"),
        InteractiveElement("图鉴", "Collection", Coord(1460, 200), "图鉴"),
        InteractiveElement("成就", "Achievements", Coord(1180, 300), "成就系统"),
        InteractiveElement("弥弥观测站", "Observatory", Coord(1320, 300), "弥弥观测站"),
        InteractiveElement("心链事件", "Heart Chain", Coord(1460, 300), "心链事件"),
        InteractiveElement("好友", "Friends", Coord(1180, 400), "好友列表"),
        InteractiveElement("签到", "Check-in", Coord(1320, 400), "每日签到"),
        InteractiveElement("公告", "Announcements", Coord(1460, 400), "游戏公告"),
        InteractiveElement("设置", "Settings", Coord(1290, 570), "设置"),
        InteractiveElement("用户中心", "User Center", Coord(1440, 570), "用户中心"),
    ),
    is_overlay=True,
)

TACTICS = PageDef(
    page_id="tactics",
    name="对策协议",
    name_en="Tactics Protocol",
    nav_from_hub=NavAction(NavMethod.CLICK, Coord(100, 170), wait_after=2.0),
    back_to_hub=NavAction(NavMethod.CLICK, Coord(35, 35), wait_after=1.5),
    stable_texts=(
        TextFeature("基础合约", CENTER_REGION),
        TextFeature("进阶合约", CENTER_REGION),
        TextFeature("购买等级", Region(1300, 80, 1600, 130)),
        TextFeature("经验值", Region(200, 80, 600, 120)),
    ),
    elements=(
        InteractiveElement("返回", "Back", Coord(35, 35), "返回主大厅", "main_hub"),
        InteractiveElement("任务", "Tasks", Coord(120, 870), "对策协议任务"),
        InteractiveElement("商店", "Shop", Coord(280, 870), "对策协议商店"),
    ),
)

TRAINING = PageDef(
    page_id="training",
    name="进修企划",
    name_en="Training Plan",
    nav_from_hub=NavAction(NavMethod.CLICK, Coord(100, 260), wait_after=2.0),
    back_to_hub=NavAction(NavMethod.CLICK, Coord(35, 35), wait_after=1.5),
    stable_texts=(
        TextFeature("外勤演练", LEFT_PANEL_REGION),
        TextFeature("黑区净化", LEFT_PANEL_REGION),
        TextFeature("梦境再构", LEFT_PANEL_REGION),
        TextFeature("多维变量", LEFT_PANEL_REGION),
        TextFeature("协作规划", LEFT_PANEL_REGION),
    ),
    elements=(
        InteractiveElement("返回", "Back", Coord(35, 35), "返回主大厅", "main_hub"),
    ),
)

EVENTS = PageDef(
    page_id="events",
    name="入职活动",
    name_en="Events",
    nav_from_hub=NavAction(NavMethod.CLICK, Coord(100, 370), wait_after=2.0),
    back_to_hub=NavAction(NavMethod.CLICK, Coord(35, 35), wait_after=1.5),
    stable_texts=(
        TextFeature("入职签到", LEFT_PANEL_REGION),
        TextFeature("新人课程", LEFT_PANEL_REGION),
        TextFeature("升级奖励", LEFT_PANEL_REGION),
        TextFeature("日常委托", LEFT_PANEL_REGION),
        TextFeature("完成进度", Region(0, 800, 300, 900)),
    ),
    elements=(
        InteractiveElement("返回", "Back", Coord(35, 35), "返回主大厅", "main_hub"),
        InteractiveElement("入职签到", "Sign-in", Coord(80, 60), "入职签到"),
        InteractiveElement("新人课程", "Course", Coord(80, 130), "新人课程"),
        InteractiveElement("升级奖励", "Level Rewards", Coord(80, 200), "升级奖励"),
        InteractiveElement("日常委托", "Daily Commission", Coord(80, 270), "日常委托"),
    ),
)

PLAYER_INFO = PageDef(
    page_id="player_info",
    name="玩家信息",
    name_en="Player Info",
    nav_from_hub=NavAction(NavMethod.CLICK, Coord(50, 40), wait_after=2.0),
    back_to_hub=NavAction(NavMethod.ESC, wait_after=1.5),
    stable_texts=(
        TextFeature("等级", Region(200, 80, 500, 200)),
        TextFeature("设置标签", Region(200, 150, 500, 200)),
        TextFeature("矩阵公会", Region(200, 280, 500, 330)),
        TextFeature("修正者", Region(200, 400, 400, 470)),
        TextFeature("用户中心", Region(0, 700, 250, 780)),
    ),
    elements=(
        InteractiveElement("用户中心", "User Center", Coord(100, 740), "用户中心"),
    ),
    is_overlay=True,
)

# ============================================================
# 页面注册表
# ============================================================

ALL_PAGES: dict[str, PageDef] = {
    p.page_id: p for p in [
        MAIN_HUB, CHARACTER, GACHA, SHOP, GUILD, INVENTORY,
        AMUSEMENT, BATTLE_SELECT, DAILY_TASKS, MAIL,
        SETTINGS_PANEL, TACTICS, TRAINING, EVENTS, PLAYER_INFO,
    ]
}

# 从hub可直接到达的安全页面
SAFE_PAGES_FROM_HUB: list[str] = [
    pid for pid, p in ALL_PAGES.items()
    if p.safe and p.nav_from_hub is not None
]

# 不安全页面
UNSAFE_PAGES: list[str] = [
    pid for pid, p in ALL_PAGES.items()
    if not p.safe
]
