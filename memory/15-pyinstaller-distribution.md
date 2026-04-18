# PyInstaller 构建与分发 (2026-04-18)

## 构建命令

```bash
python build.py --clean --zip   # 完整构建 + ZIP
python build.py --zip           # 增量构建 + ZIP
python build.py --spec-only     # 只生成 .spec 文件
```

## 构建产物

- `dist/anime-game-afk/` — 242MB 文件夹
- `dist/anime-game-afk.zip` — 119MB 压缩包

## 关键问题与解决方案

### 1. MaaFw DLL 冲突 (WinError 1114)
**问题**: PyInstaller 打包的 `msvcp140.dll` 与 MaaFw 的 `opencv_world4_maa.dll` 冲突，导致 DllMain 初始化失败。
**解决**: `build.py` post-build 删除 `_internal/MSVCP140_1.dll` 和 `_internal/msvcp140.dll`，系统 System32 的副本会被使用。

### 2. 子进程 vs In-process
**问题**: 子进程方式 (`exe --worker`) DLL 加载可能有问题。In-process 方式 (`threading`) 会导致 MaaFw 的 `BlockInput()` 锁死整个桌面。
**解决**: 使用子进程方式。DLL 问题通过删除冲突的 msvcp140 解决。
**危险**: **绝对不要用 in-process 模式** — BlockInput 会锁死用户输入。

### 3. 资产路径 (frozen mode)
**问题**: `Path("assets/...")` 相对路径在 frozen 模式下找不到文件。
**解决**: `resources.py` 和 `config.py` 使用 `sys._MEIPASS` 解析绝对路径。`identify_page.py` 用 `ASSETS_ROOT` 解析模板路径。

### 4. OCR 数据文件
**问题**: `rapidocr_onnxruntime` 的 config.yaml 和 ONNX 模型未打包。
**解决**: `build.py` 自动收集 `rapidocr_onnxruntime/*.yaml` 和 `models/*.onnx` 到 datas。

### 5. rthook 配置
- `rthook_maa.py`: 设置 `MAAFW_BINARY_PATH`，**只** 添加 `maa/bin` 到 PATH 和 DLL 目录
- **不添加 `_internal`** 到 DLL 搜索路径 — 其 VC runtime 会冲突

## GPU 加速 (DirectML)

- `onnxruntime-directml` 替代 `onnxruntime`
- OCR 性能: CPU 1.5s → GPU (DirectML) 0.07s (20x 提速)
- `ocr.py` 自动检测 `DmlExecutionProvider`，fallback 到 CPU

## Worker 子进程流程

```
GUI 进程 (pywebview)
  → 用户点击"开始"
  → task_manager.start()
  → subprocess: exe --worker --pipeline daily_routine --tasks ...
    → launcher.py _run_worker()
      → os.add_dll_directory(maa/bin)  # 补充 rthook
      → worker.main()
        → 检测游戏 → 未运行则启动 → 连接
        → 设置 game_was_launched 标志
        → pipeline.run()
          → DailyRoutine.execute()
            → game_was_launched? startup task : ReturnToHub
            → 后续任务...
```

## 前端一键启动 UX

- 移除手动"连接/断开/启动游戏"按钮
- ConnectionBar 只显示状态 (就绪/准备中/已连接)
- 点击"▶ 开始"自动完成一切
- 错误消息持久显示，不被"就绪"覆盖
