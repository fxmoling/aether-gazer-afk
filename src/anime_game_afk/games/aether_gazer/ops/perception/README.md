# perception/ — Perception Ops (Layer 5)

"See" ops — identify the current page and detect game state.

## Files
| File | Purpose |
|------|---------|
| identify_page.py | Load page templates, match screenshot, return page_id |
| detect_game_state.py | Match text templates, detect battle/cutscene/etc. |

## Key Functions
- `identify(screenshot)` → `(page_id, confidence)` — pure utility
- `is_on_page(screenshot, page_id)` → bool — quick check
- `detect_state(screenshot)` → `(GameState, confidence)` — pure utility

## Notes
- Templates loaded lazily and cached at module level
- Black screen (mean < 15) → LOADING state (no template needed)
- No templates in test env → returns "unknown"/UNKNOWN
