"""Image I/O that handles non-ASCII paths on Windows.

``cv2.imread`` / ``cv2.imwrite`` fail when the file path contains
Chinese characters (or other non-ASCII) on Windows.  These helpers
route through numpy buffers to bypass OpenCV's path handling.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def imread(path: str | Path, flags: int = cv2.IMREAD_COLOR) -> np.ndarray | None:
    """Read an image, supporting non-ASCII paths on Windows."""
    try:
        data = np.fromfile(str(path), dtype=np.uint8)
    except (OSError, FileNotFoundError):
        return None
    if data.size == 0:
        return None
    img = cv2.imdecode(data, flags)
    return img


def imwrite(
    path: str | Path,
    img: np.ndarray,
    params: list[int] | None = None,
) -> bool:
    """Write an image, supporting non-ASCII paths on Windows."""
    p = Path(path)
    ext = p.suffix if p.suffix else ".png"
    encode_params = params if params is not None else []
    success, buf = cv2.imencode(ext, img, encode_params)
    if not success:
        return False
    buf.tofile(str(p))
    return True
