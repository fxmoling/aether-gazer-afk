"""Page definitions for AetherGazer.

Pure data — coordinates, element names, page metadata.
No cv2, no device, no vision imports allowed.
All coordinates are in 1600x900 design resolution.
"""
from __future__ import annotations

from dataclasses import dataclass

from anime_game_afk.core.types import Point


@dataclass(frozen=True)
class PageElement:
    """Clickable element on a page."""
    name: str          # Chinese display name
    name_en: str       # English name (used as lookup key)
    coord: Point       # Click position (design resolution)
    target_page: str = ""   # Page ID navigated to when clicked
    safe: bool = True       # False = may cost resources


@dataclass(frozen=True)
class PageDef:
    """Complete page definition."""
    page_id: str
    name: str          # Chinese name
    name_en: str       # English name
    elements: tuple[PageElement, ...] = ()
    safe: bool = True
    is_overlay: bool = False
    parent_page: str = "main_hub"


# Helper to reduce repetition
P = Point
E = PageElement

# ============================================================
# Page definitions — 15 pages, 1600x900 design resolution
# ============================================================

MAIN_HUB = PageDef(
    page_id="main_hub", name="主大厅", name_en="Main Hub",
    elements=(
        E("修正者", "Character", P(675, 850), "character"),
        E("探测", "Gacha", P(790, 850), "gacha", safe=False),
        E("商店", "Shop", P(910, 850), "shop"),
        E("公会", "Guild", P(1025, 850), "guild"),
        E("仓库", "Inventory", P(1140, 850), "inventory", safe=False),
        E("游园街", "Amusement", P(1257, 850), "amusement"),
        E("前往作战", "Battle", P(1465, 850), "battle_select"),
        E("对策协议", "Tactics", P(100, 170), "tactics"),
        E("进修企划", "Training", P(100, 260), "training"),
        E("入职活动", "Events", P(100, 370), "events"),
        E("头像", "Avatar", P(50, 40), "player_info"),
    ),
    parent_page="",
)

CHARACTER = PageDef(
    page_id="character", name="修正者", name_en="Character",
    elements=(
        E("返回", "Back", P(35, 35), "main_hub"),
        E("属性", "Properties", P(100, 100)),
        E("技能", "Skills", P(100, 160)),
        E("权钥", "Keys", P(100, 220)),
        E("刻印", "Engravings", P(100, 280)),
        E("跃迁", "Ascension", P(100, 340)),
        E("神格", "Divinity", P(100, 400)),
        E("芯片", "Chips", P(100, 460)),
        E("培养攻略", "Guide", P(200, 870)),
        E("超越", "Transcend", P(680, 870)),
        E("突破", "Breakthrough", P(810, 870)),
    ),
)

GACHA = PageDef(
    page_id="gacha", name="探测", name_en="Gacha",
    elements=(
        E("返回", "Back", P(35, 35), "main_hub"),
    ),
    safe=False,
)

SHOP = PageDef(
    page_id="shop", name="商店", name_en="Shop",
    elements=(
        E("返回", "Back", P(35, 35), "main_hub"),
        E("交易区", "Trade", P(170, 860)),
        E("补给区", "Supply", P(350, 860)),
        E("前往查看", "View", P(1450, 870)),
    ),
)

GUILD = PageDef(
    page_id="guild", name="公会", name_en="Guild",
    elements=(
        E("返回", "Back", P(35, 35), "main_hub"),
        E("公会成员", "Members", P(920, 870)),
        E("矩阵供应", "Supply", P(1080, 870)),
        E("公会任务", "Tasks", P(1240, 870)),
        E("矩阵补给", "Rewards", P(1430, 870)),
    ),
)

INVENTORY = PageDef(
    page_id="inventory", name="仓库", name_en="Inventory",
    elements=(
        E("返回", "Back", P(35, 35), "main_hub"),
    ),
    safe=False,
)

AMUSEMENT = PageDef(
    page_id="amusement", name="游园街", name_en="Amusement Street",
    elements=(
        E("返回", "Back", P(48, 48), "main_hub"),
        E("导航", "Navigate", P(100, 780)),
        E("入住", "Move In", P(660, 770)),
        E("游园任务", "Tasks", P(1080, 860)),
        E("游园街面板", "Panel", P(1260, 860)),
        E("参观", "Visit", P(1430, 860)),
    ),
)

BATTLE_SELECT = PageDef(
    page_id="battle_select", name="作战选择", name_en="Battle Select",
    elements=(
        E("返回", "Back", P(35, 35), "main_hub"),
        E("情报", "Intel", P(195, 860)),
        E("常驻", "Permanent", P(360, 860)),
        E("物资", "Resources", P(530, 860)),
        E("刻印", "Engravings", P(700, 860)),
        E("挑战", "Challenge", P(870, 860)),
    ),
)

DAILY_TASKS = PageDef(
    page_id="daily_tasks", name="每日任务", name_en="Daily Tasks",
    elements=(
        E("返回", "Back", P(35, 35), "main_hub"),
        E("每日任务", "Daily", P(80, 95)),
        E("周常任务", "Weekly", P(80, 155)),
        E("剧情任务", "Story", P(80, 210)),
        E("弥弥观测站", "Observatory", P(110, 820)),
    ),
)

MAIL = PageDef(
    page_id="mail", name="邮件", name_en="Mail",
    elements=(
        E("返回", "Back", P(35, 35), "main_hub"),
        E("修正者信件", "Modifier Mail", P(110, 830)),
        E("收藏", "Favorite", P(420, 830)),
    ),
)

SETTINGS_PANEL = PageDef(
    page_id="settings_panel", name="设置面板", name_en="Settings Panel",
    elements=(
        E("钥从", "Keys", P(1180, 200)),
        E("管理员", "Manager", P(1320, 200)),
        E("图鉴", "Collection", P(1460, 200)),
        E("成就", "Achievements", P(1180, 300)),
        E("弥弥观测站", "Observatory", P(1320, 300)),
        E("心链事件", "Heart Chain", P(1460, 300)),
        E("好友", "Friends", P(1180, 400)),
        E("签到", "Check-in", P(1320, 400)),
        E("公告", "Announcements", P(1460, 400)),
        E("设置", "Settings", P(1290, 570)),
        E("用户中心", "User Center", P(1440, 570)),
    ),
    is_overlay=True,
)

TACTICS = PageDef(
    page_id="tactics", name="对策协议", name_en="Tactics Protocol",
    elements=(
        E("返回", "Back", P(35, 35), "main_hub"),
        E("任务", "Tasks", P(120, 870)),
        E("商店", "Shop", P(280, 870)),
    ),
)

TRAINING = PageDef(
    page_id="training", name="进修企划", name_en="Training Plan",
    elements=(
        E("返回", "Back", P(35, 35), "main_hub"),
    ),
)

EVENTS = PageDef(
    page_id="events", name="入职活动", name_en="Events",
    elements=(
        E("返回", "Back", P(35, 35), "main_hub"),
        E("入职签到", "Sign-in", P(80, 60)),
        E("新人课程", "Course", P(80, 130)),
        E("升级奖励", "Level Rewards", P(80, 200)),
        E("日常委托", "Daily Commission", P(80, 270)),
    ),
)

PLAYER_INFO = PageDef(
    page_id="player_info", name="玩家信息", name_en="Player Info",
    elements=(
        E("用户中心", "User Center", P(100, 740)),
    ),
    is_overlay=True,
)

# ============================================================
# Page registry
# ============================================================

ALL_PAGES: dict[str, PageDef] = {
    p.page_id: p for p in [
        MAIN_HUB, CHARACTER, GACHA, SHOP, GUILD, INVENTORY,
        AMUSEMENT, BATTLE_SELECT, DAILY_TASKS, MAIL,
        SETTINGS_PANEL, TACTICS, TRAINING, EVENTS, PLAYER_INFO,
    ]
}

# Pages safely reachable from hub (have nav action and are safe)
SAFE_PAGES: tuple[str, ...] = tuple(
    pid for pid, p in ALL_PAGES.items()
    if p.safe and pid != "main_hub"
)

# Pages marked unsafe (may cost resources)
UNSAFE_PAGES: tuple[str, ...] = tuple(
    pid for pid, p in ALL_PAGES.items()
    if not p.safe
)


def get_page(page_id: str) -> PageDef | None:
    """Look up a page by ID. Returns None if not found."""
    return ALL_PAGES.get(page_id)


def find_element(page_id: str, element_name_en: str) -> PageElement | None:
    """Find an element by English name within a page."""
    page = ALL_PAGES.get(page_id)
    if page is None:
        return None
    for elem in page.elements:
        if elem.name_en == element_name_en:
            return elem
    return None
