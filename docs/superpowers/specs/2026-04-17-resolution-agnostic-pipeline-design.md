# Resolution-Agnostic Vision Pipeline

## Problem

The current vision pipeline forces all screenshots to 1600×900, causing:
1. **Aspect ratio distortion** — non-16:9 windows (4:3, 21:9) get stretched, breaking template matching
2. **Wasted resources** — high-res screenshots (4K) processed at unnecessary size
3. **Hardcoded design resolution** — duplicated in 3 places (`device.py`, `primitives.py`, `goto_page.py`)
4. **Hub detection unreliable** — template includes dynamic character model
5. **No icon-level matching** — all button location relies on OCR (~2s), template matching only used for page identification

## Scope

Full pipeline redesign covering:
- Screenshot capture pipeline (proportional scaling)
- Coordinate system (unified fractional)
- Template matching adaptation (dynamic scaling)
- Hub detection fix (small stable icons + voting)
- Icon template mechanism (element-level matching)

Existing templates will be re-captured after implementation.

## Design

### 1. Screenshot Pipeline

**Remove fixed design resolution. Scale proportionally with height cap.**

```
capture(native) → h > MAX_HEIGHT? → scale down proportionally → output
                         ↓ no
                    output as-is (never upscale)
```

Constants:
- `MAX_HEIGHT = 720` (configurable)
- Scaling preserves aspect ratio (INTER_AREA for downscale)

Examples:
- 1920×1080 (16:9) → 1280×720
- 1024×768 (4:3) → 960×720
- 2560×1440 (16:9) → 1280×720
- 1280×720 → unchanged
- 640×480 → unchanged (never upscale)

`DeviceAdapter` changes:
- `screenshot()` returns image at proportionally-scaled resolution (not fixed)
- `screenshot_raw()` unchanged (native resolution)
- New property `resolution -> (width, height)` exposing current output size
- Remove `_design` resolution concept entirely
- Remove `_scale_x`, `_scale_y` based on design resolution

### 2. Coordinate System — Unified Fractional

**All positions as `(fx, fy)` where `0.0 ≤ fx ≤ 1.0`, `0.0 ≤ fy ≤ 1.0`.**

`DeviceAdapter.click(fx, fy)`:
- Converts: `pixel_x = int(fx * actual_window_width)`
- Converts: `pixel_y = int(fy * actual_window_height)`
- Uses actual window resolution (not screenshot resolution) for click targeting

`DeviceAdapter.swipe(fx1, fy1, fx2, fy2, duration_ms)`:
- Same fractional conversion

Impact:
- `ClickOp` / `SwipeOp`: remove `_to_px()` helper and `_DESIGN_W`/`_DESIGN_H` constants; pass fractional directly to device
- `navigation.py`: convert all `_click(675, 850)` → `_click(0.422, 0.944)` fractional
- `goto_page.py`: remove manual `x / 1600, y / 900` runtime conversion
- `recovery.py`: replace `device.click(800, 450)` with fractional `device.click(0.5, 0.5)`

### 3. Template Matching Adaptation

**Templates store a reference height. At match time, scale template to match screenshot height.**

Template index format change (`index.json`):
```json
{
  "main_hub": [{
    "path": "assets/aether_gazer/templates/hub_navbar.png",
    "ref_height": 720,
    "search": [0.31, 0.89, 1.0, 1.0]
  }]
}
```

Changes:
- `search` regions: pixel `[x1, y1, x2, y2]` → fractional `[fx1, fy1, fx2, fy2]`
- New `ref_height` field per template (height of screenshot when template was captured)
- `size` and `crop` fields removed (derivable from the PNG itself)

Match-time logic in `matcher.py`:
```python
scale = screenshot_height / template_ref_height
if abs(scale - 1.0) > 0.05:
    template = cv2.resize(template, None, fx=scale, fy=scale, interpolation=INTER_AREA)
# then matchTemplate as before
```

Region conversion:
```python
h, w = screenshot.shape[:2]
x1, y1 = int(fx1 * w), int(fy1 * h)
x2, y2 = int(fx2 * w), int(fy2 * h)
search_area = screenshot[y1:y2, x1:x2]
```

### 4. Hub Detection Fix

**Replace single large template (includes character model) with multiple small stable icons + voting.**

New hub detection strategy:
- 3-4 small icon templates from stable UI elements (e.g., stamina icon top-left, currency icon, a fixed navbar icon)
- Each icon has its own fractional search region
- **Voting**: ≥2 icons matched → hub confirmed
- **Idle mode**: zero icons matched → send ESC to wake UI, re-check

Benefits:
- Small icons are stable across character changes, animations, effects
- Voting is resilient to partial occlusion (overlays, popups)
- Much faster than OCR fallback (~5ms per icon vs ~2s for OCR)

### 5. Icon Template Mechanism

**New element-level matching alongside existing page-level matching.**

Two template categories:
1. **Page templates** (`templates/index.json`) — "which page am I on?" (existing, refactored)
2. **Icon templates** (`icons/index.json`) — "where is this specific element?" (new)

Icon index format:
```json
{
  "hub_stamina_icon": {
    "path": "icons/hub_stamina.png",
    "ref_height": 720,
    "search": [0.0, 0.0, 0.15, 0.1]
  },
  "battle_start_button": {
    "path": "icons/battle_start.png",
    "ref_height": 720,
    "search": [0.7, 0.8, 1.0, 1.0]
  }
}
```

API (new functions in `vision/matcher.py` or new `vision/icons.py`):
```python
def find_icon(screenshot, icon_name) -> MatchResult | None:
    """Find a named icon on screen. Returns position or None."""

def find_icons(screenshot, icon_names) -> dict[str, MatchResult]:
    """Find multiple icons in one pass. Returns {name: result} for matched icons."""
```

Use cases:
- Hub detection (Section 4)
- Button location (replace some OCR calls)
- State detection (button enabled/disabled via different icon variants)

### 6. OCR Impact

Minimal changes needed:
- `ocr_once()` region parameter: change callers from pixel `Rect` to fractional, convert internally
- `OCR_SCALE` may become unnecessary — screenshots already at 720p, close to the effective OCR resolution (was 1600×0.7 = 1120×630, now 1280×720 natively)
- Evaluate whether `OCR_SCALE=1.0` works at 720p (skip double-scaling)

### 7. File Changes Summary

| File | Change |
|------|--------|
| `core/device.py` | Remove design_resolution, proportional scaling, fractional click/swipe |
| `core/types.py` | Remove or update Resolution/design_resolution references |
| `ops/primitives.py` | Remove `_DESIGN_W/H`, `_to_px()`; pass fractional to device |
| `ops/navigate/goto_page.py` | Remove manual `/1600, /900` conversion |
| `ops/navigate/smart_return.py` | Already fractional, minor adjustments |
| `ops/navigate/wake_hub_ui.py` | Already fractional, minor adjustments |
| `orchestrator/recovery.py` | Replace pixel `device.click()` with fractional |
| `knowledge/navigation.py` | All coords → fractional |
| `vision/matcher.py` | Add template scaling, fractional region support |
| `vision/ocr.py` | Fractional region support, evaluate OCR_SCALE |
| `checks/page.py` | AtHubCheck rewrite (multi-icon voting) |
| `checks/vision.py` | TemplateMatchCheck: fractional region |
| `ops/perception/identify_page.py` | Load fractional regions, pass ref_height |
| `assets/.../templates/index.json` | Fractional search regions, add ref_height |
| `assets/.../icons/` (new) | New icon template directory + index.json |

### 8. Migration Notes

- Existing 20 page templates will be re-captured at 720p after implementation
- Icon templates for hub detection will be captured fresh
- All pixel coordinates in navigation.py converted to fractional (one-time calculation: `px / 1600` for x, `px / 900` for y based on original mapping)
- Tests updated to work with new coordinate system
