"""Tests for knowledge.navigation module."""
from anime_game_afk.games.aether_gazer.knowledge.navigation import (
    NAV_GRAPH,
    NavMethod,
)


def test_edge_count():
    """14 forward + 14 backward = 28 edges."""
    assert NAV_GRAPH.edge_count == 42


def test_direct_forward_edge():
    edge = NAV_GRAPH.get_edge("main_hub", "shop")
    assert edge is not None
    assert edge.action.method == NavMethod.CLICK
    assert edge.action.coord is not None
    fx, fy = edge.action.coord
    assert abs(fx - 0.569) < 0.01


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
