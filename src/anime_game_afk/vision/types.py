"""Result types for vision operations."""
from __future__ import annotations

from dataclasses import dataclass

from anime_game_afk.core.types import Rect


@dataclass
class MatchResult:
    """Result of a template matching operation.

    Coordinates (x, y) are the top-left corner of the matched region in the
    source image (already offset if a region was used).  w and h mirror the
    template dimensions.  ``matched`` is True when score >= threshold.
    """

    score: float
    x: int
    y: int
    w: int
    h: int
    matched: bool  # score >= threshold


@dataclass
class TextResult:
    """Result of a text recognition operation."""

    text: str
    confidence: float
    region: Rect
