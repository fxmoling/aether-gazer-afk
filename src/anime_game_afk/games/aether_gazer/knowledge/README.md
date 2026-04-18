# knowledge/ — Game Knowledge (Layer 4)

Pure data models for AetherGazer. **ZERO imports** of cv2, device, or vision.

## Files
| File | Contents |
|------|----------|
| constants.py | Design resolution, thresholds, timing defaults |
| keys.py | All VK codes (battle, UI, movement) |
| resources.py | Template directory paths, state template metadata |
| pages.py | PageDef with elements and coordinates (15 pages) |
| navigation.py | NavGraph with page-to-page edges |

## Rules
- Only import from `anime_game_afk.core.types` (Point, Rect, Resolution)
- All coordinates are in 1600x900 design resolution
- Hand-maintained — update when new pages/coordinates are discovered
