# Virtual Desktop Background Mode + Toast Notifications

## Overview

Add an optional "background mode" that runs games on a hidden Win32 desktop (`CreateDesktopW`), eliminating cursor interference entirely. When disabled, everything works as before. Also add lightweight Windows toast notifications for task completion/failure.

## Design Decisions

### Virtual Desktop Lifecycle
- **Create on demand** when a run starts with background mode enabled
- **Destroy after run** — kill game process, close desktop handle
- No reuse (not worth the complexity of orphan management)

### Architecture: Core layer, not game-specific
The virtual desktop is a **DeviceAdapter concern** (core layer), not an AetherGazer concern. Any game that uses DeviceAdapter gets background mode for free.

## Changes

### 1. `core/virtual_desktop.py` (NEW)

Encapsulates Win32 desktop lifecycle:

```python
class VirtualDesktop:
    """Manages a hidden Win32 desktop for background game execution."""
    
    def __init__(self, name: str = "AFK_Background"):
        self.name = name
        self._hdesk = None
        self._game_pid = None
        self._game_hproc = None
    
    @property
    def active(self) -> bool: ...
    
    def create(self) -> None:
        """CreateDesktopW — idempotent."""
    
    def launch(self, exe_path: str) -> int:
        """CreateProcessW with lpDesktop. Returns PID."""
    
    def find_window(self, title: str, timeout: float = 120) -> int:
        """EnumDesktopWindows poll until window appears. Returns HWND."""
    
    def terminate_game(self) -> None:
        """TerminateProcess if still alive."""
    
    def destroy(self) -> None:
        """terminate_game + CloseDesktop. Safe to call multiple times."""
    
    def __enter__(self) / __exit__(self):
        """Context manager: create → use → destroy."""
```

### 2. `core/device.py` (MODIFY)

Add background mode support:

```python
class DeviceAdapter:
    def __init__(self, config, background: bool = False):
        self._background = background
        self._vdesktop: VirtualDesktop | None = None
    
    def connect(self):
        if self._background:
            self._vdesktop = VirtualDesktop()
            self._vdesktop.create()
            # Launch game on virtual desktop
            self._vdesktop.launch(game_exe_path)
            hwnd = self._vdesktop.find_window(title)
            # Use PrintWindow + SendMessage (no cursor move)
            self._controller = Win32Controller(
                hWnd=hwnd,
                screencap_method=PrintWindow,
                mouse_method=SendMessage,
                keyboard_method=SendMessage,
            )
        else:
            # Existing logic unchanged
    
    def disconnect(self):
        # Existing cleanup...
        if self._vdesktop:
            self._vdesktop.destroy()
            self._vdesktop = None
```

Key: when `background=True`:
- screencap → `PrintWindow` (only method that works cross-desktop)
- mouse/keyboard → `SendMessage` (no CursorPos needed — no user on that desktop)
- Click mode → `"maafw"` (let MaaFw's SendMessage handle it natively)

### 3. `core/notifier.py` (NEW)

Lightweight Windows toast notifications:

```python
def notify(title: str, message: str) -> None:
    """Show a Windows toast notification.
    
    Uses win10toast_click or falls back to ctypes MessageBalloon.
    Non-blocking, does NOT steal focus or interrupt fullscreen apps.
    """
```

Implementation options (in preference order):
1. **`ctypes` Shell_NotifyIconW** — zero dependencies, system tray balloon tip
   - Does NOT break fullscreen games (balloon tips are drawn by Explorer, not a foreground window)
   - Lightweight, no pip install needed
2. **`winotify`** — pip package, modern Action Center toasts
   - Also non-intrusive, but adds a dependency
3. **`plyer`** — cross-platform but heavy

**Recommendation: `Shell_NotifyIconW` via ctypes** — zero deps, guaranteed non-intrusive.

### 4. `config/user_config.py` (MODIFY)

Add settings in `_default_data()`:

```yaml
settings:
  background_mode: false   # NEW — run game on virtual desktop
  notify_on_complete: true # NEW — toast when tasks finish
```

Add accessors: `background_mode()`, `set_background_mode()`, `notify_on_complete()`, `set_notify_on_complete()`.

### 5. `ui/api.py` (MODIFY)

- `get_settings()` → include `background_mode` and `notify_on_complete`
- `save_settings()` → accept and persist both
- Notification call integrated in worker's run-complete callback

### 6. `ui/worker.py` (MODIFY)

- Pass `background=cfg.background_mode()` to DeviceAdapter
- On run complete/failure → call `notifier.notify()`

### 7. Frontend: `SettingsView.vue` (MODIFY)

Add two toggles in a new "运行模式" section:
- 🖥️ 后台模式 (虚拟桌面) — toggle for `background_mode`
  - Subtitle: "在独立桌面运行游戏，不影响鼠标操作"
- 🔔 完成通知 — toggle for `notify_on_complete`
  - Subtitle: "任务完成或失败时显示系统通知"

### 8. Frontend: `useApi.js` (MODIFY)

Add `setBackgroundMode(enabled)`, `setNotifyOnComplete(enabled)` API calls.

## Files Summary

| File | Action | Description |
|------|--------|-------------|
| `core/virtual_desktop.py` | NEW | Virtual desktop lifecycle |
| `core/notifier.py` | NEW | Toast notifications via ctypes |
| `core/device.py` | MODIFY | `background` param, PrintWindow+SendMessage |
| `config/user_config.py` | MODIFY | Two new settings |
| `ui/api.py` | MODIFY | Expose new settings |
| `ui/worker.py` | MODIFY | Pass background flag, trigger notifications |
| `frontend/.../SettingsView.vue` | MODIFY | Two new toggles |
| `frontend/.../useApi.js` | MODIFY | New API calls |

## What stays unchanged
- All task/op/check code — they call `device.click()` / `device.screenshot()` as before
- Pipeline/orchestrator — unaware of background mode
- LogsView, TasksView, ControlBar — work exactly the same
- The game config (`aether_gazer/config.py`) — DeviceAdapter overrides methods when background

## Cleanup contract
1. `VirtualDesktop.destroy()` called in `DeviceAdapter.disconnect()`
2. `disconnect()` already called in worker's `finally` block
3. Also called when GUI window closes (`app.py` cleanup)
4. `atexit` handler as safety net for crashes
