"""Page definitions for AetherGazer.

Pure data — coordinates, element names, page metadata.
No cv2, no device, no vision imports allowed.
All coordinates are fractional [0.0, 1.0].
"""
from __future__ import annotations

from dataclasses import dataclass



@dataclass(frozen=True)
class PageElement:
    """Clickable element on a page."""
    name: str          # Chinese display name
    name_en: str       # English name (used as lookup key)
    coord: tuple[float, float]       # Fractional (fx, fy) click position
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
E = PageElement

# ============================================================
# Page definitions — 23 pages, fractional coordinates
# ============================================================

MAIN_HUB = PageDef(
    page_id="main_hub", name="主大厅", name_en="Main Hub",
    elements=(
        E("修正者", "Character", (0.422, 0.944), "character"),
        E("探测", "Gacha", (0.494, 0.944), "gacha", safe=False),
        E("商店", "Shop", (0.569, 0.944), "shop"),
        E("公会", "Guild", (0.641, 0.944), "guild"),
        E("仓库", "Inventory", (0.713, 0.944), "inventory", safe=False),
        E("游园街", "Amusement", (0.786, 0.944), "amusement"),
        E("前往作战", "Battle", (0.916, 0.944), "battle_select"),
        E("对策协议", "Tactics", (0.062, 0.189), "tactics"),
        E("进修企划", "Training", (0.062, 0.289), "training"),
        E("入职活动", "Events", (0.062, 0.411), "events"),
        E("头像", "Avatar", (0.031, 0.044), "player_info"),
        # Top bar resources (only visible when UI is active, not idle)
        E("体力", "Stamina", (0.531, 0.039), "stamina_panel"),
    ),
    parent_page="",
)

CHARACTER = PageDef(
    page_id="character", name="修正者", name_en="Character",
    elements=(
        E("返回", "Back", (0.022, 0.039), "main_hub"),
        E("属性", "Properties", (0.062, 0.111)),
        E("技能", "Skills", (0.062, 0.178)),
        E("权钥", "Keys", (0.062, 0.244)),
        E("刻印", "Engravings", (0.062, 0.311)),
        E("跃迁", "Ascension", (0.062, 0.378)),
        E("神格", "Divinity", (0.062, 0.444)),
        E("芯片", "Chips", (0.062, 0.511)),
        E("培养攻略", "Guide", (0.125, 0.967)),
        E("超越", "Transcend", (0.425, 0.967)),
        E("突破", "Breakthrough", (0.506, 0.967)),
    ),
)

GACHA = PageDef(
    page_id="gacha", name="探测", name_en="Gacha",
    elements=(
        E("返回", "Back", (0.022, 0.039), "main_hub"),
    ),
    safe=False,
)

SHOP = PageDef(
    page_id="shop", name="商店", name_en="Shop",
    elements=(
        E("返回", "Back", (0.022, 0.039), "main_hub"),
        E("交易区", "Trade", (0.056, 0.908), "shop_trade"),
        E("补给区", "Supply", (0.249, 0.907), "shop_supply"),
        E("前往查看", "View", (0.906, 0.967)),
    ),
)

# ── Shop sub-pages (verified coordinates from memory) ──

SHOP_TRADE = PageDef(
    page_id="shop_trade", name="交易区", name_en="Shop Trade",
    elements=(
        E("返回", "Back", (0.022, 0.039), "shop"),
        E("每日采购", "Daily Purchase", (0.081, 0.139), "shop_daily"),
        E("交易中心", "Trade Center", (0.081, 0.25), "shop_trade_center"),
        E("凭证置换", "Voucher Exchange", (0.081, 0.361)),
        E("刻印研发", "Engrave R&D", (0.081, 0.478)),
    ),
    parent_page="shop",
)

SHOP_DAILY = PageDef(
    page_id="shop_daily", name="每日采购", name_en="Shop Daily Purchase",
    # Items here are dynamic (情报, 刻印商品, 物资商品).
    # Use OCR to locate items, not fixed coordinates.
    elements=(
        E("返回", "Back", (0.022, 0.039), "shop"),
        E("刷新", "Refresh", (0.131, 0.944)),
    ),
    parent_page="shop_trade",
)

SHOP_TRADE_CENTER = PageDef(
    page_id="shop_trade_center", name="交易中心", name_en="Shop Trade Center",
    elements=(
        E("返回", "Back", (0.022, 0.039), "shop"),
        E("辉芒商店", "Radiance Shop", (0.257, 0.144)),
        E("合作商店", "Coop Shop", (0.402, 0.144)),
        E("情报兑换", "Intel Exchange", (0.546, 0.144)),
        E("矩阵供应", "Matrix Supply", (0.691, 0.144)),
        E("同调轨迹", "Sync Track", (0.837, 0.144)),
    ),
    parent_page="shop_trade",
)

SHOP_SUPPLY = PageDef(
    page_id="shop_supply", name="补给区", name_en="Shop Supply",
    elements=(
        E("返回", "Back", (0.022, 0.039), "shop"),
        E("日常补给", "Daily Supply", (0.35, 0.144), "shop_daily_supply"),
    ),
    parent_page="shop",
    safe=False,  # Contains paid items
)

SHOP_DAILY_SUPPLY = PageDef(
    page_id="shop_daily_supply", name="日常补给", name_en="Shop Daily Supply",
    # Free stamina pack is the leftmost item; position may vary.
    # Use OCR to confirm "免费" or "冷却" text before clicking.
    elements=(
        E("返回", "Back", (0.022, 0.039), "shop"),
        E("免费冷却包", "Free Stamina Pack", (0.219, 0.322)),
    ),
    parent_page="shop_supply",
)

GUILD = PageDef(
    page_id="guild", name="公会", name_en="Guild",
    elements=(
        E("返回", "Back", (0.022, 0.039), "main_hub"),
        E("公会成员", "Members", (0.575, 0.967)),
        E("矩阵供应", "Supply", (0.675, 0.967)),
        E("公会任务", "Tasks", (0.775, 0.967)),
        E("矩阵补给", "Rewards", (0.894, 0.967)),
    ),
)

INVENTORY = PageDef(
    page_id="inventory", name="仓库", name_en="Inventory",
    elements=(
        E("返回", "Back", (0.022, 0.039), "main_hub"),
    ),
    safe=False,
)

AMUSEMENT = PageDef(
    page_id="amusement", name="游园街", name_en="Amusement Street",
    elements=(
        E("返回", "Back", (0.03, 0.053), "main_hub"),
        E("导航", "Navigate", (0.062, 0.867)),
        E("入住", "Move In", (0.412, 0.856)),
        E("游园任务", "Tasks", (0.675, 0.956)),
        E("游园街面板", "Panel", (0.787, 0.956)),
        E("参观", "Visit", (0.894, 0.956)),
    ),
)

BATTLE_SELECT = PageDef(
    page_id="battle_select", name="作战选择", name_en="Battle Select",
    elements=(
        E("返回", "Back", (0.022, 0.039), "main_hub"),
        E("情报", "Intel", (0.122, 0.956), "battle_intel"),
        E("常驻", "Permanent", (0.225, 0.956)),
        E("物资", "Resources", (0.331, 0.956)),
        E("刻印", "Engravings", (0.438, 0.956)),
        E("挑战", "Challenge", (0.544, 0.956)),
    ),
)

# ── Battle sub-pages ──

BATTLE_INTEL = PageDef(
    page_id="battle_intel", name="情报", name_en="Battle Intel",
    elements=(
        E("返回", "Back", (0.022, 0.039), "battle_select"),
        E("主线剧情", "Main Story", (0.333, 0.5), "main_story_map"),
        E("支线", "Side Story", (0.631, 0.694)),
    ),
    parent_page="battle_select",
)

MAIN_STORY_MAP = PageDef(
    page_id="main_story_map", name="主线地图", name_en="Main Story Map",
    # Stage nodes are dynamic — use OCR/template matching to find them.
    # "准备作战" button is at bottom-right when a node is selected.
    elements=(
        E("返回", "Back", (0.022, 0.039), "battle_intel"),
        E("准备作战", "Prep Battle", (0.844, 0.933)),
    ),
    parent_page="battle_intel",
)

DAILY_TASKS = PageDef(
    page_id="daily_tasks", name="每日任务", name_en="Daily Tasks",
    elements=(
        E("返回", "Back", (0.022, 0.039), "main_hub"),
        E("每日任务", "Daily", (0.05, 0.106)),
        E("周常任务", "Weekly", (0.05, 0.172)),
        E("剧情任务", "Story", (0.05, 0.233)),
        E("弥弥观测站", "Observatory", (0.069, 0.911)),
    ),
)

MAIL = PageDef(
    page_id="mail", name="邮件", name_en="Mail",
    elements=(
        E("返回", "Back", (0.022, 0.039), "main_hub"),
        E("修正者信件", "Modifier Mail", (0.069, 0.922)),
        E("收藏", "Favorite", (0.263, 0.922)),
    ),
)

SETTINGS_PANEL = PageDef(
    page_id="settings_panel", name="设置面板", name_en="Settings Panel",
    elements=(
        E("钥从", "Keys", (0.738, 0.222)),
        E("管理员", "Manager", (0.825, 0.222)),
        E("图鉴", "Collection", (0.912, 0.222)),
        E("成就", "Achievements", (0.738, 0.333)),
        E("弥弥观测站", "Observatory", (0.825, 0.333)),
        E("心链事件", "Heart Chain", (0.912, 0.333)),
        E("好友", "Friends", (0.738, 0.444)),
        E("签到", "Check-in", (0.825, 0.444)),
        E("公告", "Announcements", (0.912, 0.444)),
        E("设置", "Settings", (0.806, 0.633)),
        E("用户中心", "User Center", (0.9, 0.633)),
    ),
    is_overlay=True,
)

TACTICS = PageDef(
    page_id="tactics", name="对策协议", name_en="Tactics Protocol",
    elements=(
        E("返回", "Back", (0.022, 0.039), "main_hub"),
        E("任务", "Tasks", (0.101, 0.932)),
        E("商店", "Shop", (0.237, 0.932)),
    ),
)

TRAINING = PageDef(
    page_id="training", name="进修企划", name_en="Training Plan",
    elements=(
        E("返回", "Back", (0.022, 0.039), "main_hub"),
    ),
)

EVENTS = PageDef(
    page_id="events", name="入职活动", name_en="Events",
    elements=(
        E("返回", "Back", (0.022, 0.039), "main_hub"),
        E("入职签到", "Sign-in", (0.05, 0.067)),
        E("新人课程", "Course", (0.05, 0.144)),
        E("升级奖励", "Level Rewards", (0.05, 0.222)),
        E("日常委托", "Daily Commission", (0.05, 0.3)),
    ),
)

PLAYER_INFO = PageDef(
    page_id="player_info", name="玩家信息", name_en="Player Info",
    elements=(
        E("用户中心", "User Center", (0.062, 0.822)),
    ),
    is_overlay=True,
)

# ── Stamina panel (overlay opened from hub top bar) ──

STAMINA_PANEL = PageDef(
    page_id="stamina_panel", name="体力面板", name_en="Stamina Panel",
    # Three tabs with fixed positions (verified 2026-04-05)
    elements=(
        E("冷却剂", "Coolant", (0.282, 0.172)),
        E("移转之辉", "Transfer Light", (0.489, 0.17)),
        E("每日补给", "Daily Supply", (0.696, 0.171)),
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
