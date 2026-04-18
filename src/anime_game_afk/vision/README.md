# vision/ — Vision Toolkit (Layer 2)

Game-agnostic computer vision tools. Pure functions: image in, results out.

## Files

| File | Purpose |
|------|---------|
| `types.py` | `MatchResult`, `TextResult` dataclasses |
| `matcher.py` | Template matching (`cv2.matchTemplate` wrapper) |
| `geometry.py` | Crop, resize, contour detection *(planned)* |
| `color.py` | HSV colour detection *(planned)* |
| `ocr.py` | OCR interface — template-based initially *(planned)* |

## Rules

- Stateless pure functions only
- No device access, no file I/O, no game resources
- Callers pass images in (`np.ndarray`), get results out
- Only imports from `core.types`

## Usage

```python
import cv2
import numpy as np
from anime_game_afk.core.types import Rect
from anime_game_afk.vision.matcher import match_template, match_best, match_all

# Load images however you like (device capture, file, etc.)
image: np.ndarray = ...
template: np.ndarray = cv2.imread("template.png", cv2.IMREAD_GRAYSCALE)

# Single template search
result = match_template(image, template, threshold=0.8)
if result.matched:
    print(f"Found at ({result.x}, {result.y}) with score {result.score:.3f}")

# Search within a sub-region
region = Rect(x=100, y=50, w=400, h=300)
result = match_template(image, template, region=region, threshold=0.8)

# Best of many templates
result = match_best(image, [tmpl_a, tmpl_b, tmpl_c], threshold=0.75)

# All occurrences (non-maximum suppression applied)
results = match_all(image, template, threshold=0.8)
for r in results:
    print(f"  ({r.x}, {r.y})  score={r.score:.3f}")
```

## Scoring Convention

All functions use **higher = better** scoring regardless of the underlying
`cv2` method:

- `TM_CCOEFF_NORMED`, `TM_CCORR_NORMED` — raw score (already higher = better)
- `TM_SQDIFF`, `TM_SQDIFF_NORMED` — score inverted to `1 - raw_value`

`MatchResult.matched` is `True` when `score >= threshold`.
