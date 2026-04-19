# 17 — Virtual Desktop Background Mode

**Date**: 2025-07-18

## Summary

Added optional background mode that runs the game on a hidden Win32 desktop
(`CreateDesktopW`), eliminating cursor interference entirely. Also added
Windows toast notifications for task completion/failure.

## New Files

| File | Purpose |
|------|---------|
| `core/virtual_desktop.py` | Win32 desktop lifecycle: create → launch → find_window → destroy |
| `core/notifier.py` | Zero-dep toast notifications via `Shell_NotifyIconW` ctypes |

## Modified Files

| File | Change |
|------|--------|
| `core/types.py` | Added `game_exe_path: str = ""` to `DeviceConfig` |
| `core/device.py` | Added `background` param; `_connect_background()` uses `VirtualDesktop` + `PrintWindow`/`SendMessage` |
| `config/user_config.py` | Added `background_mode` and `notify_on_complete` settings + accessors |
| `ui/api.py` | Added `set_background_mode()`, `set_notify_on_complete()` API methods |
| `ui/worker.py` | Routes to background/foreground connect; sends notifications on complete |
| `frontend/src/views/SettingsView.vue` | New "运行模式" section with two toggles |
| `frontend/src/composables/useApi.js` | Added `setBackgroundMode`, `setNotifyOnComplete` API calls |

## Key Technical Decisions

- **`EnumDesktopWindows`** (not `FindWindow`) for cross-desktop window search
- **`PrintWindow`** screencap — only method that works across desktops
- **`SendMessage`** input — no `SetCursorPos` needed on virtual desktop
- **`atexit` handler** as safety net for orphaned desktops
- **Notification thread** is daemon — never blocks shutdown
- **Foreground path unchanged** — `background=False` (default) is identical to before
