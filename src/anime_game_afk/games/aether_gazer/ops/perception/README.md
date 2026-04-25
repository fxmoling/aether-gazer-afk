# perception/ — Perception Ops (Layer 5)

"See" ops — identify the current page from screenshots.

## Files
| File | Purpose |
|------|---------|
| identify_page.py | Load page templates, match screenshot, return page_id |

## Key Functions
- `identify(screenshot)` → `(page_id, confidence)` — pure utility
- `is_on_page(screenshot, page_id)` → bool — quick check

## Notes
- Templates loaded lazily and cached at module level
- No templates in test env → returns "unknown"
