# core/

Layer 1 — Device Adapter. Single point of contact with MaaFramework.

## Files

| File | Purpose |
|------|---------|
| `types.py` | Shared types: Point, Rect, Resolution, DeviceConfig |
| `device.py` | DeviceAdapter — screenshot, click, press_key, hold_key, swipe |
| `errors.py` | Exception hierarchy: AutomationError, DeviceError, DeviceConnectionError, etc. |
| `session.py` | **Deprecated** — old GameSession, delegates to DeviceAdapter |

## Key Types

- `DeviceConfig` — window_title, screencap/mouse/keyboard methods, design_resolution
- `DeviceConnectionError` — replaces old `ConnectionError` to avoid shadowing Python builtin

## Layer Rule

This layer may only import from Layer 0 (MaaFramework). No game logic, no config/ imports.
