"""Navigation graph for AetherGazer.

Defines page-to-page edges with action sequences.
Supports both hub-level navigation and sub-page drill-down.
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


# ── Hub-level navigation ──

_HUB_FORWARD: list[NavEdge] = [
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

_HUB_BACKWARD: list[NavEdge] = [
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

# ── Sub-page navigation (parent → child) ──

_SUB_FORWARD: list[NavEdge] = [
    # Shop sub-pages
    NavEdge("shop",              "shop_trade",        _click(89, 817)),
    NavEdge("shop",              "shop_supply",       _click(399, 816)),
    NavEdge("shop_trade",        "shop_daily",        _click(130, 125)),
    NavEdge("shop_trade",        "shop_trade_center", _click(130, 225)),
    NavEdge("shop_supply",       "shop_daily_supply", _click(560, 130)),
    # Battle sub-pages
    NavEdge("battle_select",     "battle_intel",      _click(195, 860)),
    NavEdge("battle_intel",      "main_story_map",    _click(533, 450)),
]

_SUB_BACKWARD: list[NavEdge] = [
    # Shop back to parent (all use back arrow to shop overview)
    NavEdge("shop_trade",        "shop",    _click(35, 35, 1.5)),
    NavEdge("shop_daily",        "shop",    _click(35, 35, 1.5)),
    NavEdge("shop_trade_center", "shop",    _click(35, 35, 1.5)),
    NavEdge("shop_supply",       "shop",    _click(35, 35, 1.5)),
    NavEdge("shop_daily_supply", "shop",    _click(35, 35, 1.5)),
    # Battle back
    NavEdge("battle_intel",      "battle_select", _click(35, 35, 1.5)),
    NavEdge("main_story_map",    "battle_select", _click(35, 35, 1.5)),
]

_ALL_EDGES = _HUB_FORWARD + _HUB_BACKWARD + _SUB_FORWARD + _SUB_BACKWARD


class NavGraph:
    """Navigation graph with multi-hop route finding.

    Supports hub-level pages and sub-page drill-down.
    find_route uses BFS to find shortest path between any two pages.
    """

    def __init__(self) -> None:
        self._edges: dict[tuple[str, str], NavEdge] = {}
        for edge in _ALL_EDGES:
            self._edges[(edge.source, edge.target)] = edge

    def get_edge(self, source: str, target: str) -> NavEdge | None:
        """Get direct edge between two pages."""
        return self._edges.get((source, target))

    def find_route(self, source: str, target: str) -> list[NavEdge] | None:
        """Find shortest route from source to target using BFS.

        Returns list of edges, or None if no route exists.
        Handles multi-hop paths (e.g. main_hub → shop → shop_trade → shop_daily).
        """
        if source == target:
            return []

        # Direct edge?
        direct = self.get_edge(source, target)
        if direct is not None:
            return [direct]

        # BFS for shortest path
        from collections import deque
        visited: set[str] = {source}
        # Queue: (current_page, path_of_edges)
        queue: deque[tuple[str, list[NavEdge]]] = deque()
        for edge in self.outgoing(source):
            queue.append((edge.target, [edge]))
            visited.add(edge.target)

        while queue:
            current, path = queue.popleft()
            if current == target:
                return path
            for edge in self.outgoing(current):
                if edge.target not in visited:
                    visited.add(edge.target)
                    queue.append((edge.target, path + [edge]))

        return None

    def outgoing(self, page_id: str) -> list[NavEdge]:
        """All edges from a given page."""
        return [e for (s, _), e in self._edges.items() if s == page_id]

    @property
    def edge_count(self) -> int:
        return len(self._edges)


# Module-level singleton
NAV_GRAPH = NavGraph()
