# Wave 2: Game Knowledge & Atomic Ops (Layers 4-5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement task-by-task.

**Goal:** Build game-specific data models (Layer 4) and atomic operations (Layer 5). Migrate existing `definitions.py`, `template_identifier.py`, `atomic.py`, and `navigator.py` into the new layered structure.

**Dependencies:** Wave 1 complete (core/types.py, core/device.py, vision/matcher.py, runtime/logger.py exist).

**Architecture:** Layer 4 is pure data — ZERO imports of cv2/device/vision. Layer 5 ops each do ONE thing, return OpResult, never call other ops. Composition is Layer 6's job.

**Tech Stack:** Python 3.11, opencv-python, numpy, loguru (via runtime.logger)

---

## Task 1: Knowledge — constants.py, keys.py, resources.py

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/knowledge/__init__.py`
- Create: `src/anime_game_afk/games/aether_gazer/knowledge/constants.py`
- Create: `src/anime_game_afk/games/aether_gazer/knowledge/keys.py`
- Create: `src/anime_game_afk/games/aether_gazer/knowledge/resources.py`
- Create: `src/anime_game_afk/games/aether_gazer/knowledge/README.md`
- Test: `tests/games/aether_gazer/knowledge/test_keys.py`

**Purpose:** Foundational constants, all VK codes, and asset paths. No complex data structures — just values.

- [ ] Step 1: Create `knowledge/` directory with empty `__init__.py`
- [ ] Step 2: Create `constants.py` with design resolution, thresholds, timing defaults
- [ ] Step 3: Create `keys.py` with all VK codes grouped by context
- [ ] Step 4: Create `resources.py` with template directory paths and state template metadata
- [ ] Step 5: Create `README.md` for knowledge/
- [ ] Step 6: Write test verifying key groups and constants
- [ ] Step 7: Run tests, commit

**constants.py:**
```python
"""Game constants for AetherGazer.

Design resolution, match thresholds, timing defaults.
Pure values — no imports of cv2, device, or vision.
"""
from anime_game_afk.core.types import Resolution

# Design coordinate system — all coordinates use this resolution
DESIGN_RESOLUTION = Resolution(width=1600, height=900)

# Screen center — used for wake-up clicks and idle dismissal
SCREEN_CENTER_X = 800
SCREEN_CENTER_Y = 450

# Back button — top-left corner, shared by most pages
BACK_BUTTON_X = 35
BACK_BUTTON_Y = 35

# Template matching thresholds
MATCH_THRESHOLD = 0.65
HIGH_CONFIDENCE = 0.80

# Timing defaults (seconds)
CLICK_WAIT = 1.0
NAV_WAIT = 1.5
PAGE_LOAD_WAIT = 2.0
BATTLE_KEY_INTERVAL = 0.25
WALK_DEFAULT_DURATION = 2.0

# Game mechanics
STAMINA_CAP = 200

# Unknown state rotation phases (cycle_position -> action)
UNKNOWN_ROTATION = {
    "space": (0, 5),
    "attack": (5, 10),
    "walk": (10, 20),
    "esc_enter": (20, 25),
}
```

**keys.py:**
```python
"""Virtual key code constants for AetherGazer.

All VK codes used by the game, organized by context.
Pure values — no imports of cv2, device, or vision.
"""

# --- UI Navigation ---
VK_ESCAPE = 0x1B
VK_ENTER = 0x0D
VK_TAB = 0x09
VK_SPACE = 0x20

# --- Hub shortcuts (press from main hub to open panel) ---
VK_G = 0x47       # Daily tasks panel
VK_H = 0x48       # Mail panel
VK_J_HUB = 0x4A   # Battle select (same physical key as attack J)

# --- Battle attack keys ---
VK_J = 0x4A       # Normal attack
VK_U = 0x55       # Skill 1
VK_I = 0x49       # Skill 2
VK_O = 0x4F       # Skill 3
VK_R = 0x52       # Ultimate

VK_1 = 0x31       # Combo 1 / QTE
VK_2 = 0x32       # Combo 2 / QTE

# --- Movement (WASD) ---
VK_W = 0x57       # Forward
VK_A = 0x41       # Left
VK_S = 0x53       # Backward
VK_D = 0x44       # Right

# --- Attack rotation sequence ---
# One full cycle: J J U J I J O R 1 2
ATTACK_CYCLE_KEYS = [
    VK_J, VK_J, VK_U, VK_J, VK_I, VK_J, VK_O, VK_R, VK_1, VK_2,
]

# --- Convenience groups ---
SKILL_KEYS = [VK_U, VK_I, VK_O]
MOVE_KEYS = [VK_W, VK_A, VK_S, VK_D]

# --- Human-readable names for logging ---
KEY_NAMES: dict[int, str] = {
    VK_ESCAPE: "ESC", VK_ENTER: "Enter", VK_TAB: "Tab",
    VK_SPACE: "Space", VK_G: "G", VK_H: "H",
    VK_J: "J", VK_U: "U", VK_I: "I", VK_O: "O", VK_R: "R",
    VK_1: "1", VK_2: "2",
    VK_W: "W", VK_A: "A", VK_S: "S", VK_D: "D",
}


def key_name(vk: int) -> str:
    """Return human-readable name for a VK code."""
    return KEY_NAMES.get(vk, f"0x{vk:02X}")
```

**resources.py:**
```python
"""Asset paths and template metadata for AetherGazer.

Directories, index files, and state-template definitions.
Pure values — no imports of cv2, device, or vision.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from anime_game_afk.core.types import Rect

# --- Directory paths ---
ASSETS_ROOT = Path("assets/aether_gazer")
TEMPLATE_DIR = ASSETS_ROOT / "templates"
TEXT_TEMPLATE_DIR = TEMPLATE_DIR / "text"
TEMPLATE_INDEX = TEMPLATE_DIR / "index.json"
SCREENSHOT_DIR = ASSETS_ROOT / "screenshots"


@dataclass(frozen=True)
class StateTemplateDef:
    """Metadata for a game-state detection template."""
    name: str
    filename: str
    search_region: Rect | None
    threshold: float
    half_scale: bool = False  # True if template is 800x450


# Priority order matters — check most critical states first.
# Higher-priority states appear earlier in the list.
STATE_TEMPLATES: tuple[StateTemplateDef, ...] = (
    StateTemplateDef(
        name="mission_failed",
        filename="txt_mission_failed.png",
        search_region=Rect(400, 50, 800, 200),
        threshold=0.60,
    ),
    StateTemplateDef(
        name="revive_prompt",
        filename="txt_revive_800.png",
        search_region=None,
        threshold=0.70,
        half_scale=True,
    ),
    StateTemplateDef(
        name="skip_story_confirm",
        filename="txt_skip_story.png",
        search_region=Rect(500, 200, 600, 150),
        threshold=0.70,
    ),
    StateTemplateDef(
        name="continuous_battle",
        filename="txt_continuous_battle.png",
        search_region=Rect(400, 220, 800, 140),
        threshold=0.70,
    ),
    StateTemplateDef(
        name="prep_battle",
        filename="txt_prep_battle.png",
        search_region=Rect(1000, 780, 600, 120),
        threshold=0.70,
    ),
    StateTemplateDef(
        name="battle_hud",
        filename="txt_pause.png",
        search_region=Rect(0, 830, 200, 70),
        threshold=0.65,
    ),
    StateTemplateDef(
        name="stage_map",
        filename="txt_progress.png",
        search_region=Rect(0, 820, 300, 80),
        threshold=0.60,
    ),
)
```

**README.md:**
```markdown
# knowledge/ — Game Knowledge (Layer 4)

Pure data models for AetherGazer. **ZERO imports** of cv2, device, or vision.

## Files
| File | Contents |
|------|----------|
| constants.py | Design resolution, thresholds, timing defaults |
| keys.py | All VK codes (battle, UI, movement) |
| resources.py | Template directory paths, state template metadata |
| pages.py | PageDef with elements and coordinates (15 pages) |
| navigation.py | NavGraph with page-to-page edges |

## Rules
- Only import from `anime_game_afk.core.types` (Point, Rect, Resolution)
- All coordinates are in 1600x900 design resolution
- Hand-maintained — update when new pages/coordinates are discovered
```

**test_keys.py:**
```python
"""Tests for knowledge.keys module."""
from anime_game_afk.games.aether_gazer.knowledge.keys import (
    ATTACK_CYCLE_KEYS,
    KEY_NAMES,
    MOVE_KEYS,
    SKILL_KEYS,
    VK_ENTER,
    VK_ESCAPE,
    VK_J,
    VK_SPACE,
    VK_W,
    key_name,
)


def test_attack_cycle_length():
    """Attack cycle has 10 keys: J J U J I J O R 1 2."""
    assert len(ATTACK_CYCLE_KEYS) == 10


def test_attack_cycle_starts_with_j():
    assert ATTACK_CYCLE_KEYS[0] == VK_J
    assert ATTACK_CYCLE_KEYS[1] == VK_J


def test_skill_keys_count():
    assert len(SKILL_KEYS) == 3


def test_move_keys_count():
    assert len(MOVE_KEYS) == 4
    assert VK_W in MOVE_KEYS


def test_key_name_known():
    assert key_name(VK_ESCAPE) == "ESC"
    assert key_name(VK_ENTER) == "Enter"
    assert key_name(VK_SPACE) == "Space"
    assert key_name(VK_J) == "J"


def test_key_name_unknown():
    assert key_name(0xFF) == "0xFF"


def test_all_attack_keys_have_names():
    for vk in ATTACK_CYCLE_KEYS:
        assert vk in KEY_NAMES
```

---

## Task 2: Knowledge — pages.py (all 15 page definitions)

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/knowledge/pages.py`
- Test: `tests/games/aether_gazer/knowledge/test_pages.py`

**Purpose:** Migrate all 15 PageDef from `pages/definitions.py`. Convert Coord to Point, English comments, pure data only.

- [ ] Step 1: Create `pages.py` with PageElement and PageDef dataclasses
- [ ] Step 2: Define MAIN_HUB with all 11 elements
- [ ] Step 3: Define CHARACTER, GACHA, SHOP, GUILD, INVENTORY (5 pages)
- [ ] Step 4: Define AMUSEMENT, BATTLE_SELECT, DAILY_TASKS, MAIL (4 pages)
- [ ] Step 5: Define SETTINGS_PANEL, TACTICS, TRAINING, EVENTS, PLAYER_INFO (5 pages)
- [ ] Step 6: Create ALL_PAGES registry, SAFE_PAGES, UNSAFE_PAGES lists
- [ ] Step 7: Write test verifying page count, element lookups, safe/unsafe lists
- [ ] Step 8: Run tests, commit

**pages.py:**
```python
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
SAFE_PAGES: list[str] = [
    pid for pid, p in ALL_PAGES.items()
    if p.safe and pid != "main_hub"
]

# Pages marked unsafe (may cost resources)
UNSAFE_PAGES: list[str] = [
    pid for pid, p in ALL_PAGES.items()
    if not p.safe
]


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
```

**test_pages.py:**
```python
"""Tests for knowledge.pages module."""
from anime_game_afk.games.aether_gazer.knowledge.pages import (
    ALL_PAGES,
    SAFE_PAGES,
    UNSAFE_PAGES,
    find_element,
    get_page,
)


def test_total_page_count():
    """All 15 pages defined."""
    assert len(ALL_PAGES) == 15


def test_main_hub_exists():
    hub = get_page("main_hub")
    assert hub is not None
    assert hub.name_en == "Main Hub"
    assert hub.parent_page == ""


def test_main_hub_elements():
    hub = get_page("main_hub")
    assert hub is not None
    assert len(hub.elements) == 11


def test_unsafe_pages():
    assert "gacha" in UNSAFE_PAGES
    assert "inventory" in UNSAFE_PAGES
    assert "main_hub" not in UNSAFE_PAGES


def test_safe_pages_excludes_hub():
    assert "main_hub" not in SAFE_PAGES


def test_find_element_exists():
    elem = find_element("main_hub", "Battle")
    assert elem is not None
    assert elem.coord.x == 1465
    assert elem.coord.y == 850
    assert elem.target_page == "battle_select"


def test_find_element_missing():
    assert find_element("main_hub", "NonExistent") is None
    assert find_element("no_such_page", "Battle") is None


def test_all_pages_have_unique_ids():
    ids = [p.page_id for p in ALL_PAGES.values()]
    assert len(ids) == len(set(ids))


def test_character_page_has_back():
    elem = find_element("character", "Back")
    assert elem is not None
    assert elem.target_page == "main_hub"
```

---

## Task 3: Knowledge — navigation.py

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/knowledge/navigation.py`
- Test: `tests/games/aether_gazer/knowledge/test_navigation.py`

**Purpose:** Navigation graph defining page-to-page edges with action sequences. Extracted from nav_from_hub/back_to_hub fields in the old definitions.py.

- [ ] Step 1: Create `navigation.py` with NavMethod, NavAction, NavEdge dataclasses
- [ ] Step 2: Define all hub-to-page forward edges (click/key/esc)
- [ ] Step 3: Define all page-to-hub backward edges
- [ ] Step 4: Build NavGraph class with find_route() method
- [ ] Step 5: Write test for route lookup and edge counts
- [ ] Step 6: Run tests, commit

**navigation.py:**
```python
"""Navigation graph for AetherGazer.

Defines page-to-page edges with action sequences.
Hub-centric topology: all routes go through main_hub.
Pure data — no cv2, no device, no vision imports.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from anime_game_afk.core.types import Point
from anime_game_afk.games.aether_gazer.knowledge.keys import (
    VK_ESCAPE,
    VK_G,
    VK_H,
    VK_TAB,
)


class NavMethod(Enum):
    """How to perform a navigation action."""
    CLICK = "click"
    KEY = "key"
    ESC = "esc"


@dataclass(frozen=True)
class NavAction:
    """Single navigation step."""
    method: NavMethod
    coord: Point | None = None    # For CLICK method
    key_code: int | None = None   # For KEY method
    wait_after: float = 1.5       # Seconds to wait after action


@dataclass(frozen=True)
class NavEdge:
    """Directed edge in the navigation graph."""
    source: str      # Source page ID
    target: str      # Target page ID
    action: NavAction


def _click(x: int, y: int, wait: float = 2.0) -> NavAction:
    """Shorthand for a click navigation action."""
    return NavAction(NavMethod.CLICK, coord=Point(x, y), wait_after=wait)


def _key(vk: int, wait: float = 2.0) -> NavAction:
    """Shorthand for a key-press navigation action."""
    return NavAction(NavMethod.KEY, key_code=vk, wait_after=wait)


def _esc(wait: float = 1.5) -> NavAction:
    """Shorthand for an ESC navigation action."""
    return NavAction(NavMethod.ESC, key_code=VK_ESCAPE, wait_after=wait)


# Forward navigation: hub -> page
_FORWARD_EDGES: list[NavEdge] = [
    NavEdge("main_hub", "character",      _click(675, 850)),
    NavEdge("main_hub", "gacha",          _click(790, 850)),
    NavEdge("main_hub", "shop",           _click(910, 850)),
    NavEdge("main_hub", "guild",          _click(1025, 850)),
    NavEdge("main_hub", "inventory",      _click(1140, 850)),
    NavEdge("main_hub", "amusement",      _click(1257, 850)),
    NavEdge("main_hub", "battle_select",  _click(1465, 850)),
    NavEdge("main_hub", "tactics",        _click(100, 170)),
    NavEdge("main_hub", "training",       _click(100, 260)),
    NavEdge("main_hub", "events",         _click(100, 370)),
    NavEdge("main_hub", "player_info",    _click(50, 40)),
    NavEdge("main_hub", "daily_tasks",    _key(VK_G)),
    NavEdge("main_hub", "mail",           _key(VK_H)),
    NavEdge("main_hub", "settings_panel", _key(VK_TAB)),
]

# Backward navigation: page -> hub
_BACKWARD_EDGES: list[NavEdge] = [
    NavEdge("character",      "main_hub", _click(35, 35, 1.5)),
    NavEdge("gacha",          "main_hub", _esc()),
    NavEdge("shop",           "main_hub", _click(35, 35, 1.5)),
    NavEdge("guild",          "main_hub", _click(35, 35, 1.5)),
    NavEdge("inventory",      "main_hub", _click(35, 35, 1.5)),
    NavEdge("amusement",      "main_hub", _click(48, 48, 1.5)),
    NavEdge("battle_select",  "main_hub", _click(35, 35, 1.5)),
    NavEdge("tactics",        "main_hub", _click(35, 35, 1.5)),
    NavEdge("training",       "main_hub", _click(35, 35, 1.5)),
    NavEdge("events",         "main_hub", _click(35, 35, 1.5)),
    NavEdge("player_info",    "main_hub", _esc()),
    NavEdge("daily_tasks",    "main_hub", _esc()),
    NavEdge("mail",           "main_hub", _esc()),
    NavEdge("settings_panel", "main_hub", _esc()),
]


class NavGraph:
    """Navigation graph with route finding.

    Hub-centric: all routes go through main_hub.
    Any page -> hub -> any page = at most 2 edges.
    """

    def __init__(self) -> None:
        self._edges: dict[tuple[str, str], NavEdge] = {}
        for edge in _FORWARD_EDGES + _BACKWARD_EDGES:
            self._edges[(edge.source, edge.target)] = edge

    def get_edge(self, source: str, target: str) -> NavEdge | None:
        """Get direct edge between two pages."""
        return self._edges.get((source, target))

    def find_route(self, source: str, target: str) -> list[NavEdge] | None:
        """Find route from source to target.

        Returns list of edges, or None if no route exists.
        Routes are at most 2 hops (source->hub->target).
        """
        if source == target:
            return []

        # Direct edge?
        direct = self.get_edge(source, target)
        if direct is not None:
            return [direct]

        # Via hub: source -> hub -> target
        to_hub = self.get_edge(source, "main_hub")
        from_hub = self.get_edge("main_hub", target)
        if to_hub is not None and from_hub is not None:
            return [to_hub, from_hub]

        return None

    def outgoing(self, page_id: str) -> list[NavEdge]:
        """All edges from a given page."""
        return [e for (s, _), e in self._edges.items() if s == page_id]

    @property
    def edge_count(self) -> int:
        return len(self._edges)


# Module-level singleton
NAV_GRAPH = NavGraph()
```

**test_navigation.py:**
```python
"""Tests for knowledge.navigation module."""
from anime_game_afk.games.aether_gazer.knowledge.navigation import (
    NAV_GRAPH,
    NavMethod,
)


def test_edge_count():
    """14 forward + 14 backward = 28 edges."""
    assert NAV_GRAPH.edge_count == 28


def test_direct_forward_edge():
    edge = NAV_GRAPH.get_edge("main_hub", "shop")
    assert edge is not None
    assert edge.action.method == NavMethod.CLICK
    assert edge.action.coord is not None
    assert edge.action.coord.x == 910


def test_direct_backward_edge():
    edge = NAV_GRAPH.get_edge("shop", "main_hub")
    assert edge is not None
    assert edge.action.method == NavMethod.CLICK


def test_key_nav_edge():
    edge = NAV_GRAPH.get_edge("main_hub", "daily_tasks")
    assert edge is not None
    assert edge.action.method == NavMethod.KEY
    assert edge.action.key_code == 0x47  # VK_G


def test_esc_back_edge():
    edge = NAV_GRAPH.get_edge("settings_panel", "main_hub")
    assert edge is not None
    assert edge.action.method == NavMethod.ESC


def test_route_same_page():
    route = NAV_GRAPH.find_route("main_hub", "main_hub")
    assert route == []


def test_route_direct():
    route = NAV_GRAPH.find_route("main_hub", "character")
    assert route is not None
    assert len(route) == 1


def test_route_via_hub():
    route = NAV_GRAPH.find_route("shop", "guild")
    assert route is not None
    assert len(route) == 2
    assert route[0].target == "main_hub"
    assert route[1].target == "guild"


def test_route_nonexistent():
    route = NAV_GRAPH.find_route("main_hub", "nonexistent_page")
    assert route is None


def test_hub_outgoing():
    edges = NAV_GRAPH.outgoing("main_hub")
    assert len(edges) == 14
```

---

## Task 4: Ops — base.py (Op protocol, OpResult, OpContext)

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/ops/__init__.py`
- Create: `src/anime_game_afk/games/aether_gazer/ops/base.py`
- Create: `src/anime_game_afk/games/aether_gazer/ops/README.md`
- Test: `tests/games/aether_gazer/ops/test_base.py`

**Purpose:** Define the Op protocol that every atomic operation implements. OpContext wraps device + logger. OpResult signals success/failure.

- [ ] Step 1: Create `ops/` directory with empty `__init__.py`
- [ ] Step 2: Create `base.py` with OpResult, OpContext, GameState enum, Op protocol
- [ ] Step 3: Create `README.md` documenting ops/ directory structure
- [ ] Step 4: Write test with a trivial mock op verifying protocol
- [ ] Step 5: Run tests, commit

**base.py:**
```python
"""Base types for atomic operations.

Every op implements the Op protocol: async run(ctx) -> OpResult.
Ops are the smallest executable units — each does ONE thing.
Ops do NOT call other ops. Composition belongs in Layer 6.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

import numpy as np


@dataclass
class OpResult:
    """Result of an atomic operation."""
    success: bool
    data: Any = None
    error: str | None = None


class GameState(Enum):
    """Possible game states during automation."""
    BATTLE = "battle"
    CUTSCENE = "cutscene"
    DIALOGUE = "dialogue"
    REVIVE_PROMPT = "revive_prompt"
    LOADING = "loading"
    STAGE_MAP = "stage_map"
    SKIP_STORY_CONFIRM = "skip_story_confirm"
    CONTINUOUS_BATTLE = "continuous_battle"
    MISSION_FAILED = "mission_failed"
    PREP_BATTLE = "prep_battle"
    UNKNOWN = "unknown"


@runtime_checkable
class DevicePort(Protocol):
    """What ops need from the device (Layer 1)."""
    def screenshot(self) -> np.ndarray: ...
    def click(self, x: int, y: int) -> None: ...
    def press_key(self, vk_code: int) -> None: ...
    def hold_key(self, vk_code: int, duration_s: float) -> None: ...


@runtime_checkable
class LoggerPort(Protocol):
    """What ops need from the logger (Layer 3)."""
    def info(self, msg: str, **ctx: Any) -> None: ...
    def debug(self, msg: str, **ctx: Any) -> None: ...
    def warning(self, msg: str, **ctx: Any) -> None: ...
    def error(self, msg: str, **ctx: Any) -> None: ...


class _NullLogger:
    """Fallback logger that does nothing."""
    def info(self, msg: str, **ctx: Any) -> None: ...
    def debug(self, msg: str, **ctx: Any) -> None: ...
    def warning(self, msg: str, **ctx: Any) -> None: ...
    def error(self, msg: str, **ctx: Any) -> None: ...


@dataclass
class OpContext:
    """Shared context passed to all ops.

    Provides access to device I/O, logging, and shared state.
    Vision functions are imported directly by ops (stateless Layer 2).
    Knowledge is imported directly by ops (pure data Layer 4).
    """
    device: DevicePort
    logger: LoggerPort = field(default_factory=_NullLogger)
    state: dict[str, Any] = field(default_factory=dict)

    def screenshot(self) -> np.ndarray:
        """Convenience: take screenshot via device."""
        return self.device.screenshot()


@runtime_checkable
class Op(Protocol):
    """Protocol for atomic operations."""
    async def run(self, ctx: OpContext) -> OpResult: ...
```

**README.md:**
```markdown
# ops/ — Atomic Operations (Layer 5)

Smallest executable units. Each op does ONE thing, returns OpResult.

## Structure
| Subdir | Purpose |
|--------|---------|
| base.py | Op protocol, OpResult, OpContext, GameState |
| perception/ | "See" — read game state from screenshots |
| navigate/ | "Go" — move between pages |
| interact/ | "Act" — click, confirm, skip |
| combat/ | "Fight" — battle-specific actions |

## Rules
- Each file = one op (or small family)
- Ops complete in <10 seconds
- Ops do NOT call other ops
- Ops handle their own retries, NOT cross-op recovery
- Depends on: Layers 1-4 only
```

**test_base.py:**
```python
"""Tests for ops.base module."""
import asyncio
from dataclasses import dataclass

import numpy as np

from anime_game_afk.games.aether_gazer.ops.base import (
    GameState,
    Op,
    OpContext,
    OpResult,
)


@dataclass
class MockDevice:
    """Minimal device mock for testing."""
    click_log: list = None
    key_log: list = None

    def __post_init__(self):
        self.click_log = self.click_log or []
        self.key_log = self.key_log or []

    def screenshot(self) -> np.ndarray:
        return np.zeros((900, 1600, 3), dtype=np.uint8)

    def click(self, x: int, y: int) -> None:
        self.click_log.append((x, y))

    def press_key(self, vk_code: int) -> None:
        self.key_log.append(vk_code)

    def hold_key(self, vk_code: int, duration_s: float) -> None:
        self.key_log.append((vk_code, duration_s))


class TrivialOp:
    """Op that always succeeds."""
    async def run(self, ctx: OpContext) -> OpResult:
        return OpResult(success=True, data="ok")


def test_op_result_success():
    r = OpResult(success=True, data=42)
    assert r.success
    assert r.data == 42
    assert r.error is None


def test_op_result_failure():
    r = OpResult(success=False, error="timeout")
    assert not r.success
    assert r.error == "timeout"


def test_op_protocol():
    op = TrivialOp()
    assert isinstance(op, Op)


def test_op_context_screenshot():
    device = MockDevice()
    ctx = OpContext(device=device)
    img = ctx.screenshot()
    assert img.shape == (900, 1600, 3)


def test_trivial_op_run():
    device = MockDevice()
    ctx = OpContext(device=device)
    result = asyncio.get_event_loop().run_until_complete(
        TrivialOp().run(ctx)
    )
    assert result.success
    assert result.data == "ok"


def test_game_state_enum():
    assert GameState.BATTLE.value == "battle"
    assert GameState.UNKNOWN.value == "unknown"
    assert len(GameState) == 11
```

---

## Task 5: Ops — perception/ (identify_page, detect_game_state)

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/ops/perception/__init__.py`
- Create: `src/anime_game_afk/games/aether_gazer/ops/perception/identify_page.py`
- Create: `src/anime_game_afk/games/aether_gazer/ops/perception/detect_game_state.py`
- Create: `src/anime_game_afk/games/aether_gazer/ops/perception/README.md`
- Test: `tests/games/aether_gazer/ops/perception/test_identify_page.py`
- Test: `tests/games/aether_gazer/ops/perception/test_detect_game_state.py`

**Purpose:** Migrate template_identifier.py into identify_page op. Create game state detection from ch6_battle.py's StateDetector.

- [ ] Step 1: Create `perception/` directory with empty `__init__.py`
- [ ] Step 2: Create `identify_page.py` — loads page templates, matches against screenshot
- [ ] Step 3: Create `detect_game_state.py` — loads text templates, detects game state
- [ ] Step 4: Create `README.md`
- [ ] Step 5: Write tests with mock device returning known images
- [ ] Step 6: Run tests, commit

**identify_page.py:**
```python
"""Identify current page from screenshot.

Loads page templates from index.json, matches against screenshot
using vision.matcher. Returns (page_id, confidence).

Migrated from pages/template_identifier.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from anime_game_afk.core.types import Rect
from anime_game_afk.vision.matcher import match_template
from anime_game_afk.games.aether_gazer.knowledge.constants import (
    MATCH_THRESHOLD,
)
from anime_game_afk.games.aether_gazer.knowledge.resources import (
    TEMPLATE_DIR,
    TEMPLATE_INDEX,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult


# Module-level template cache (loaded once, reused)
_page_templates: dict[str, list[dict]] | None = None


def _load_templates() -> dict[str, list[dict]]:
    """Load page templates from index.json.

    Returns dict: page_id -> list of {image, search_region}.
    Cached at module level after first call.
    """
    global _page_templates
    if _page_templates is not None:
        return _page_templates

    _page_templates = {}
    if not TEMPLATE_INDEX.exists():
        return _page_templates

    with open(TEMPLATE_INDEX, encoding="utf-8") as f:
        index = json.load(f)

    for page_id, templates in index.items():
        loaded = []
        for tpl in templates:
            img_path = TEMPLATE_DIR / tpl["path"] if not Path(tpl["path"]).is_absolute() else Path(tpl["path"])
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            search = tpl.get("search")
            region = None
            if search and len(search) == 4:
                x1, y1, x2, y2 = search
                region = Rect(x1, y1, x2 - x1, y2 - y1)
            loaded.append({"image": img, "region": region})
        if loaded:
            _page_templates[page_id] = loaded

    return _page_templates


def identify(screenshot: np.ndarray) -> tuple[str, float]:
    """Identify which page the screenshot shows.

    Returns (page_id, confidence). Returns ("unknown", 0.0) if
    no page matches above MATCH_THRESHOLD.

    This is a pure utility function — usable by other ops directly.
    """
    templates = _load_templates()
    best_page = "unknown"
    best_score = 0.0

    for page_id, tpl_list in templates.items():
        scores = []
        for tpl in tpl_list:
            result = match_template(
                screenshot, tpl["image"], region=tpl["region"],
            )
            scores.append(result.score)
        if scores:
            avg = sum(scores) / len(scores)
            if avg > best_score:
                best_score = avg
                best_page = page_id

    if best_score < MATCH_THRESHOLD:
        return ("unknown", best_score)
    return (best_page, best_score)


def is_on_page(screenshot: np.ndarray, page_id: str) -> bool:
    """Quick check: is the screenshot showing the given page?"""
    templates = _load_templates()
    tpl_list = templates.get(page_id, [])
    if not tpl_list:
        return False
    scores = []
    for tpl in tpl_list:
        result = match_template(
            screenshot, tpl["image"], region=tpl["region"],
        )
        scores.append(result.score)
    avg = sum(scores) / len(scores) if scores else 0.0
    return avg >= MATCH_THRESHOLD


class IdentifyPageOp:
    """Op wrapper: take screenshot and identify current page.

    Result data: {"page_id": str, "confidence": float}
    """

    async def run(self, ctx: OpContext) -> OpResult:
        screenshot = ctx.screenshot()
        page_id, confidence = identify(screenshot)
        ctx.logger.info(
            f"Page identified: {page_id} (confidence={confidence:.2f})"
        )
        return OpResult(
            success=(page_id != "unknown"),
            data={"page_id": page_id, "confidence": confidence},
        )
```

**detect_game_state.py:**
```python
"""Detect current game state from screenshot.

Uses template matching against known text templates to determine
whether we're in battle, cutscene, dialogue, menus, etc.
Templates are loaded from assets/aether_gazer/templates/text/.

Migrated from scripts/ch6_battle.py StateDetector.
"""
from __future__ import annotations

import cv2
import numpy as np

from anime_game_afk.core.types import Rect
from anime_game_afk.vision.matcher import match_template
from anime_game_afk.games.aether_gazer.knowledge.resources import (
    STATE_TEMPLATES,
    TEXT_TEMPLATE_DIR,
    StateTemplateDef,
)
from anime_game_afk.games.aether_gazer.ops.base import (
    GameState,
    OpContext,
    OpResult,
)

# Mapping from template name to GameState enum
_STATE_MAP: dict[str, GameState] = {
    "mission_failed": GameState.MISSION_FAILED,
    "revive_prompt": GameState.REVIVE_PROMPT,
    "skip_story_confirm": GameState.SKIP_STORY_CONFIRM,
    "continuous_battle": GameState.CONTINUOUS_BATTLE,
    "prep_battle": GameState.PREP_BATTLE,
    "battle_hud": GameState.BATTLE,
    "stage_map": GameState.STAGE_MAP,
}

# Module-level cache: template name -> loaded image
_loaded: dict[str, np.ndarray] | None = None


def _load_state_templates() -> dict[str, np.ndarray]:
    """Load all state detection templates from disk."""
    global _loaded
    if _loaded is not None:
        return _loaded

    _loaded = {}
    for tdef in STATE_TEMPLATES:
        path = TEXT_TEMPLATE_DIR / tdef.filename
        img = cv2.imread(str(path))
        if img is None:
            continue
        _loaded[tdef.name] = img
    return _loaded


def detect_state(screenshot: np.ndarray) -> tuple[GameState, float]:
    """Detect game state from a 1600x900 screenshot.

    Returns (GameState, confidence). Checks templates in priority
    order; returns the highest-confidence match above threshold.

    Pure utility function — usable by other ops directly.
    """
    images = _load_state_templates()
    half = cv2.resize(screenshot, (800, 450), interpolation=cv2.INTER_AREA)

    best_state = GameState.UNKNOWN
    best_conf = 0.0

    for tdef in STATE_TEMPLATES:
        tpl_img = images.get(tdef.name)
        if tpl_img is None:
            continue

        # Choose image scale: half-size templates match against 800x450
        img = half if tdef.half_scale else screenshot
        region = tdef.search_region

        # Scale search region for half-size templates
        if tdef.half_scale and region is not None:
            region = Rect(
                region.x // 2, region.y // 2,
                region.w // 2, region.h // 2,
            )

        result = match_template(img, tpl_img, region=region)

        if result.score >= tdef.threshold and result.score > best_conf:
            best_conf = result.score
            best_state = _STATE_MAP.get(tdef.name, GameState.UNKNOWN)

    # Black screen = loading (only reliable non-template check).
    # This is NOT pixel-brightness UI detection — it detects a
    # fully black loading screen where mean < 15.
    if best_state == GameState.UNKNOWN and np.mean(screenshot) < 15:
        best_state = GameState.LOADING
        best_conf = 0.99

    return (best_state, best_conf)


class DetectGameStateOp:
    """Op wrapper: take screenshot and detect game state.

    Result data: {"state": GameState, "confidence": float}
    """

    async def run(self, ctx: OpContext) -> OpResult:
        screenshot = ctx.screenshot()
        state, confidence = detect_state(screenshot)
        ctx.logger.debug(
            f"Game state: {state.value} (confidence={confidence:.2f})"
        )
        return OpResult(
            success=True,
            data={"state": state, "confidence": confidence},
        )
```

**test_identify_page.py:**
```python
"""Tests for perception.identify_page module."""
import asyncio
from dataclasses import dataclass

import numpy as np

from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.perception.identify_page import (
    IdentifyPageOp,
)


@dataclass
class MockDevice:
    def screenshot(self) -> np.ndarray:
        return np.zeros((900, 1600, 3), dtype=np.uint8)
    def click(self, x: int, y: int) -> None: ...
    def press_key(self, vk_code: int) -> None: ...
    def hold_key(self, vk_code: int, duration_s: float) -> None: ...


def test_identify_returns_result():
    """Op returns OpResult with page_id and confidence keys."""
    ctx = OpContext(device=MockDevice())
    op = IdentifyPageOp()
    result = asyncio.get_event_loop().run_until_complete(op.run(ctx))
    assert isinstance(result, OpResult)
    assert "page_id" in result.data
    assert "confidence" in result.data


def test_black_screen_is_unknown():
    """Black screenshot should not match any page."""
    ctx = OpContext(device=MockDevice())
    op = IdentifyPageOp()
    result = asyncio.get_event_loop().run_until_complete(op.run(ctx))
    # With no templates loaded (test env), expect unknown
    assert result.data["page_id"] == "unknown"
```

**test_detect_game_state.py:**
```python
"""Tests for perception.detect_game_state module."""
import asyncio
from dataclasses import dataclass

import numpy as np

from anime_game_afk.games.aether_gazer.ops.base import GameState, OpContext
from anime_game_afk.games.aether_gazer.ops.perception.detect_game_state import (
    DetectGameStateOp,
    detect_state,
)


@dataclass
class MockDevice:
    _image: np.ndarray | None = None
    def screenshot(self) -> np.ndarray:
        if self._image is not None:
            return self._image
        return np.zeros((900, 1600, 3), dtype=np.uint8)
    def click(self, x: int, y: int) -> None: ...
    def press_key(self, vk_code: int) -> None: ...
    def hold_key(self, vk_code: int, duration_s: float) -> None: ...


def test_black_screen_is_loading():
    """Fully black image should be detected as LOADING."""
    black = np.zeros((900, 1600, 3), dtype=np.uint8)
    state, conf = detect_state(black)
    assert state == GameState.LOADING
    assert conf > 0.9


def test_bright_screen_not_loading():
    """Non-black image should not be LOADING (without templates)."""
    bright = np.full((900, 1600, 3), 128, dtype=np.uint8)
    state, conf = detect_state(bright)
    # Without templates, non-black = UNKNOWN
    assert state == GameState.UNKNOWN


def test_op_returns_result():
    ctx = OpContext(device=MockDevice())
    op = DetectGameStateOp()
    result = asyncio.get_event_loop().run_until_complete(op.run(ctx))
    assert result.success
    assert "state" in result.data
    assert isinstance(result.data["state"], GameState)
```

---

## Task 6: Ops — navigate/ (go_back, return_to_hub, goto_page, wake_hub_ui)

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/ops/navigate/__init__.py`
- Create: `src/anime_game_afk/games/aether_gazer/ops/navigate/go_back.py`
- Create: `src/anime_game_afk/games/aether_gazer/ops/navigate/return_to_hub.py`
- Create: `src/anime_game_afk/games/aether_gazer/ops/navigate/goto_page.py`
- Create: `src/anime_game_afk/games/aether_gazer/ops/navigate/wake_hub_ui.py`
- Create: `src/anime_game_afk/games/aether_gazer/ops/navigate/README.md`
- Test: `tests/games/aether_gazer/ops/navigate/test_navigate.py`

**Purpose:** Decompose Navigator class into four independent ops. Each handles one navigation concern.

- [ ] Step 1: Create `navigate/` directory with empty `__init__.py`
- [ ] Step 2: Create `wake_hub_ui.py` — click screen center to dismiss idle
- [ ] Step 3: Create `go_back.py` — press ESC or click back button
- [ ] Step 4: Create `return_to_hub.py` — loop detect+back until hub reached
- [ ] Step 5: Create `goto_page.py` — navigate hub->target via NavGraph
- [ ] Step 6: Create `README.md`
- [ ] Step 7: Write tests with mocked device
- [ ] Step 8: Run tests, commit

**wake_hub_ui.py:**
```python
"""Wake up hub UI from idle mode.

Clicks screen center to dismiss any idle overlay,
then waits briefly for the UI to appear.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.constants import (
    SCREEN_CENTER_X,
    SCREEN_CENTER_Y,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult


class WakeHubUiOp:
    """Click screen center to wake idle hub UI."""

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.device.click(SCREEN_CENTER_X, SCREEN_CENTER_Y)
        ctx.logger.debug("Clicked screen center to wake UI")
        await asyncio.sleep(0.5)
        return OpResult(success=True)
```

**go_back.py:**
```python
"""Go back one page.

Presses ESC or clicks the back button (35, 35) depending on
the current page's navigation edge. Falls back to ESC if no
edge is found.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.constants import (
    BACK_BUTTON_X,
    BACK_BUTTON_Y,
)
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ESCAPE
from anime_game_afk.games.aether_gazer.knowledge.navigation import (
    NAV_GRAPH,
    NavMethod,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult


class GoBackOp:
    """Go back from current page toward hub.

    Uses the navigation graph to determine the correct back action.
    If current_page is unknown, falls back to ESC.
    """

    def __init__(self, current_page: str = "unknown") -> None:
        self._current_page = current_page

    async def run(self, ctx: OpContext) -> OpResult:
        # Look up the backward edge
        edge = NAV_GRAPH.get_edge(self._current_page, "main_hub")

        if edge is not None:
            action = edge.action
            if action.method == NavMethod.CLICK and action.coord:
                ctx.device.click(action.coord.x, action.coord.y)
                ctx.logger.info(
                    f"Go back: click ({action.coord.x}, {action.coord.y})"
                )
            elif action.method == NavMethod.KEY and action.key_code:
                ctx.device.press_key(action.key_code)
                ctx.logger.info(
                    f"Go back: press key 0x{action.key_code:02X}"
                )
            else:
                ctx.device.press_key(VK_ESCAPE)
                ctx.logger.info("Go back: ESC (default)")
            await asyncio.sleep(action.wait_after)
        else:
            # Unknown page — try ESC
            ctx.device.press_key(VK_ESCAPE)
            ctx.logger.info("Go back: ESC (no edge found)")
            await asyncio.sleep(1.5)

        return OpResult(success=True)
```

**return_to_hub.py:**
```python
"""Return to main hub from any page.

Repeatedly detects current page and navigates backward until
main_hub is reached. Uses template matching for verification.
Max 8 attempts before giving up.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.constants import (
    BACK_BUTTON_X,
    BACK_BUTTON_Y,
    SCREEN_CENTER_X,
    SCREEN_CENTER_Y,
)
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ESCAPE
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.perception.identify_page import (
    identify,
)

_MAX_ATTEMPTS = 8
_HUB_THRESHOLD = 0.60


class ReturnToHubOp:
    """Navigate back to main hub from any page."""

    async def run(self, ctx: OpContext) -> OpResult:
        for attempt in range(_MAX_ATTEMPTS):
            # Dismiss any dialog/overlay
            ctx.device.click(SCREEN_CENTER_X, SCREEN_CENTER_Y - 50)
            await asyncio.sleep(0.5)

            # Check current page
            screenshot = ctx.screenshot()
            page_id, conf = identify(screenshot)

            if page_id == "main_hub" and conf >= _HUB_THRESHOLD:
                ctx.logger.info(
                    f"At main hub (attempt {attempt}, conf={conf:.2f})"
                )
                return OpResult(
                    success=True,
                    data={"page_id": "main_hub", "attempts": attempt},
                )

            # Settings panel: just ESC
            if page_id == "settings_panel":
                ctx.device.press_key(VK_ESCAPE)
                ctx.logger.info("Settings panel detected, pressing ESC")
                await asyncio.sleep(1.0)
                continue

            # Alternate between ESC and click-back
            ctx.logger.warning(
                f"Not at hub (page={page_id}, conf={conf:.2f}), "
                f"attempt {attempt}"
            )
            if attempt % 2 == 0:
                ctx.device.press_key(VK_ESCAPE)
            else:
                ctx.device.click(BACK_BUTTON_X, BACK_BUTTON_Y)
            await asyncio.sleep(1.5)

        # Final check
        ctx.device.click(SCREEN_CENTER_X, SCREEN_CENTER_Y - 50)
        await asyncio.sleep(0.5)
        screenshot = ctx.screenshot()
        page_id, conf = identify(screenshot)

        if page_id == "main_hub" and conf >= _HUB_THRESHOLD:
            return OpResult(success=True, data={"page_id": "main_hub"})

        ctx.logger.error("Failed to return to hub after max attempts")
        return OpResult(success=False, error="Could not reach main hub")
```

**goto_page.py:**
```python
"""Navigate to a specific page via the hub.

Route: current_page -> main_hub -> target_page.
Uses NavGraph to determine actions, template matching to verify.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.constants import (
    SCREEN_CENTER_X,
    SCREEN_CENTER_Y,
)
from anime_game_afk.games.aether_gazer.knowledge.navigation import (
    NAV_GRAPH,
    NavMethod,
)
from anime_game_afk.games.aether_gazer.knowledge.pages import ALL_PAGES
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.perception.identify_page import (
    identify,
    is_on_page,
)

_MAX_RETRIES = 2


def _execute_nav_action(ctx: OpContext, action) -> None:
    """Execute a single NavAction on the device."""
    if action.method == NavMethod.CLICK and action.coord:
        ctx.device.click(action.coord.x, action.coord.y)
    elif action.method == NavMethod.KEY and action.key_code:
        ctx.device.press_key(action.key_code)
    elif action.method == NavMethod.ESC:
        from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ESCAPE
        ctx.device.press_key(VK_ESCAPE)


class GotoPageOp:
    """Navigate from current location to target page.

    Finds route via NavGraph, executes each edge's action,
    and verifies arrival with template matching.
    """

    def __init__(self, target_page_id: str) -> None:
        self._target = target_page_id

    async def run(self, ctx: OpContext) -> OpResult:
        if self._target not in ALL_PAGES:
            return OpResult(
                success=False, error=f"Unknown page: {self._target}"
            )

        # Already there?
        screenshot = ctx.screenshot()
        if is_on_page(screenshot, self._target):
            ctx.logger.info(f"Already on page: {self._target}")
            return OpResult(
                success=True,
                data={"page_id": self._target, "already_there": True},
            )

        # Detect current page
        current, _ = identify(screenshot)

        for attempt in range(_MAX_RETRIES + 1):
            # Find route
            route = NAV_GRAPH.find_route(current, self._target)
            if route is None:
                return OpResult(
                    success=False,
                    error=f"No route from {current} to {self._target}",
                )

            # Execute each edge
            for edge in route:
                # Wake UI before navigation
                ctx.device.click(SCREEN_CENTER_X, SCREEN_CENTER_Y)
                await asyncio.sleep(0.3)

                _execute_nav_action(ctx, edge.action)
                await asyncio.sleep(edge.action.wait_after)

            # Verify arrival
            screenshot = ctx.screenshot()
            if is_on_page(screenshot, self._target):
                ctx.logger.info(
                    f"Navigation success: {self._target} "
                    f"(attempt {attempt})"
                )
                return OpResult(
                    success=True,
                    data={"page_id": self._target},
                )

            # Failed — re-detect and retry
            current, _ = identify(screenshot)
            ctx.logger.warning(
                f"Navigation verify failed: expected={self._target}, "
                f"actual={current} (attempt {attempt})"
            )

        return OpResult(
            success=False,
            error=f"Failed to reach {self._target} after {_MAX_RETRIES} retries",
        )
```

**test_navigate.py:**
```python
"""Tests for navigate ops."""
import asyncio
from dataclasses import dataclass, field

import numpy as np

from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.games.aether_gazer.ops.navigate.go_back import GoBackOp
from anime_game_afk.games.aether_gazer.ops.navigate.wake_hub_ui import (
    WakeHubUiOp,
)


@dataclass
class MockDevice:
    click_log: list = field(default_factory=list)
    key_log: list = field(default_factory=list)

    def screenshot(self) -> np.ndarray:
        return np.zeros((900, 1600, 3), dtype=np.uint8)
    def click(self, x: int, y: int) -> None:
        self.click_log.append((x, y))
    def press_key(self, vk_code: int) -> None:
        self.key_log.append(vk_code)
    def hold_key(self, vk_code: int, duration_s: float) -> None:
        self.key_log.append((vk_code, duration_s))


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_wake_hub_ui_clicks_center():
    device = MockDevice()
    ctx = OpContext(device=device)
    result = _run(WakeHubUiOp().run(ctx))
    assert result.success
    assert (800, 450) in device.click_log


def test_go_back_unknown_presses_esc():
    device = MockDevice()
    ctx = OpContext(device=device)
    result = _run(GoBackOp("unknown").run(ctx))
    assert result.success
    assert 0x1B in device.key_log  # VK_ESCAPE


def test_go_back_shop_clicks_back():
    device = MockDevice()
    ctx = OpContext(device=device)
    result = _run(GoBackOp("shop").run(ctx))
    assert result.success
    assert (35, 35) in device.click_log
```

---

## Task 7: Ops — interact/ (click_element, skip_cutscene, advance_dialogue, confirm_popup)

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/ops/interact/__init__.py`
- Create: `src/anime_game_afk/games/aether_gazer/ops/interact/click_element.py`
- Create: `src/anime_game_afk/games/aether_gazer/ops/interact/skip_cutscene.py`
- Create: `src/anime_game_afk/games/aether_gazer/ops/interact/advance_dialogue.py`
- Create: `src/anime_game_afk/games/aether_gazer/ops/interact/confirm_popup.py`
- Create: `src/anime_game_afk/games/aether_gazer/ops/interact/README.md`
- Test: `tests/games/aether_gazer/ops/interact/test_interact.py`

**Purpose:** UI interaction atomic ops extracted from atomic.py and ch6_battle.py.

- [ ] Step 1: Create `interact/` directory with empty `__init__.py`
- [ ] Step 2: Create `click_element.py` — look up element by name_en, click coord
- [ ] Step 3: Create `skip_cutscene.py` — ESC -> wait -> Enter to skip
- [ ] Step 4: Create `advance_dialogue.py` — press Space to advance
- [ ] Step 5: Create `confirm_popup.py` — press Enter to confirm or ESC to cancel
- [ ] Step 6: Create `README.md`
- [ ] Step 7: Write tests
- [ ] Step 8: Run tests, commit

**click_element.py:**
```python
"""Click a named element on a page.

Looks up the element by English name (name_en) in the page's
element list, then clicks its coordinate. Refuses to click
unsafe elements unless force=True.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.constants import CLICK_WAIT
from anime_game_afk.games.aether_gazer.knowledge.pages import find_element
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult


class ClickElementOp:
    """Click a named element on a specified page."""

    def __init__(
        self,
        page_id: str,
        element_name_en: str,
        wait_after: float = CLICK_WAIT,
        force_unsafe: bool = False,
    ) -> None:
        self._page_id = page_id
        self._element_name = element_name_en
        self._wait = wait_after
        self._force = force_unsafe

    async def run(self, ctx: OpContext) -> OpResult:
        elem = find_element(self._page_id, self._element_name)
        if elem is None:
            return OpResult(
                success=False,
                error=f"Element '{self._element_name}' not found "
                      f"on page '{self._page_id}'",
            )

        if not elem.safe and not self._force:
            return OpResult(
                success=False,
                error=f"Element '{self._element_name}' is unsafe. "
                      f"Use force_unsafe=True to override.",
            )

        ctx.device.click(elem.coord.x, elem.coord.y)
        ctx.logger.info(
            f"Clicked {self._element_name} at "
            f"({elem.coord.x}, {elem.coord.y}) on {self._page_id}"
        )
        await asyncio.sleep(self._wait)
        return OpResult(
            success=True,
            data={"element": self._element_name, "page": self._page_id},
        )
```

**skip_cutscene.py:**
```python
"""Skip a cutscene.

Sequence: ESC (open skip dialog) -> wait -> Enter (confirm skip).
Uses keyboard shortcuts per the game's UI convention.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.keys import (
    VK_ENTER,
    VK_ESCAPE,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult


class SkipCutsceneOp:
    """Skip a cutscene by pressing ESC then Enter."""

    def __init__(self, confirm_wait: float = 1.5) -> None:
        self._confirm_wait = confirm_wait

    async def run(self, ctx: OpContext) -> OpResult:
        # ESC opens the "skip?" confirmation dialog
        ctx.device.press_key(VK_ESCAPE)
        ctx.logger.info("Skip cutscene: pressed ESC")
        await asyncio.sleep(self._confirm_wait)

        # Enter confirms the skip
        ctx.device.press_key(VK_ENTER)
        ctx.logger.info("Skip cutscene: pressed Enter to confirm")
        await asyncio.sleep(2.0)

        return OpResult(success=True)
```

**advance_dialogue.py:**
```python
"""Advance in-game dialogue.

Presses Space to push dialogue forward. Simple single-action op.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.keys import VK_SPACE
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult


class AdvanceDialogueOp:
    """Press Space to advance dialogue."""

    def __init__(self, wait_after: float = 0.4) -> None:
        self._wait = wait_after

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.device.press_key(VK_SPACE)
        ctx.logger.debug("Advance dialogue: pressed Space")
        await asyncio.sleep(self._wait)
        return OpResult(success=True)
```

**confirm_popup.py:**
```python
"""Confirm or dismiss a popup dialog.

Presses Enter to confirm or ESC to cancel.
The action is configurable; default is confirm (Enter).
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.keys import (
    VK_ENTER,
    VK_ESCAPE,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult


class ConfirmPopupOp:
    """Respond to a popup dialog."""

    def __init__(
        self, confirm: bool = True, wait_after: float = 2.0
    ) -> None:
        self._confirm = confirm
        self._wait = wait_after

    async def run(self, ctx: OpContext) -> OpResult:
        if self._confirm:
            ctx.device.press_key(VK_ENTER)
            ctx.logger.info("Popup confirmed: pressed Enter")
        else:
            ctx.device.press_key(VK_ESCAPE)
            ctx.logger.info("Popup dismissed: pressed ESC")

        await asyncio.sleep(self._wait)
        return OpResult(success=True, data={"confirmed": self._confirm})
```

**test_interact.py:**
```python
"""Tests for interact ops."""
import asyncio
from dataclasses import dataclass, field

import numpy as np

from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.games.aether_gazer.ops.interact.advance_dialogue import (
    AdvanceDialogueOp,
)
from anime_game_afk.games.aether_gazer.ops.interact.click_element import (
    ClickElementOp,
)
from anime_game_afk.games.aether_gazer.ops.interact.confirm_popup import (
    ConfirmPopupOp,
)
from anime_game_afk.games.aether_gazer.ops.interact.skip_cutscene import (
    SkipCutsceneOp,
)


@dataclass
class MockDevice:
    click_log: list = field(default_factory=list)
    key_log: list = field(default_factory=list)

    def screenshot(self) -> np.ndarray:
        return np.zeros((900, 1600, 3), dtype=np.uint8)
    def click(self, x: int, y: int) -> None:
        self.click_log.append((x, y))
    def press_key(self, vk_code: int) -> None:
        self.key_log.append(vk_code)
    def hold_key(self, vk_code: int, duration_s: float) -> None:
        self.key_log.append((vk_code, duration_s))


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_click_element_success():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = ClickElementOp("main_hub", "Shop", wait_after=0.0)
    result = _run(op.run(ctx))
    assert result.success
    assert (910, 850) in device.click_log


def test_click_element_not_found():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = ClickElementOp("main_hub", "Nonexistent", wait_after=0.0)
    result = _run(op.run(ctx))
    assert not result.success
    assert "not found" in result.error


def test_click_element_unsafe_blocked():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = ClickElementOp("main_hub", "Gacha", wait_after=0.0)
    result = _run(op.run(ctx))
    assert not result.success
    assert "unsafe" in result.error


def test_click_element_unsafe_forced():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = ClickElementOp(
        "main_hub", "Gacha", wait_after=0.0, force_unsafe=True
    )
    result = _run(op.run(ctx))
    assert result.success


def test_skip_cutscene():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = SkipCutsceneOp(confirm_wait=0.0)
    result = _run(op.run(ctx))
    assert result.success
    assert 0x1B in device.key_log  # ESC
    assert 0x0D in device.key_log  # Enter


def test_advance_dialogue():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = AdvanceDialogueOp(wait_after=0.0)
    result = _run(op.run(ctx))
    assert result.success
    assert 0x20 in device.key_log  # Space


def test_confirm_popup_confirm():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = ConfirmPopupOp(confirm=True, wait_after=0.0)
    result = _run(op.run(ctx))
    assert result.success
    assert result.data["confirmed"] is True
    assert 0x0D in device.key_log


def test_confirm_popup_dismiss():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = ConfirmPopupOp(confirm=False, wait_after=0.0)
    result = _run(op.run(ctx))
    assert result.success
    assert result.data["confirmed"] is False
    assert 0x1B in device.key_log
```

---

## Task 8: Ops — combat/ (attack_cycle, handle_revive, walk_forward)

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/ops/combat/__init__.py`
- Create: `src/anime_game_afk/games/aether_gazer/ops/combat/attack_cycle.py`
- Create: `src/anime_game_afk/games/aether_gazer/ops/combat/handle_revive.py`
- Create: `src/anime_game_afk/games/aether_gazer/ops/combat/walk_forward.py`
- Create: `src/anime_game_afk/games/aether_gazer/ops/combat/README.md`
- Test: `tests/games/aether_gazer/ops/combat/test_combat.py`

**Purpose:** Battle-specific atomic ops extracted from ch6_battle.py key sequences and action handlers.

- [ ] Step 1: Create `combat/` directory with empty `__init__.py`
- [ ] Step 2: Create `attack_cycle.py` — one full rotation of battle keys
- [ ] Step 3: Create `handle_revive.py` — press Enter to accept revival
- [ ] Step 4: Create `walk_forward.py` — hold W for configurable duration
- [ ] Step 5: Create `README.md`
- [ ] Step 6: Write tests verifying key sequences
- [ ] Step 7: Run tests, commit

**attack_cycle.py:**
```python
"""One round of battle attack keys.

Presses the full attack rotation: J J U J I J O R 1 2
with configurable interval between keys. Takes ~2.5s at
default interval (0.25s * 10 keys).
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.constants import (
    BATTLE_KEY_INTERVAL,
)
from anime_game_afk.games.aether_gazer.knowledge.keys import (
    ATTACK_CYCLE_KEYS,
    key_name,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult


class AttackCycleOp:
    """Execute one full attack key rotation."""

    def __init__(self, interval: float = BATTLE_KEY_INTERVAL) -> None:
        self._interval = interval

    async def run(self, ctx: OpContext) -> OpResult:
        for i, vk in enumerate(ATTACK_CYCLE_KEYS):
            ctx.device.press_key(vk)
            if i % 5 == 0:
                ctx.logger.debug(
                    f"Attack key {i}/{len(ATTACK_CYCLE_KEYS)}: "
                    f"{key_name(vk)}"
                )
            await asyncio.sleep(self._interval)

        return OpResult(
            success=True,
            data={"keys_pressed": len(ATTACK_CYCLE_KEYS)},
        )
```

**handle_revive.py:**
```python
"""Handle revive prompt during battle.

When a character dies, the game shows a revival confirmation.
This op presses Enter to accept the revival.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ENTER
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult


class HandleReviveOp:
    """Accept revival prompt by pressing Enter."""

    def __init__(self, wait_after: float = 3.0) -> None:
        self._wait = wait_after

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.device.press_key(VK_ENTER)
        ctx.logger.info("Revive prompt: pressed Enter to accept")
        await asyncio.sleep(self._wait)
        return OpResult(success=True, data={"action": "revive_accepted"})
```

**walk_forward.py:**
```python
"""Walk forward by holding W key.

Used during exploration segments between battles.
Holds W for a configurable duration (default 2 seconds).
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.constants import (
    WALK_DEFAULT_DURATION,
)
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_W
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult


class WalkForwardOp:
    """Hold W to walk forward for a duration."""

    def __init__(self, duration: float = WALK_DEFAULT_DURATION) -> None:
        self._duration = duration

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.device.hold_key(VK_W, self._duration)
        ctx.logger.info(f"Walking forward for {self._duration}s")
        await asyncio.sleep(self._duration + 0.2)
        return OpResult(
            success=True,
            data={"direction": "forward", "duration": self._duration},
        )
```

**test_combat.py:**
```python
"""Tests for combat ops."""
import asyncio
from dataclasses import dataclass, field

import numpy as np

from anime_game_afk.games.aether_gazer.knowledge.keys import (
    ATTACK_CYCLE_KEYS,
    VK_ENTER,
    VK_W,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.games.aether_gazer.ops.combat.attack_cycle import (
    AttackCycleOp,
)
from anime_game_afk.games.aether_gazer.ops.combat.handle_revive import (
    HandleReviveOp,
)
from anime_game_afk.games.aether_gazer.ops.combat.walk_forward import (
    WalkForwardOp,
)


@dataclass
class MockDevice:
    click_log: list = field(default_factory=list)
    key_log: list = field(default_factory=list)
    hold_log: list = field(default_factory=list)

    def screenshot(self) -> np.ndarray:
        return np.zeros((900, 1600, 3), dtype=np.uint8)
    def click(self, x: int, y: int) -> None:
        self.click_log.append((x, y))
    def press_key(self, vk_code: int) -> None:
        self.key_log.append(vk_code)
    def hold_key(self, vk_code: int, duration_s: float) -> None:
        self.hold_log.append((vk_code, duration_s))


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_attack_cycle_presses_all_keys():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = AttackCycleOp(interval=0.0)
    result = _run(op.run(ctx))
    assert result.success
    assert len(device.key_log) == len(ATTACK_CYCLE_KEYS)
    assert device.key_log == list(ATTACK_CYCLE_KEYS)
    assert result.data["keys_pressed"] == 10


def test_attack_cycle_order():
    """Keys are in correct order: J J U J I J O R 1 2."""
    device = MockDevice()
    ctx = OpContext(device=device)
    _run(AttackCycleOp(interval=0.0).run(ctx))
    assert device.key_log[0] == 0x4A  # J
    assert device.key_log[2] == 0x55  # U
    assert device.key_log[4] == 0x49  # I
    assert device.key_log[6] == 0x4F  # O
    assert device.key_log[7] == 0x52  # R
    assert device.key_log[8] == 0x31  # 1
    assert device.key_log[9] == 0x32  # 2


def test_handle_revive():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = HandleReviveOp(wait_after=0.0)
    result = _run(op.run(ctx))
    assert result.success
    assert VK_ENTER in device.key_log
    assert result.data["action"] == "revive_accepted"


def test_walk_forward():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = WalkForwardOp(duration=1.5)
    result = _run(op.run(ctx))
    assert result.success
    assert (VK_W, 1.5) in device.hold_log
    assert result.data["duration"] == 1.5


def test_walk_forward_default_duration():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = WalkForwardOp()
    result = _run(op.run(ctx))
    assert result.success
    assert result.data["duration"] == 2.0
```

---

## Task 9: Integration — deprecation wrappers + full verification

**Files:**
- Modify: `src/anime_game_afk/games/aether_gazer/pages/__init__.py`
- Modify: `src/anime_game_afk/games/aether_gazer/__init__.py`
- Test: Run full test suite

**Purpose:** Keep old imports working temporarily. Verify all new code integrates correctly.

- [ ] Step 1: Add re-exports in `pages/__init__.py` pointing to new knowledge/ types
- [ ] Step 2: Run `pytest tests/games/aether_gazer/knowledge/ -v`
- [ ] Step 3: Run `pytest tests/games/aether_gazer/ops/ -v`
- [ ] Step 4: Verify no import cycles: `python -c "from anime_game_afk.games.aether_gazer.knowledge import pages, navigation, keys, resources, constants"`
- [ ] Step 5: Verify no cv2 in knowledge layer: `grep -r "import cv2" src/anime_game_afk/games/aether_gazer/knowledge/` (expect empty)
- [ ] Step 6: Commit with message "Wave 2 complete: knowledge + ops layers"

**pages/__init__.py deprecation wrapper:**
```python
"""Backward-compatible re-exports.

DEPRECATED: Import from knowledge/ instead.
This file will be removed after all consumers are migrated.
"""
import warnings

from anime_game_afk.games.aether_gazer.knowledge.pages import (
    ALL_PAGES,
    SAFE_PAGES,
    UNSAFE_PAGES,
    PageDef,
    PageElement,
    find_element,
    get_page,
)
from anime_game_afk.games.aether_gazer.knowledge.keys import (
    VK_ESCAPE,
    VK_G,
    VK_H,
    VK_J,
    VK_TAB,
)
from anime_game_afk.games.aether_gazer.knowledge.navigation import (
    NavAction,
    NavMethod,
)

warnings.warn(
    "Importing from pages/ is deprecated. Use knowledge/ instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Legacy aliases
Coord = None  # No longer needed — use Point directly
SAFE_PAGES_FROM_HUB = SAFE_PAGES

__all__ = [
    "ALL_PAGES", "SAFE_PAGES", "UNSAFE_PAGES",
    "PageDef", "PageElement",
    "VK_ESCAPE", "VK_TAB", "VK_J", "VK_G", "VK_H",
    "NavAction", "NavMethod",
]
```

---

## Summary: File count and line estimates

| Task | New files | Test files | Est. lines |
|------|-----------|------------|------------|
| 1: constants, keys, resources | 5 | 1 | ~180 |
| 2: pages.py (15 pages) | 1 | 1 | ~200 |
| 3: navigation.py | 1 | 1 | ~130 |
| 4: ops/base.py | 3 | 1 | ~100 |
| 5: perception/ (2 ops) | 4 | 2 | ~200 |
| 6: navigate/ (4 ops) | 6 | 1 | ~250 |
| 7: interact/ (4 ops) | 6 | 1 | ~200 |
| 8: combat/ (3 ops) | 5 | 1 | ~150 |
| 9: integration | 1 modify | 0 | ~30 |
| **Total** | **~32** | **~9** | **~1440** |
