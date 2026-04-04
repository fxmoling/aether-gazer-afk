"""页面模块"""

from anime_game_afk.games.aether_gazer.pages.definitions import (
    ALL_PAGES,
    SAFE_PAGES_FROM_HUB,
    UNSAFE_PAGES,
    Coord,
    InteractiveElement,
    NavAction,
    NavMethod,
    PageDef,
    Region,
    TextFeature,
    TextReliability,
)
from anime_game_afk.games.aether_gazer.pages.identifier import (
    check_bottom_nav_present,
    identify_page,
    is_on_page,
)

__all__ = [
    "ALL_PAGES",
    "SAFE_PAGES_FROM_HUB",
    "UNSAFE_PAGES",
    "Coord",
    "InteractiveElement",
    "NavAction",
    "NavMethod",
    "PageDef",
    "Region",
    "TextFeature",
    "TextReliability",
    "check_bottom_nav_present",
    "identify_page",
    "is_on_page",
]
