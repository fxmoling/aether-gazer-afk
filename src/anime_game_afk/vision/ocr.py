"""OCR interface — text recognition.

Two backends:
1. RapidOCR (primary) — real OCR using PaddleOCR ONNX models.
   Recognizes arbitrary Chinese/English text from screenshots.
2. Template matching (fallback) — matches pre-cropped text images.
   Used when RapidOCR is unavailable or for known fixed text.

Performance guidelines (measured 2026-04-06):
- ocr_find on 1600x900: ~3000ms per call (full OCR each time!)
- ocr_full on 800x450:  ~2000ms (same accuracy, 40% faster)
- Multiple ocr_find on same image → use OcrResult.find() instead

Preferred pattern (batch):
    result = ocr_once(image)  # one OCR pass at half-res
    battle = result.find("前往作战")
    explore = result.find("探测")

Legacy pattern (slow, avoid):
    battle = ocr_find(image, "前往作战")   # 3s
    explore = ocr_find(image, "探测")      # 3s more!
"""
from __future__ import annotations

import time

import cv2
import numpy as np
from loguru import logger as _loguru

from anime_game_afk.core.types import Rect
from anime_game_afk.vision.types import TextResult

# Lazy-loaded RapidOCR engine (initialized on first use)
_ocr_engine = None
_ocr_available: bool | None = None


def _get_ocr_engine():
    """Lazy-initialize RapidOCR engine. Returns None if unavailable.

    Tries DirectML (GPU) first, falls back to CPU with a clear log
    line explaining why so users on GPU-less systems aren't confused.
    """
    global _ocr_engine, _ocr_available
    if _ocr_available is not None:
        return _ocr_engine

    try:
        from rapidocr_onnxruntime import RapidOCR

        # Try DirectML (GPU) first — works on virtually all Win10+
        # systems with a DirectX 12 capable GPU (NVIDIA / AMD / Intel iGPU
        # since 2015).  Fails gracefully on RDP / VMs without GPU passthrough.
        try:
            import onnxruntime as ort
            providers = ort.get_available_providers()
            if "DmlExecutionProvider" in providers:
                _ocr_engine = RapidOCR(
                    det_use_dml=True, rec_use_dml=True, cls_use_dml=True,
                )
                _ocr_available = True
                _loguru.info(
                    "RapidOCR engine initialized (DirectML GPU) — "
                    "expect ~200ms per call"
                )
                return _ocr_engine
            else:
                _loguru.warning(
                    "DmlExecutionProvider not available (providers={}). "
                    "Falling back to CPU OCR (~1500ms per call). "
                    "If you have a DirectX 12 GPU, reinstall onnxruntime: "
                    "pip uninstall onnxruntime -y && pip install onnxruntime-directml",
                    providers,
                )
        except Exception as exc:
            _loguru.warning(
                "DirectML init failed, falling back to CPU OCR "
                "(~1500ms per call): {}", exc,
            )

        # CPU fallback — slower but works everywhere
        _ocr_engine = RapidOCR()
        _ocr_available = True
        _loguru.info(
            "RapidOCR engine initialized (CPU) — expect ~1500ms per call"
        )
    except Exception as exc:
        _ocr_engine = None
        _ocr_available = False
        _loguru.error(
            "RapidOCR initialization failed — OCR is unavailable. "
            "This is usually a packaging/runtime issue, not a game/admin "
            "permission issue. Error: {!r}",
            exc,
        )
    return _ocr_engine


# ── Batch OCR (preferred API) ──


# Default OCR scale factor: 0.7 = resize 1600x900 → 1120x630
# 0.7 gives reliable accuracy across all screenshots (~20% faster than 1.0)
# 0.5 is faster but unreliably drops "前往作战". 0.7 is the sweet spot.
OCR_SCALE = 0.7


class OcrResult:
    """Cached result of a single OCR pass. Search without re-running OCR.

    Usage:
        result = ocr_once(image)
        btn = result.find("前往作战")       # TextResult | None
        all_items = result.find_all("情报")  # list[TextResult]
        if result.has("探测"):              # bool
            ...

    Coordinates in TextResult.region are in the ORIGINAL image resolution
    (auto-scaled back from the OCR resolution).
    """

    __slots__ = ("_items",)

    def __init__(self, items: list[TextResult]) -> None:
        self._items = items

    @property
    def items(self) -> list[TextResult]:
        """All recognized text items."""
        return self._items

    def find(self, target: str) -> TextResult | None:
        """Find best match containing *target* substring."""
        matches = [r for r in self._items if target in r.text]
        if not matches:
            return None
        return max(matches, key=lambda r: r.confidence)

    def find_all(self, target: str) -> list[TextResult]:
        """Find all matches containing *target* substring."""
        return [r for r in self._items if target in r.text]

    def has(self, target: str) -> bool:
        """Check if any text contains *target*."""
        return any(target in r.text for r in self._items)

    def has_all(self, *targets: str) -> bool:
        """Check if ALL targets are found."""
        return all(self.has(t) for t in targets)

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return f"OcrResult({len(self._items)} items)"


def ocr_once(
    image: np.ndarray,
    region: Rect | None = None,
    scale: float = OCR_SCALE,
    threshold: float = 0.5,
) -> OcrResult:
    """Run OCR once, return searchable result. Preferred API.

    Resizes image to *scale* factor before OCR for speed, then maps
    coordinates back to original resolution.

    Args:
        image: BGR source image (typically 1600x900).
        region: Optional sub-region to crop BEFORE scaling.
                Coordinates are in original image space.
        scale: Resize factor (0.5 = half-res). Set 1.0 to skip resize.
        threshold: Minimum OCR confidence.

    Returns:
        OcrResult with coordinates in original image space.
    """
    engine = _get_ocr_engine()
    if engine is None:
        return OcrResult([])

    # Crop region first (in original coords)
    if region is not None:
        h, w = image.shape[:2]
        x1 = max(0, region.x)
        y1 = max(0, region.y)
        x2 = min(w, region.x + region.w)
        y2 = min(h, region.y + region.h)
        if x2 <= x1 or y2 <= y1:
            return OcrResult([])
        cropped = image[y1:y2, x1:x2]
        offset_x, offset_y = x1, y1
    else:
        cropped = image
        offset_x, offset_y = 0, 0

    # Scale down for speed
    if scale != 1.0 and scale > 0:
        sh, sw = cropped.shape[:2]
        new_w = int(sw * scale)
        new_h = int(sh * scale)
        if new_w > 0 and new_h > 0:
            scaled = cv2.resize(cropped, (new_w, new_h))
            inv_scale = 1.0 / scale
        else:
            scaled = cropped
            inv_scale = 1.0
    else:
        scaled = cropped
        inv_scale = 1.0

    _start = time.perf_counter()
    result, _ = engine(scaled)
    _elapsed_ms = (time.perf_counter() - _start) * 1000
    _loguru.debug(
        "ocr_once: {:.0f}ms, {} items found (scale={}, region={})",
        _elapsed_ms, len(result) if result else 0, scale, region,
    )
    if not result:
        _loguru.debug("ocr_once returned empty results for region {}", region)
        return OcrResult([])

    items: list[TextResult] = []
    for line in result:
        box, text, conf = line
        if conf < threshold:
            continue
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        # Map back to original resolution
        bx = int(min(xs) * inv_scale) + offset_x
        by = int(min(ys) * inv_scale) + offset_y
        bw = int((max(xs) - min(xs)) * inv_scale)
        bh = int((max(ys) - min(ys)) * inv_scale)
        items.append(TextResult(
            text=text,
            confidence=float(conf),
            region=Rect(bx, by, bw, bh),
        ))

    items.sort(key=lambda r: r.confidence, reverse=True)
    return OcrResult(items)


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

    _start = time.perf_counter()
    result, _ = engine(cropped)
    _elapsed_ms = (time.perf_counter() - _start) * 1000
    _loguru.debug(
        "_ocr_recognize: {:.0f}ms, {} items found (region={})",
        _elapsed_ms, len(result) if result else 0, region,
    )
    if not result:
        _loguru.debug("_ocr_recognize returned empty results for region {}", region)
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
