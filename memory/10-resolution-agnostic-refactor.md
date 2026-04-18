# Resolution-Agnostic Vision Pipeline Refactor (2026-04-17)

## Summary

Refactored the entire vision pipeline from hardcoded 1600×900 design resolution to
resolution-agnostic fractional coordinates. The system now works correctly with any
game window size and aspect ratio.

## Key Changes

### Device Layer (`core/device.py`)
- **MAX_HEIGHT = 720**: Screenshots proportionally scaled so height ≤ 720, aspect ratio preserved, never upscaled
- **Fractional click/swipe**: `device.click(fx, fy)` accepts [0.0, 1.0] values, converts to actual window pixels
- **Removed**: `design_resolution`, `_scale_x`, `_scale_y` from DeviceAdapter and DeviceConfig
- **`resolution` property**: Returns current screenshot output (w, h) for OCR coordinate conversion

### Coordinate Convention
- **All game logic uses fractional coords [0.0, 1.0]**
- (0.0, 0.0) = top-left, (1.0, 1.0) = bottom-right, (0.5, 0.5) = center
- `ClickOp(x=fx, y=fy)` — for fractional coords (page elements, nav actions)
- `ClickPxOp(px=cx, py=cy)` — for OCR/vision pixel coords (auto-converts via `device.resolution`)
- `RapidClickPxAction(px=cx, py=cy)` — multi-click version for OCR pixel coords

### Navigation & Pages
- `NavAction.coord` changed from `Point(int, int)` to `tuple[float, float]`
- `PageElement.coord` changed from `Point(int, int)` to `tuple[float, float]`
- All ~90 page elements and ~40 nav actions converted to fractional

### Vision Layer
- `index.json`: Search regions stored as fractional [0..1], added `ref_height: 900`
- `identify_page.py`: Templates scaled at runtime (`screenshot_h / ref_height`)
- Existing template PNGs (captured at 1600×900) work via proportional scaling

### Constants Removed
- `DESIGN_RESOLUTION`, `SCREEN_CENTER_X/Y`, `BACK_BUTTON_X/Y` from constants.py
- `_DESIGN_W`, `_DESIGN_H`, `_to_px()` from primitives.py

## Commits
- Wave 1: `362a759` — device.py + types.py
- Wave 2: `8add64c` — primitives.py + constants.py
- Wave 3: `2e899fc` — navigation, pages, tasks + ClickPxOp
- Wave 4: `f1d518d` — vision pipeline (identify_page + index.json)
- Wave 5: `2475400` — all tests updated (534 passing)

## Config Cleanup (post-refactor)

- **Deleted** `core/session.py` (GameSession) — fully replaced by DeviceAdapter
- **Deleted** `games/aether_gazer/adapter.py` — empty wrapper around GameSession
- **Deleted** `GameConfig.design_resolution` field — no consumers remain
- **DeviceConfig** all fields now required (no unsafe defaults)
- **GameConfig.to_device_config()** — single-point conversion, eliminates boilerplate
- Commit: `0d49348`

## identify_page.py Behavior (2026-04-18 rewrite)

- **Per-template thresholds**: Each template in index.json can have `"threshold"` field
- **Mask support**: `"mask": "circle"` generates circular mask at load time
- **Stricter matching**: ALL templates for a page must individually pass their thresholds
  (old: average score >= global threshold; new: each template checked independently)
- **Masked matching**: Forces `TM_CCORR_NORMED` (OpenCV requirement for masks)
- **_prepare_mask()**: Scales with INTER_NEAREST + re-binarize for clean {0,255} values

## Design Spec
`docs/superpowers/specs/2026-04-17-resolution-agnostic-pipeline-design.md`
