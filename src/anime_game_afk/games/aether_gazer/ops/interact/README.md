# interact/ — Interaction Ops (Layer 5)

"Act" ops — click elements, skip cutscenes, advance dialogue, confirm popups.

## Files
| File | Purpose |
|------|---------|
| click_element.py | Look up element by name_en, click its coordinate |
| skip_cutscene.py | ESC → wait → Enter to skip cutscene |
| advance_dialogue.py | Press Space to advance dialogue |
| confirm_popup.py | Enter to confirm or ESC to dismiss popup |

## Safety
- `ClickElementOp` blocks unsafe elements unless `force_unsafe=True`
- Unsafe elements: Gacha (costs pulls), Inventory (could spend items)
