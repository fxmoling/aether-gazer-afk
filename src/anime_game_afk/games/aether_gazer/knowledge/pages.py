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
# Page definitions — 23 pages, 1600x900 design resolution
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
        # Top bar resources (only visible when UI is active, not idle)
        E("体力", "Stamina", P(850, 35), "stamina_panel"),
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
        E("交易区", "Trade", P(89, 817), "shop_trade"),
        E("补给区", "Supply", P(399, 816), "shop_supply"),
        E("前往查看", "View", P(1450, 870)),
    ),
)

# ── Shop sub-pages (verified coordinates from memory) ──

SHOP_TRADE = PageDef(
    page_id="shop_trade", name="交易区", name_en="Shop Trade",
    elements=(
        E("返回", "Back", P(35, 35), "shop"),
        E("每日采购", "Daily Purchase", P(130, 125), "shop_daily"),
        E("交易中心", "Trade Center", P(130, 225), "shop_trade_center"),
        E("凭证置换", "Voucher Exchange", P(130, 325)),
        E("刻印研发", "Engrave R&D", P(130, 430)),
    ),
    parent_page="shop",
)

SHOP_DAILY = PageDef(
    page_id="shop_daily", name="每日采购", name_en="Shop Daily Purchase",
    # Items here are dynamic (情报, 刻印商品, 物资商品).
    # Use OCR to locate items, not fixed coordinates.
    elements=(
        E("返回", "Back", P(35, 35), "shop"),
        E("刷新", "Refresh", P(210, 850)),
    ),
    parent_page="shop_trade",
)

SHOP_TRADE_CENTER = PageDef(
    page_id="shop_trade_center", name="交易中心", name_en="Shop Trade Center",
    elements=(
        E("返回", "Back", P(35, 35), "shop"),
        E("辉芒商店", "Radiance Shop", P(411, 130)),
        E("合作商店", "Coop Shop", P(643, 130)),
        E("情报兑换", "Intel Exchange", P(874, 130)),
        E("矩阵供应", "Matrix Supply", P(1106, 130)),
        E("同调轨迹", "Sync Track", P(1339, 130)),
    ),
    parent_page="shop_trade",
)

SHOP_SUPPLY = PageDef(
    page_id="shop_supply", name="补给区", name_en="Shop Supply",
    elements=(
        E("返回", "Back", P(35, 35), "shop"),
        E("日常补给", "Daily Supply", P(560, 130), "shop_daily_supply"),
    ),
    parent_page="shop",
    safe=False,  # Contains paid items
)

SHOP_DAILY_SUPPLY = PageDef(
    page_id="shop_daily_supply", name="日常补给", name_en="Shop Daily Supply",
    # Free stamina pack is the leftmost item; position may vary.
    # Use OCR to confirm "免费" or "冷却" text before clicking.
    elements=(
        E("返回", "Back", P(35, 35), "shop"),
        E("免费冷却包", "Free Stamina Pack", P(350, 290)),
    ),
    parent_page="shop_supply",
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
        E("情报", "Intel", P(195, 860), "battle_intel"),
        E("常驻", "Permanent", P(360, 860)),
        E("物资", "Resources", P(530, 860)),
        E("刻印", "Engravings", P(700, 860)),
        E("挑战", "Challenge", P(870, 860)),
    ),
)

# ── Battle sub-pages ──

BATTLE_INTEL = PageDef(
    page_id="battle_intel", name="情报", name_en="Battle Intel",
    elements=(
        E("返回", "Back", P(35, 35), "battle_select"),
        E("主线剧情", "Main Story", P(533, 450), "main_story_map"),
        E("支线", "Side Story", P(1010, 625)),
    ),
    parent_page="battle_select",
)

MAIN_STORY_MAP = PageDef(
    page_id="main_story_map", name="主线地图", name_en="Main Story Map",
    # Stage nodes are dynamic — use OCR/template matching to find them.
    # "准备作战" button is at bottom-right when a node is selected.
    elements=(
        E("返回", "Back", P(35, 35), "battle_intel"),
        E("准备作战", "Prep Battle", P(1350, 840)),
    ),
    parent_page="battle_intel",
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
        E("任务", "Tasks", P(162, 839)),
        E("商店", "Shop", P(379, 839)),
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

# ── Stamina panel (overlay opened from hub top bar) ──

STAMINA_PANEL = PageDef(
    page_id="stamina_panel", name="体力面板", name_en="Stamina Panel",
    # Three tabs with fixed positions (verified 2026-04-05)
    elements=(
        E("冷却剂", "Coolant", P(451, 155)),
        E("移转之辉", "Transfer Light", P(783, 153)),
        E("每日补给", "Daily Supply", P(1113, 154)),
    ),
    is_overlay=True,
    parent_page="main_hub",
)

# ============================================================
# Page registry
# ============================================================

ALL_PAGES: dict[str, PageDef] = {
    p.page_id: p for p in [
        MAIN_HUB, CHARACTER, GACHA,
        SHOP, SHOP_TRADE, SHOP_DAILY, SHOP_TRADE_CENTER,
        SHOP_SUPPLY, SHOP_DAILY_SUPPLY,
        GUILD, INVENTORY, AMUSEMENT,
        BATTLE_SELECT, BATTLE_INTEL, MAIN_STORY_MAP,
        DAILY_TASKS, MAIL,
        SETTINGS_PANEL, TACTICS, TRAINING, EVENTS, PLAYER_INFO,
        STAMINA_PANEL,
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
