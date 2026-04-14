# 已知问题与注意事项

## 1. 截图文件过大 (已解决 ✅)

**现象**: 上传截图到 Claude 时出现 "Request too large (max 20MB)" 错误
**影响**: 会话中断，难以恢复
**解决方案** (2026-04-05):
- `scripts/explore.py`: MAX_DISPLAY_WIDTH=800, JPEG quality=65
- `scripts/explore_all_pages.py`: 批量转换工具，PNG→JPEG 压缩率 96%
- **强制规则**: 所有展示用截图必须 ≤ 800px 宽 + JPEG 格式，每张 < 60KB

## 2. 按钮点击不准确 (已解决 ✅)

**现象**: `post_click(x, y)` 点击偏移，无法命中导航按钮

### 根因 (3 个叠加问题)

1. **输入方法错误** — `SendMessage` → `SendMessageWithCursorPos`
   - Unity 游戏读物理光标位置，不读 lParam
   - 修复: `config.py` 中 mouse/keyboard_method 改为 SendMessageWithCursorPos ✅

2. **Resolution 为 (0,0)** — MaaFw 首次截图前不知道窗口分辨率
   - `preproc_touch_point` 用 resolution 做坐标映射，(0,0) 导致错误
   - 修复: `session.py` connect() 中增加 `post_screencap().wait()` 初始化 resolution ✅

3. **坐标估算不准** — 视觉估算偏差 50-100px
   - 解决: 使用像素扫描法 (`brightness > 550`) 精确定位文字中心 ✅

### MaaFw 坐标映射机制 (已研究确认)

```
实际点击坐标 = input_x × (image_raw_width / image_target_width)
```

- `set_screenshot_use_raw_size(True)` → target=raw → 1:1 映射，无缩放
- 默认 `image_target_short_side_ = 720` → 1600×900 会映射到 1280×720（1.25倍缩放）
- `SendMessageWithCursorPos`: SetCursorPos(screen) + SendMessage(WM_LBUTTONDOWN, MAKELPARAM(client_x, client_y))
- `block_input = true` 防止用户鼠标干扰（会短暂抢鼠标）

## 3. 游戏资源文件位置

**安装路径**: `E:\shenkongzhiyan\AetherGazerLauncher\AetherGazer\`
**版本**: v2.30.15, Unity IL2CPP

| 路径 | 内容 |
|------|------|
| `StreamingAssets\Windows\` | 62,671 个 `.ys` AssetBundle (51GB) |
| `assets/uiresources/` (包内) | 950 个 UI 资源 |
| `atlas/` (包内) | 314 个精灵图集 |

资源包格式: `.ys` = 标准 UnityFS，通过 `AssetHash_Info.bytes` JSON 映射。可用 `UnityPy` 提取。

## 4. 探测页面安全规则 ⚠️

- **禁止在探测（抽卡）页面做任何操作**
- 仅用于页面识别，识别后立即退出
- 如不慎进入，立刻 ESC 退出

## 5. 抢鼠标 + BlockInput 问题 (已知限制)

- `SendMessageWithCursorPos` + `block_input=true` 会短暂占用物理鼠标
- MaaFramework 内部调用 `BlockInput(TRUE)` → `SetCursorPos` → `SendMessage` → 恢复光标 → `BlockInput(FALSE)`
- `BlockInput` 是 Win32 系统级 API，**阻止所有桌面的鼠标/键盘输入**，包括虚拟桌面
- 高频操作时可能触发 **explorer.exe 缓冲区溢出** 错误弹窗：
  "系统在此应用程序中检测到基于堆栈的缓冲区溢出。溢出可能允许恶意用户获得此应用程序的控制。"
  这是 Windows 内部防护机制对频繁 BlockInput 调用的误报，不影响功能
- **所有基于 MaaFramework 的 Unity 游戏自动化工具都有同样限制**（M9A 也用 SendMessageWithCursorPos）
- 后续方案: CreateDesktopW 隔离桌面 / Android 模拟器 + ADB

## 状态

- **创建**: 2026-04-04
- **上次更新**: 2026-04-06 — explorer.exe 缓冲区溢出问题记录，BlockInput 限制详细说明
