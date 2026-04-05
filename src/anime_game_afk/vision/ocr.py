"""OCR interface — text recognition.

Two backends:
1. RapidOCR (primary) — real OCR using PaddleOCR ONNX models.
   Recognizes arbitrary Chinese/English text from screenshots.
2. Template matching (fallback) — matches pre-cropped text images.
   Used when RapidOCR is unavailable or for known fixed text.

RapidOCR is the default. Template matching is kept as a fallback
for environments where ONNX runtime is not available.
"""
from __future__ import annotations

import numpy as np
from loguru import logger as _loguru

from anime_game_afk.core.types import Rect
from anime_game_afk.vision.matcher import match_template
from anime_game_afk.vision.types import MatchResult, TextResult

# Lazy-loaded RapidOCR engine (initialized on first use)
_ocr_engine = None
_ocr_available: bool | None = None


def _get_ocr_engine():
    """Lazy-initialize RapidOCR engine. Returns None if unavailable."""
    global _ocr_engine, _ocr_available
    if _ocr_available is not None:
        return _ocr_engine

    try:
        from rapidocr_onnxruntime import RapidOCR
        _ocr_engine = RapidOCR()
        _ocr_available = True
        _loguru.info("RapidOCR engine initialized")
    except ImportError:
        _ocr_engine = None
        _ocr_available = False
        _loguru.warning(
            "RapidOCR not installed — falling back to template matching. "
            "Install with: pip install rapidocr_onnxruntime"
        )
    return _ocr_engine


def recognize_text(
    image: np.ndarray,
    region: Rect | None = None,
    templates: dict[str, np.ndarray] | None = None,
    threshold: float = 0.7,
) -> list[TextResult]:
    """Recognize text in an image region.

    When *templates* are provided, uses template matching (exact image match).
    When *templates* is None, uses RapidOCR for real text recognition.

    Args:
        image: BGR source image.
        region: Optional sub-region to restrict the search.
        templates: If provided, uses template matching instead of OCR.
                   Mapping of ``{text_label: template_image}``.
        threshold: Minimum confidence (0.0-1.0) to include a result.

    Returns:
        List of TextResult sorted by confidence descending.
    """
    # Explicit templates → always use template matching
    if templates is not None:
        return _template_recognize(image, region, templates, threshold)

    # No templates → use real OCR
    engine = _get_ocr_engine()
    if engine is not None:
        return _ocr_recognize(engine, image, region, threshold)
    else:
        return []


def ocr_full(
    image: np.ndarray,
    region: Rect | None = None,
    threshold: float = 0.5,
) -> list[TextResult]:
    """Full OCR — recognize ALL text in image/region.

    Requires RapidOCR. Returns empty list if not available.
    This is the primary API for reading arbitrary game text.

    Args:
        image: BGR source image (1600x900 or any size).
        region: Optional sub-region to crop before OCR.
        threshold: Minimum confidence to include.

    Returns:
        List of TextResult with text, confidence, and bounding box.
    """
    engine = _get_ocr_engine()
    if engine is None:
        _loguru.error("ocr_full requires RapidOCR but it's not installed")
        return []
    return _ocr_recognize(engine, image, region, threshold)


def ocr_find(
    image: np.ndarray,
    target: str,
    region: Rect | None = None,
    threshold: float = 0.5,
) -> TextResult | None:
    """Find specific text in image. Returns the best match or None.

    Uses substring matching — target "情报" will match "朔望情报".

    Args:
        image: BGR source image.
        target: Text to search for (substring match).
        region: Optional sub-region to restrict search.
        threshold: Minimum OCR confidence.

    Returns:
        TextResult if found, None if not found.
    """
    results = ocr_full(image, region, threshold)
    matches = [r for r in results if target in r.text]
    if not matches:
        return None
    # Return highest confidence match
    return max(matches, key=lambda r: r.confidence)


def ocr_find_all(
    image: np.ndarray,
    target: str,
    region: Rect | None = None,
    threshold: float = 0.5,
) -> list[TextResult]:
    """Find all occurrences of text in image.

    Args:
        image: BGR source image.
        target: Text to search for (substring match).
        region: Optional sub-region.
        threshold: Minimum OCR confidence.

    Returns:
        List of matching TextResult, sorted by confidence descending.
    """
    results = ocr_full(image, region, threshold)
    return [r for r in results if target in r.text]


# ── Internal implementations ──


def _ocr_recognize(
    engine,
    image: np.ndarray,
    region: Rect | None,
    threshold: float,
) -> list[TextResult]:
    """Run RapidOCR on image, return TextResults."""
    if region is not None:
        h, w = image.shape[:2]
        x1 = max(0, region.x)
        y1 = max(0, region.y)
        x2 = min(w, region.x + region.w)
        y2 = min(h, region.y + region.h)
        cropped = image[y1:y2, x1:x2]
        offset_x, offset_y = x1, y1
    else:
        cropped = image
        offset_x, offset_y = 0, 0

    result, _ = engine(cropped)
    if not result:
        return []

    texts: list[TextResult] = []
    for line in result:
        box, text, conf = line
        if conf < threshold:
            continue
        # box is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] — take bounding rect
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        bx = int(min(xs)) + offset_x
        by = int(min(ys)) + offset_y
        bw = int(max(xs) - min(xs))
        bh = int(max(ys) - min(ys))
        texts.append(TextResult(
            text=text,
            confidence=float(conf),
            region=Rect(bx, by, bw, bh),
        ))

    texts.sort(key=lambda r: r.confidence, reverse=True)
    return texts


def _template_recognize(
    image: np.ndarray,
    region: Rect | None,
    templates: dict[str, np.ndarray] | None,
    threshold: float,
) -> list[TextResult]:
    """Fallback: template matching for known text snippets."""
    if not templates:
        return []

    results: list[TextResult] = []
    for text, tpl in templates.items():
        match = match_template(image, tpl, region=region, threshold=threshold)
        if match.matched:
            results.append(TextResult(
                text=text,
                confidence=match.score,
                region=Rect(match.x, match.y, match.w, match.h),
            ))

    results.sort(key=lambda r: r.confidence, reverse=True)
    return results
