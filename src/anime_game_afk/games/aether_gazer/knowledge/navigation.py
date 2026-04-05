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
