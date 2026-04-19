# 虚拟桌面后台模式 (2026-04-19)

## 概要

通过 Win32 `CreateDesktopW` API 在独立桌面上运行游戏，彻底消除鼠标光标抢占问题。
用户桌面的鼠标完全不受影响。

## 架构位置

```
Layer 1 (core/):
  virtual_desktop.py  — Win32 桌面生命周期 (CreateDesktop/EnumDesktopWindows/CloseDesktop)
  device.py           — DeviceAdapter 内部根据 config.background 自动切换模式
  notifier.py         — Shell_NotifyIconW 通知 (零依赖)
  types.py            — DeviceConfig 携带 background + game_exe_path

Layer 3 (config/):
  models.py           — GameConfig.to_device_config(background=True, game_exe_path=...)
  user_config.py      — background_mode / notify_on_complete 用户设置

Layer 8 (ui/):
  worker.py           — 读取设置，传入 GameConfig.to_device_config()，其他不变
  task_manager.py     — stop() 调用 VirtualDesktop.cleanup_all()
  api.py              — set_background_mode / set_notify_on_complete
  SettingsView.vue    — 运行模式开关
```

## 关键设计决策

### 为什么在 core/ 层
- 后台模式是设备 I/O 层面的关注点，不是业务逻辑
- 所有游戏代码 (ops/checks/tasks) 调用 `device.click()` / `device.screenshot()` 接口不变
- 未来新增游戏只需调 `game_config.to_device_config(background=True)` 即可

### 跨桌面 I/O 方法选择
| 功能 | 方法 | 原因 |
|------|------|------|
| 截图 | PrintWindow | 唯一可跨 Win32 Desktop 的截图方式 |
| 鼠标 | SendMessageWithCursorPos | Unity 校验 GetCursorPos，需移动虚拟桌面的光标 |
| 键盘 | SendMessage | 键盘不需要光标位置 |

### 清理机制
1. `DeviceAdapter.disconnect()` → `VirtualDesktop.destroy()` (正常结束)
2. `TaskManager.stop()` → `VirtualDesktop.cleanup_all()` (用户点停止)
3. `atexit` handler (进程崩溃兜底)

### 通知
- 纯 ctypes `Shell_NotifyIconW`，零依赖
- 使用 `GetDesktopWindow()` 作为 hWnd（自建窗口方式在某些环境下不工作）
- 不抢焦点、不打断全屏游戏

## 对未来游戏开发的影响

**零影响**。新游戏只需要：
1. 定义 `GameConfig`（已有模式）
2. 用户设置页开关后台模式
3. Worker 中 `config.to_device_config(background=cfg.background_mode(), game_exe_path=exe)`
4. 所有 task/op/check 代码完全不需要考虑后台模式

## 验证记录
- 2026-04-19: 深空之眼 (AetherGazer, Unity) 在虚拟桌面上正常渲染 ✅
- PrintWindow 截图 1280×720 ✅
- SendMessageWithCursorPos 点击生效，从登录进入主界面 ✅
- 用户光标全程无干扰 ✅
- GDI/FramePool 不可用 ❌（已排除）
