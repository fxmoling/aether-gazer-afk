"""Tests for vision result types: MatchResult and TextResult."""
from __future__ import annotations

import pytest

from anime_game_afk.core.types import Rect
from anime_game_afk.vision.types import MatchResult, TextResult


# ---------------------------------------------------------------------------
# MatchResult
# ---------------------------------------------------------------------------


def test_match_result_construction() -> None:
    m = MatchResult(score=0.95, x=10, y=20, w=50, h=30, matched=True)
    assert m.score == 0.95
    assert m.x == 10
    assert m.y == 20
    assert m.w == 50
    assert m.h == 30
    assert m.matched is True


def test_match_result_unmatched() -> None:
    m = MatchResult(score=0.5, x=0, y=0, w=20, h=20, matched=False)
    assert m.matched is False


def test_match_result_equality() -> None:
    a = MatchResult(score=0.9, x=5, y=5, w=10, h=10, matched=True)
    b = MatchResult(score=0.9, x=5, y=5, w=10, h=10, matched=True)
    assert a == b


def test_match_result_inequality_score() -> None:
    a = MatchResult(score=0.9, x=5, y=5, w=10, h=10, matched=True)
    b = MatchResult(score=0.8, x=5, y=5, w=10, h=10, matched=True)
    assert a != b


def test_match_result_inequality_position() -> None:
    a = MatchResult(score=0.9, x=5, y=5, w=10, h=10, matched=True)
    b = MatchResult(score=0.9, x=6, y=5, w=10, h=10, matched=True)
    assert a != b


def test_match_result_mutable() -> None:
    """MatchResult is a plain dataclass — fields can be updated after creation."""
    m = MatchResult(score=0.5, x=0, y=0, w=10, h=10, matched=False)
    m.score = 0.9
    m.matched = True
    assert m.score == 0.9
    assert m.matched is True


def test_match_result_zero_score() -> None:
    m = MatchResult(score=0.0, x=0, y=0, w=0, h=0, matched=False)
    assert m.score == 0.0
    assert m.matched is False


def test_match_result_perfect_score() -> None:
    m = MatchResult(score=1.0, x=100, y=200, w=40, h=40, matched=True)
    assert m.score == 1.0
    assert m.matched is True


# ---------------------------------------------------------------------------
# TextResult
# ---------------------------------------------------------------------------


def test_text_result_construction() -> None:
    region = Rect(x=10, y=20, w=100, h=30)
    t = TextResult(text="hello", confidence=0.98, region=region)
    assert t.text == "hello"
    assert t.confidence == 0.98
    assert t.region == region


def test_text_result_empty_string() -> None:
    region = Rect(x=0, y=0, w=50, h=20)
    t = TextResult(text="", confidence=0.0, region=region)
    assert t.text == ""
    assert t.confidence == 0.0


def test_text_result_equality() -> None:
    r = Rect(0, 0, 100, 50)
    a = TextResult(text="OK", confidence=0.9, region=r)
    b = TextResult(text="OK", confidence=0.9, region=r)
    assert a == b


def test_text_result_inequality_text() -> None:
    r = Rect(0, 0, 100, 50)
    a = TextResult(text="OK", confidence=0.9, region=r)
    b = TextResult(text="Cancel", confidence=0.9, region=r)
    assert a != b


def test_text_result_inequality_confidence() -> None:
    r = Rect(0, 0, 100, 50)
    a = TextResult(text="OK", confidence=0.9, region=r)
    b = TextResult(text="OK", confidence=0.5, region=r)
    assert a != b


def test_text_result_inequality_region() -> None:
    a = TextResult(text="OK", confidence=0.9, region=Rect(0, 0, 100, 50))
    b = TextResult(text="OK", confidence=0.9, region=Rect(10, 0, 100, 50))
    assert a != b


def test_text_result_mutable() -> None:
    """TextResult is a plain dataclass — fields can be updated."""
    r = Rect(0, 0, 100, 50)
    t = TextResult(text="old", confidence=0.5, region=r)
    t.text = "new"
    assert t.text == "new"


def test_text_result_unicode() -> None:
    r = Rect(0, 0, 200, 40)
    t = TextResult(text="深空之眼", confidence=0.85, region=r)
    assert t.text == "深空之眼"
