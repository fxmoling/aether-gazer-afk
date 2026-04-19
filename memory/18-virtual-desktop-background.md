# 虚拟桌面后台模式 — 已搁置 (2026-04-19)

## 状态: ❌ 已搁置

CreateDesktopW 虚拟桌面方案对 Unity 游戏的鼠标点击**从根本上不可行**。
键盘和截图正常工作，但鼠标点击无法实现。

## 根因分析（2026-04-19 深度调查）

### 核心问题
虚拟桌面进程调用 `GetCursorPos()` **始终返回 (0, 0)**（result=0，失败）。
Unity 依赖 GetCursorPos 获取鼠标位置 + GetAsyncKeyState/RawInput 检测按键状态。

### 已验证的方法（全部失败）

| 方法 | 类型 | 结果 | 原因 |
|------|------|------|------|
| SendMessage WM_LBUTTONDOWN | 窗口消息 | ❌ | Unity 不从 WM 消息读取鼠标按键 |
| PostMessage WM_LBUTTONDOWN | 队列消息 | ❌ | 同上 |
| MaaFw SendMessage | API | ❌ | 底层同上 |
| MaaFw PostMessage | API | ❌ | 底层同上 |
| MaaFw SendMessageWithCursorPos | API | ❌ | SetCursorPos 在 VD 上失败 |
| MaaFw PostMessageWithCursorPos | API | ❌ | 同上 |
| MaaFw SendMessageWithWindowPos | API | ❌ | 窗口移动正确但按键不被识别 |
| MaaFw PostMessageWithWindowPos | API | ❌ | 同上 |
| MaaFw Seize | 硬件 | ❌ | 非输入桌面无效 |
| SwitchDesktop + SetCursorPos + SendMessage | 桌面切换 | ❌ + 屏幕闪烁 | 点击仍不生效 |
| SwitchDesktop + SendInput | 硬件注入 | ❌ + 屏幕闪烁 | 同上 |
| 移动窗口到 (0,0) + SendMessage | 位置欺骗 | ❌ | hover 检测生效(diff=10.37)但点击不被处理 |
| 移动窗口到 (0,0) + PostMessage | 位置欺骗 | ❌ | 同上 |

### 关键发现

1. **GetCursorPos 在 VD 进程中返回 (0,0)**：通过在 VD 上运行独立 Python 探测脚本确认
2. **WM_MOUSEMOVE 不触发 hover**：发送 WM_MOUSEMOVE 到按钮位置，截图对比无 hover 效果
3. **窗口移动可影响光标位置**：移动窗口使 (0,0) 对应按钮位置后，hover diff 从 2.97 升到 10.37
4. **BetterGI 不用 CreateDesktopW**：BetterGI 在用户桌面运行，用 SetCursorPos + PostMessage（短暂移动光标）

### 什么能工作
- 键盘 (SendMessage WM_KEYDOWN/WM_KEYUP): ✅ 完美工作
- 截图 (PrintWindow): ✅ 完美工作
- 游戏启动 + 窗口发现 (EnumDesktopWindows): ✅

## 架构（仍保留在代码中，暂未启用）

```
Layer 1 (core/):
  virtual_desktop.py  — Win32 桌面生命周期
  device.py           — background 参数路由
  notifier.py         — 通知系统
  types.py            — DeviceConfig.background

Layer 3 (config/):
  user_config.py      — background_mode 设置

Layer 8 (ui/):
  SettingsView.vue    — 运行模式开关
```

## 未来方向

如果要重新探索后台模式，可考虑：
1. **Win10/11 虚拟桌面 API**：共享输入系统，GetCursorPos 正常工作
2. **DLL 注入 hook GetCursorPos**：在游戏进程内伪造光标位置
3. **接受短暂光标移动**：跟 BetterGI 一样，ShowCursor(FALSE) + SetCursorPos + 恢复
