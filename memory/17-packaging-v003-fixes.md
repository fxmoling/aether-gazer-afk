# v0.0.3 打包问题修复 (2026-04-24)

## 问题总结

v0.0.3-beta 用户反馈两类问题：
1. **打不开** — exe 完全无响应，无窗口、无报错
2. **Worker 崩溃** — 找到游戏窗口后立即 exit code 1

## 根因分析

### 打不开：MSVCP140.dll + 静默失败链

```
build.py 删除 _internal/msvcp140.dll (为了解决 MaaFw DLL 冲突)
  ↓ 用户没装 VC++ Redistributable
Python 自身无法加载 (msvcp140.dll 缺失)
  ↓ exe 启动即崩
console=False → 无控制台输出
  ↓ 想弹 tkinter 对话框
tkinter 被 exclude → 弹窗代码也不可用
  ↓ 想用 pywebview 显示
bottle 包被删除 → pywebview 也可能初始化失败
  → 用户看到"什么都没发生"
```

### Worker 崩溃：截图方法不兼容

```
config.py: screencap_method = FramePool (DXGI)
  ↓ 用户 GPU/驱动不支持 DXGI FramePool
Win32Controller 初始化崩溃
  ↓ 没有 fallback 机制
Worker 进程 exit(1)
```

## 修复措施

| 问题 | 修复 | 文件 |
|------|------|------|
| msvcp140.dll 删除 | 保留删除（必须），但添加 start.bat 检测 + 详细注释 | build.py |
| bottle 被删 | 从清理列表移除 bottle | build.py |
| tkinter 被排除 | 从 excludes 移除 tkinter | build.py |
| 错误弹窗 | launcher.py 用 ctypes MessageBoxW 兜底 | launcher.py |
| 截图方法 | FramePool → DXGI_DesktopDup → GDI 降级链 | device.py |
| 缺少 hidden imports | 添加 duowei_process, duowei_tasks, keys, registry | build.py |

## 决策记录

### 为什么必须删除 msvcp140.dll

PyInstaller 打包的 msvcp140.dll（在 `_internal/`）与 MaaFw 的 `opencv_world4_maa.dll` 版本不兼容。Windows DLL 加载顺序会优先找到 `_internal/` 的版本，导致 WinError 1114 (DllMain 初始化失败)。

MaaFw 的 `maa/bin/` 中**不包含** msvcp140.dll，它依赖系统的 VC++ 运行库。所以：
- 删除 PyInstaller 的副本 → 系统 System32 的副本被使用 → 两者兼容
- 保留 PyInstaller 的副本 → MaaFw 永远崩溃

因此 VC++ 2015-2022 Redistributable 是**硬性依赖**。

### 为什么不能排除 tkinter

虽然 tkinter 增加包体积 (~5MB)，但当 pywebview/.NET 初始化失败时，需要 tkinter 弹出错误对话框。没有 tkinter 就只能用 ctypes MessageBoxW（作为兜底方案已添加）。

## 打包安全清单

每次修改 build.py 前必须检查：
- [ ] `excludes` 列表中的包确认不被任何代码路径使用
- [ ] post-build 清理列表中的包确认不被 pywebview/pythonnet/maa 依赖
- [ ] 新增的 Python 模块已添加到 `hiddenimports`（特别是延迟 import 的模块）
- [ ] 在无 VC++ 的干净 Windows 上测试过（或至少确认 start.bat 能检测）
- [ ] 错误路径有可见的用户反馈（不能是完全静默的）
