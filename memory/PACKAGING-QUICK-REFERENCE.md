# 打包方案快速参考

## 核心问题解答

### 1. ok-ww 如何分发可执行文件？
**答**: 使用 **PyAppify** 工具，将 Python 代码编译为单一 `.exe` 可执行文件
- 产物: `ok-ww-win32.exe` (包含所有依赖，可直接运行)
- 也生成: 安装程序 `ok-ww-win32-China-setup.exe` 和 `ok-ww-win32-Global-setup.exe`

### 2. 使用什么打包工具？
**ok-ww**: PyAppify (自研工具，比 PyInstaller 更适合 GUI 应用)
**MAA**: CMake (C++ 编译) + 手动打包
**M9A**: 无打包 (直接分发源代码)

### 3. 如何处理依赖？
| 项目 | 依赖策略 |
|------|--------|
| ok-ww | 依赖内联到 EXE (用户零配置) |
| MAA | 部分静态链接 + VCRedist (需用户装一次) |
| M9A | pip install requirements.txt |

### 4. 最终分发形式？
| 项目 | 分发物 |
|------|--------|
| ok-ww | 单一 .exe + 可选安装程序 |
| MAA | ZIP (Windows) / DMG (macOS) |
| M9A | Git 源代码 |

---

## ok-ww PyAppify 配置要点

```yaml
# pyappify.yml 核心配置
name: "ok-ww"                    # 应用名称
uac: true                         # 需要管理员权限
profiles:
  - name: "China"
    git_url: "..."                # 自动更新源
    admin: true
    main_script: "main.py"        # 入口脚本
    requires_python: "3.12"
    requirements: "requirements.txt"  # 依赖声明
    use_pythonw: true             # 无控制台窗口
    show_add_defender: true       # 提示用户白名单
```

### GitHub Actions 构建步骤
```
标签推送 (v*)
  ↓ [setup Python 3.12]
  ↓ [pip install requirements]
  ↓ [运行测试]
  ↓ [inline_ok_requirements]
  ↓ [pyappify build-exe-only]
  ↓ [可选: SignPath 代码签名]
  ↓ [pyappify build-setup-exe]
  ↓ [发布到 GitHub Releases]
```

---

## 依赖对比

### ok-ww requirements.txt (核心)
- `ok-script==1.0.87` - 作者自研框架
- `pyappify==1.0.2` - 打包工具
- `pyside6==6.9.1` - GUI
- `opencv-python` - 图像处理
- `onnxocr-ppocrv5` - OCR
- `openvino` - 模型推理

**打包时**: 全部内嵌到 .exe

### MAA 依赖 (编译时)
- OpenCV (C++)
- PaddleOCR + FastDeploy (C++)
- ONNX Runtime (C++)
- .NET Runtime (自包含)
- Visual C++ Redistributable x64 (用户安装)

**打包时**: 大部分静态链接，.NET 自包含

---

## 分发渠道对比

| 渠道 | ok-ww | MAA |
|------|-------|-----|
| GitHub Releases | ✅ 主渠道 | ✅ 主渠道 |
| WinGet | ❌ | ✅ `winget install maa` |
| MirrorChyan | ✅ 付费加速 | ✅ 付费加速 |
| 国内云盘 | 夸克网盘 | QQ 群文件 |

---

## 选择建议

### PyAppify (ok-ww 模式) 适合
- ✅ 纯 Python 项目
- ✅ Windows 优先
- ✅ 非技术用户
- ✅ 快速迭代
- ✅ 单 EXE 分发

### CMake (MAA 模式) 适合
- ✅ C++ 核心项目
- ✅ 性能关键
- ✅ 跨平台需求
- ✅ 多语言绑定
- ✅ 大型项目

---

## 当前项目推荐

**最佳选择**: PyAppify 方案
- 项目为 Python
- 目标用户非技术
- Windows 优先
- 需要快速迭代

**配置示例**:
```yaml
name: "anime-game-afk"
profiles:
  - name: "Release"
    main_script: "main.py"
    requires_python: "3.11"
    requirements: "requirements.txt"
    use_pythonw: true
```

---

## 关键文件位置

| 项目 | 配置文件 | 构建脚本 |
|------|---------|---------|
| ok-ww | `pyappify.yml` | `.github/workflows/build.yml` |
| MAA | `CMakeLists.txt` | `.github/workflows/ci.yml` |

---

## 更新时间
2026/04/07 (由 Claude 生成)
