"""OCR interface — text recognition.

Currently uses template matching for known text snippets.
Designed so a real OCR backend (pytesseract, paddleocr) can be
swapped in later without changing callers.
"""
from __future__ import annotations

import numpy as np

from anime_game_afk.core.types import Rect
from anime_game_afk.vision.matcher import match_template
from anime_game_afk.vision.types import TextResult


def recognize_text(
    image: np.ndarray,
    region: Rect | None = None,
    templates: dict[str, np.ndarray] | None = None,
    threshold: float = 0.7,
) -> list[TextResult]:
    """Recognize text in an image region via template matching.

    Each key in *templates* is the text string to report; the corresponding
    value is a template image representing that text's visual appearance.
    When a template matches above *threshold*, a :class:`TextResult` is emitted
    with the matched coordinates and score as its confidence.

    A real OCR backend (pytesseract, paddleocr, etc.) can replace this function
    without any changes to callers — the signature is intentionally backend-
    agnostic.

    Args:
        image: BGR (or greyscale) source image to search.
        region: Optional sub-region to restrict the search.
        templates: Mapping of ``{text_label: template_image}``.  When ``None``
                   or empty, an empty list is returned immediately.
        threshold: Minimum match score (0.0–1.0) to consider a match.

    Returns:
        List of :class:`TextResult` sorted by confidence descending.
        Empty list when no templates are provided or no match meets the
        threshold.
    """
    if not templates:
        return []

    results: list[TextResult] = []
    for text, tpl in templates.items():
        match = match_template(image, tpl, region=region, threshold=threshold)
        if match.matched:
            results.append(
                TextResult(
                    text=text,
                    confidence=match.score,
                    region=Rect(match.x, match.y, match.w, match.h),
                )
            )

    results.sort(key=lambda r: r.confidence, reverse=True)
    return results
