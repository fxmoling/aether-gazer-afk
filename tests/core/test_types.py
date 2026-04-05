"""Tests for core type definitions: Point, Rect, Resolution."""
from __future__ import annotations

import pytest

from anime_game_afk.core.types import Point, Rect, Resolution


# ---------------------------------------------------------------------------
# Point
# ---------------------------------------------------------------------------


def test_point_construction() -> None:
    p = Point(x=10, y=20)
    assert p.x == 10
    assert p.y == 20


def test_point_equality() -> None:
    assert Point(3, 4) == Point(3, 4)
    assert Point(3, 4) != Point(4, 3)


def test_point_is_frozen() -> None:
    p = Point(1, 2)
    with pytest.raises(Exception):
        p.x = 99  # type: ignore[misc]


def test_point_hash() -> None:
    """Frozen dataclasses must be hashable (usable in sets/dicts)."""
    s = {Point(0, 0), Point(1, 1), Point(0, 0)}
    assert len(s) == 2


# ---------------------------------------------------------------------------
# Rect
# ---------------------------------------------------------------------------


def test_rect_construction() -> None:
    r = Rect(x=5, y=10, w=100, h=50)
    assert r.x == 5
    assert r.y == 10
    assert r.w == 100
    assert r.h == 50


def test_rect_x2_y2() -> None:
    r = Rect(x=5, y=10, w=100, h=50)
    assert r.x2 == 105
    assert r.y2 == 60


def test_rect_x2_y2_zero_origin() -> None:
    r = Rect(x=0, y=0, w=1600, h=900)
    assert r.x2 == 1600
    assert r.y2 == 900


def test_rect_contains_center() -> None:
    r = Rect(x=0, y=0, w=100, h=100)
    assert r.contains(Point(50, 50))


def test_rect_contains_top_left_corner() -> None:
    """Top-left corner is inclusive."""
    r = Rect(x=10, y=20, w=80, h=60)
    assert r.contains(Point(10, 20))


def test_rect_does_not_contain_right_edge() -> None:
    """Right and bottom edges are exclusive."""
    r = Rect(x=0, y=0, w=100, h=100)
    assert not r.contains(Point(100, 50))
    assert not r.contains(Point(50, 100))


def test_rect_does_not_contain_point_outside() -> None:
    r = Rect(x=10, y=10, w=50, h=50)
    assert not r.contains(Point(0, 0))
    assert not r.contains(Point(200, 200))


def test_rect_equality() -> None:
    assert Rect(0, 0, 100, 100) == Rect(0, 0, 100, 100)
    assert Rect(0, 0, 100, 100) != Rect(0, 0, 100, 99)


def test_rect_is_frozen() -> None:
    r = Rect(0, 0, 10, 10)
    with pytest.raises(Exception):
        r.w = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def test_resolution_construction() -> None:
    res = Resolution(width=1920, height=1080)
    assert res.width == 1920
    assert res.height == 1080


def test_resolution_equality() -> None:
    assert Resolution(1280, 720) == Resolution(1280, 720)
    assert Resolution(1280, 720) != Resolution(1920, 1080)


def test_resolution_is_frozen() -> None:
    res = Resolution(1280, 720)
    with pytest.raises(Exception):
        res.width = 100  # type: ignore[misc]


def test_resolution_hash() -> None:
    s = {Resolution(1280, 720), Resolution(1920, 1080), Resolution(1280, 720)}
    assert len(s) == 2
