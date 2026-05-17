# PyInstaller 打包经验教训 (2026-04-18/19)

## 核心教训

### 1. 绝对不要用 in-process 模式执行游戏操作
**问题**: MaaFw 的 `SendMessageWithCursorPos` 使用 `BlockInput()` 锁定鼠标键盘。在 GUI 进程的后台线程运行 pipeline 会锁死整个桌面，用户无法操作。
**规则**: **永远用子进程** 运行 pipeline。子进程可被 kill，不影响主进程。

### 2. MSVCP140.dll 与 MaaFw DLL 冲突
**问题**: PyInstaller 打包的 `msvcp140.dll`（在 `_internal/`）与 MaaFw 的 `opencv_world4_maa.dll` 冲突，导致 WinError 1114（DllMain 初始化失败）。
**规则**: `build.py` post-build 必须删除 `_internal/msvcp140.dll` 和 `MSVCP140_1.dll`。系统 System32 的副本会被使用。
**禁止**: 不要把 VC runtime DLLs 复制到 `maa/bin/`，也不要把 `_internal` 加到 DLL 搜索路径。

### 3. rthook 只加 maa/bin，不加 _internal
**问题**: `os.add_dll_directory(_internal)` 会让 MaaFw DLLs 找到冲突的 VC runtime。
**规则**: `rthook_maa.py` 和 `launcher.py _run_worker()` 只添加 `maa/bin` 到 DLL 搜索路径。

### 4. frozen 模式资产路径必须用 sys._MEIPASS
**问题**: `Path("assets/...")` 相对路径在 frozen 模式下找不到文件。
**规则**: `resources.py`、`config.py`、`identify_page.py` 必须用 `sys._MEIPASS`（frozen）或项目根目录（dev）解析路径。

### 5. 子进程也需要 os.add_dll_directory
**问题**: PyInstaller bootloader 的 rthook 在子进程中执行，但 `os.add_dll_directory()` 是进程级的，不继承。
**规则**: `launcher.py _run_worker()` 必须在 `import maa` 之前重新注册 DLL 目录。

### 6. OCR 包必须包含在构建中
**问题**: `rapidocr_onnxruntime` 的 config.yaml 和 ONNX 模型文件未被 PyInstaller 自动收集。
**规则**: `build.py` 必须显式收集 `rapidocr_onnxruntime/*.yaml` 和 `models/*.onnx`。
**补充**: `onnxruntime-directml` 的 `onnxruntime/capi/*.dll|*.pyd` 也必须显式收集，尤其是 `DirectML.dll`；MaaFw DLL 过滤只能过滤来源为 `maa/bin` 的 DLL，不能按文件名误删 ORT 的 `DirectML.dll`。

## 启动流程教训

### 7. 判断"游戏是否在运行"用进程检测，不用窗口连接
**问题**: 游戏启动器和游戏本体是不同进程。窗口连接（DeviceAdapter.connect）可能连到启动器窗口。
**规则**: 用 `tasklist /FI "IMAGENAME eq AetherGazer.exe"` 检测游戏进程。不检测启动器。

### 8. startup task 只在游戏首次启动时运行
**问题**: idle 页面不是 hub，如果 startup task 无条件运行，会在 idle 页面疯狂点击 (0.4, 0.05)。
**规则**: 
- 游戏进程不存在 → 启动游戏 → `game_was_launched=True` → 跑 startup（rapid click 消弹窗）
- 游戏进程已存在 → `game_was_launched=False` → 跳过 startup → ReturnToHub（正常导航）

### 9. DailyRoutine 不能在 startup 之前调 ReturnToHub
**问题**: ReturnToHub 里的 `smart_return.py` 会按 ESC，在开服弹窗阶段按 ESC 触发退出对话框。
**规则**: startup task 是第一个 task，在它之前不能有任何导航操作。

### 10. Hub 检测需要双重确认（仅 startup）
**问题**: 弹窗之间的短暂间隙会露出 hub 背景，单次模板匹配会误判。
**规则**: startup task 检测到 hub 后，等 0.5s 再验证一次。仅在 startup 使用，其他任务不需要。

### 11. startup 点击位置是 (0.4, 0.05)，不是左上角
**问题**: 点左上角容易点到用户中心/返回按钮。
**规则**: 点 (0.4, 0.05) — 顶部中间偏左的空白区域。rapid click ×5，间隔 0.15s。

## 前端 UX 教训

### 12. 用户不需要手动连接/断开/启动游戏
**规则**: 一键"▶ 开始"自动完成一切。ConnectionBar 只显示状态。

### 13. 错误消息不能被"就绪"覆盖
**问题**: `onRunComplete` 清除 statusMsg，导致错误信息一闪而过。
**规则**: 有错误时 `onRunComplete` 不清除 `statusMsg`。用 `_hasError` flag 控制。

### 14. 设置自动保存，不需要保存按钮
**规则**: 输入框 blur 或 Enter 触发保存。显示 ✔ 确认提示 2 秒。

## 代码质量教训

### 15. 每次改动必须跑测试
**规则**: `python -m pytest tests/ -x -q` 在每次提交前。

### 16. 不要保留死代码
**已清理**: `find_contours`、`find_color_regions`、`recognize_text`、`current_version`、`StaminaConfig`、`TaskResult`、10 个无用模板 PNG、16 个无用资源图片。

### 17. 重复逻辑合并
**已合并**: `HasTextCheck` 和 `FindTextCheck` 合并为 `FindTextCheck`（保留别名兼容）。

## 退出生命周期教训

### 18. pywebview closing 事件里禁止任何同步清理或 evaluate_js
**问题**: `window.events.closing` 在 WinForms/WebView2 UI 线程同步执行。关闭时如果后台线程还通过 `window.evaluate_js()` 推日志/状态，或 closing handler 触发日志转发，会和 WebView2 teardown 互锁，表现为点 X 后窗口无响应，直到系统强制 kill。

**规则**:
- closing handler 必须只做非阻塞工作：解绑 `TaskManager`/`LogForwarder` 的 window，调用 `TaskManager.begin_exit()`，然后启动 daemon 线程做慢清理。
- 任何 shutdown 日志之前必须先解绑前端，避免 loguru sink 调 `window.evaluate_js()`。
- app 级 shutdown guard 必须在 closing handler 返回前标记完成，防止 `webview.start()` 返回后主线程同步跑 `shutdown()`。
- `TaskManager.begin_exit()` 只能做快速操作：`_window=None`、停止标志、`KillOnCloseJob.close()`、`proc.kill()`，不能 `wait()`/`join()`/连接 MaaFw。

**验证**: 2026-05-16 重建 dist 后，用 WM_CLOSE 自动化测试 `anime-game-afk.exe`，进程 10s 内退出，日志连续出现 `Shutdown triggered by: window.closing` → `TaskManager shutdown initiated` → `TaskManager shutdown complete`。

### 19. 用户点击“停止”不能触发完成后动作
**问题**: `TaskManager.stop()` kill worker 后，reader thread 的 `finally` 仍然会执行 `_handle_manual_post_action()`。如果配置里曾保存过 `post_run_action: exit_app_and_game`，用户点击“停止”会被当成“任务结束”，导致游戏和工具一起退出。

**规则**:
- `stop()` 必须设置 `_stop_requested=True` 并立即返回，不能 `proc.wait()` 卡住前端。
- reader `finally` 必须在 `_stop_requested` 或 `_exiting` 时跳过 scheduled/manual post-action。
- 手动 post-action 只应在 worker 正常成功退出（`returncode == 0`）后执行；crash/kill/stop 都不执行。
- 前端停止按钮应立即把 `state.running=false`，避免用户以为第一次点击没生效。
- “完成后”下拉必须等真实配置加载成功再启用，不能因为 pywebview API 暂时未 ready 而显示误导性的默认值。

### 20. `onnxruntime`/`onnxruntime-directml` 不能混装进构建环境
**问题**: `rapidocr_onnxruntime` 依赖普通 `onnxruntime`，`uv run` 会把 CPU wheel 重新装回环境；它和 `onnxruntime-directml` 共享同一个 Python 包名，混装会导致构建时收集到 CPU-only 或不完整的 ORT，打包后表现为 OCR 不可用或 DirectML provider 缺失。

**规则**:
- `build.py` 在 PyInstaller 前必须卸载普通 `onnxruntime`，再 `--force-reinstall --no-deps onnxruntime-directml`。
- 构建前必须验证 `onnxruntime.get_available_providers()` 至少包含 `CPUExecutionProvider`，有 GPU 时应包含 `DmlExecutionProvider`。
- OCR 初始化失败必须记录真实异常，不能只报“RapidOCR not installed”，否则会误导为依赖没装或权限问题。
