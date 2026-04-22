# navigate/ — Navigation Actions (Layer 5)

"Go" actions — move between pages, return to hub, wake UI.

## Files
| File | Purpose |
|------|---------|
| wake_hub_ui.py | Click center to dismiss idle overlay |
| go_back.py | ESC or click back button (one step back) |
| smart_return.py | Cycle ESC/back/Enter until hub reached (ReturnToHubAction) |

## Rules
- ReturnToHubAction uses AtHubCheck (template + OCR) — no direct vision calls
- Max 10 attempts for smart_return
- Tasks navigate to pages via direct clicks from hub (not route-based)
