# 打包方案技术深度分析

## 1. PyAppify (ok-wuthering-waves 使用)

### 核心机制
**目标**: Python 源代码 → 独立可执行 Windows 应用

**工作流**:
```
Python 项目 (main.py + 依赖)
    ↓
PyAppify 解析 pyappify.yml
    ↓
1. 创建虚拟环境 (venv)
2. pip install requirements.txt
3. 内联所有 .pyd / .py 文件
4. 嵌入 Python 解释器
5. 打包成单一 .exe
    ↓
输出: ok-ww-win32.exe (自包含)
```

### PyAppify 特色
- **Python 嵌入式**: 不需要用户装 Python
- **自动依赖检测**: 从 import 语句推断依赖
- **多配置文件**: pyappify.yml 支持多个 profile (China/Global/Debug)
- **Git 自动更新**: 内置 Git，可后台自动更新代码
- **UAC 支持**: 可配置是否需要管理员权限

### 配置解读 (ok-ww 的 pyappify.yml)

```yaml
name: "ok-ww"
uac: true                          # Windows UAC: 需要管理员权限

profiles:
  - name: "China"
    git_url: "https://cnb.cool/ok-oldking/ok-wuthering-waves.git"
    # ^ 指定自动更新源，用户首次运行时可选从此 Git repo 拉取最新代码
    
    admin: true                     # 要求管理员权限
    main_script: "main.py"          # 入口脚本
    requires_python: "3.12"         # 最低 Python 版本
    requirements: "requirements.txt" # 依赖声明文件
    use_pythonw: true               # 使用 pythonw.exe (无控制台窗口)
    show_add_defender: true         # 首运行时提示用户添加到 Defender 白名单
    
  - name: "Global"
    # 国际版，从 GitHub 拉取更新
    git_url: "https://github.com/ok-oldking/ok-ww-update.git"
    main_script: "main.py"
    requirements: "requirements.txt"
    # (无 admin/pythonw 配置，使用默认值)
```

### GitHub Actions 构建详解

**触发条件**: `push tags v*` (标签推送，如 v1.0.0)

**关键步骤**:

1. **Checkout** (Git 克隆)
   ```yaml
   - uses: actions/checkout@v4
     with:
       submodules: true    # 克隆子模块
       lfs: true          # Git LFS 大文件
       fetch-depth: 0     # 完整历史
   ```

2. **Python Setup**
   ```yaml
   - uses: actions/setup-python@v2
     with:
       python-version: 3.12
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # 构建工具依赖
   ```

4. **Run Tests** (确保代码质量)
   ```bash
   python -m unittest tests/*.py
   ```

5. **Inline Requirements** (特殊步骤！)
   ```bash
   python -m ok.update.inline_ok_requirements --tag v1.0.0
   ```
   - 作用: 将 requirements.txt 转换为内联配置
   - 结果: EXE 内包含所有依赖版本信息
   - 目的: 支持离线运行，无需 pip

6. **Build EXE Only**
   ```yaml
   - uses: ok-oldking/pyappify-action@master
     with:
       build_exe_only: false
   ```
   - 输出: `ok-ww-win32.exe` (~100-200MB)

7. **Code Signing** (可选，防止浏览器警告)
   ```yaml
   - uses: signpath/github-action-submit-signing-request@v1.1
     with:
       organization-id: '...'
       project-slug: 'ok-wuthering-waves'
   ```

8. **Build Setup EXE** (安装程序)
   ```bash
   # 创建 ok-ww-win32-China-setup.exe 和 ok-ww-win32-Global-setup.exe
   # 这些是 NSIS 或类似工具生成的安装程序
   # 首次运行时弹出选择: China/Global 版本
   ```

9. **Release to GitHub**
   ```yaml
   - uses: softprops/action-gh-release@v2
     with:
       files: pyappify_dist/*
   ```
   - 上传到 GitHub Releases
   - 自动生成下载链接

### 输出物
- `ok-ww-win32.exe` — 单一可执行文件 (~150-200 MB)
- `ok-ww-win32-China-setup.exe` — 安装程序
- `ok-ww-win32-Global-setup.exe` — 安装程序
- 可选: 代码签名证书

### 优点
- ✅ 最简单的用户体验 (双击即用)
- ✅ 零依赖配置
- ✅ 自动更新机制
- ✅ 多地域支持 (China/Global)
- ✅ 构建速度快 (相对 CMake)

### 缺点
- ❌ 只支持 Windows
- ❌ EXE 体积大 (150+ MB)
- ❌ 不支持多语言绑定
- ❌ 启动时间长 (首次解压文件)

---

## 2. CMake (MAA 使用)

### 核心机制
**目标**: C++ 源代码 → 原生二进制文件

**工作流**:
```
C++ 源代码 + CMakeLists.txt
    ↓
CMake 生成编译配置 (Visual Studio Project)
    ↓
1. 下载依赖 (OpenCV, ONNX Runtime, PaddleOCR)
2. 调用 MSVC 编译
3. 链接静态库
4. 生成 MAA.exe + DLL
    ↓
创建分发包 (ZIP)
    ↓
输出: MAA-v2.X.Y-win-x64.zip
```

### 依赖管理 (MAA 示例)

**CMakeLists.txt 片段**:
```cmake
# 找到依赖
find_package(OpenCV REQUIRED)
find_package(ONNX REQUIRED)
find_package(PaddleOCR REQUIRED)

# 链接到目标
target_link_libraries(MAA PRIVATE 
  ${OpenCV_LIBRARIES}
  ${ONNX_LIBRARIES}
  ${PaddleOCR_LIBRARIES}
)
```

**自定义依赖下载脚本**: `tools/maadeps-download.py`
- 作用: 在构建前下载所有依赖
- 优势: CI 可缓存依赖，加快构建

### GitHub Actions 构建流程

**并行矩阵** (同时构建 6 个平台):
```yaml
strategy:
  matrix:
    include:
      - { os: windows-latest, arch: x64 }
      - { os: windows-latest, arch: x86 }
      - { os: windows-latest, arch: arm64 }
      - { os: macos-latest, arch: universal }
      - { os: ubuntu-latest, arch: x64 }
      - { os: ubuntu-latest, arch: arm64 }
```

**Windows x64 构建步骤**:
```
Checkout
  ↓
Setup MSVC (Visual Studio 2022)
  ↓
Download Dependencies (maadeps-download.py)
  ↓
CMake Configure:
  cmake -B build -DCMAKE_BUILD_TYPE=Release
  ↓
Build:
  cmake --build build --config Release -j4
  ↓
Code Signing (Authenticode):
  signtool sign /f cert.pfx out/MAA.exe
  ↓
Package:
  zip -r MAA-v2.X.Y-win-x64.zip out/
  ↓
Upload to GitHub Releases
```

### 输出物
- `MAA-v2.X.Y-win-x64.zip` (~150-300 MB)
- 包含:
  - MAA.exe
  - 所有 DLL 依赖
  - DependencySetup_*.bat (VCRedist 安装脚本)
  - config.json (默认配置)

### 优点
- ✅ 跨平台 (Win/Mac/Linux)
- ✅ 高性能 (编译后二进制)
- ✅ 多语言绑定 (Python, Java, Rust, Go, TS, Dart)
- ✅ 模块化架构 (分离 Core 和 GUI)
- ✅ 社区成熟 (C++ 开发者众多)

### 缺点
- ❌ 编译复杂 (需要 CMake 和 MSVC)
- ❌ 构建时间长 (30+ 分钟)
- ❌ 依赖安装复杂 (用户需装 VCRedist)
- ❌ 不适合快速迭代

---

## 3. 依赖打包对比

### ok-ww (PyAppify) - 全内联

```
requirements.txt:
  ok-script==1.0.87
    └─ pyappify==1.0.2
    └─ pyside6==6.9.1
       └─ shiboken6 (.so/.pyd 文件)
    └─ opencv-python
       └─ cv2.*.pyd
    └─ onnxocr-ppocrv5
    └─ openvino==2026.0.0
       └─ openvino_runtime.dll

打包时:
  1. 创建 venv
  2. pip install -r requirements.txt
  3. 扫描所有 .py 文件和 .pyd 文件
  4. 全部打包到 .exe 中
  5. 运行时: .exe 解压到临时目录 → Python 解释
  
结果: 单一 EXE，无需额外安装
```

### MAA (CMake) - 混合链接

```
编译依赖:
  OpenCV 4.x (C++)
    └─ 与 MAA.exe 静态链接
  PaddleOCR (C++)
    └─ 与 MAA.exe 静态链接
  ONNX Runtime (C++)
    └─ .dll 动态链接 (onnxruntime.dll)
  .NET Runtime
    └─ 自包含部署 (内嵌)

发行时:
  运行时依赖:
    - Visual C++ Redistributable x64 (用户安装一次)
    - onnxruntime.dll (包含在 ZIP)
    - .NET Runtime (内嵌)

用户体验:
  1. 解压 ZIP
  2. 运行 DependencySetup_*.bat (安装 VCRedist)
  3. 双击 MAA.exe
```

---

## 4. CI/CD 流程对比

### ok-ww 构建时间
- 代码检出: 2 分钟
- 依赖安装: 5 分钟
- 测试: 2 分钟
- 内联依赖: 3 分钟
- PyAppify 构建: 5-10 分钟
- 代码签名: 2 分钟
- **总计**: ~20-25 分钟

### MAA 构建时间
- 代码检出: 2 分钟
- 依赖下载: 10 分钟
- CMake 配置: 5 分钟
- 编译: 30-60 分钟 (取决于优化级别)
- 代码签名: 2 分钟
- **总计**: ~50-75 分钟

---

## 5. 性能对比

| 指标 | ok-ww (PyAppify) | MAA (CMake) |
|------|-----------------|------------|
| 启动时间 | 3-5 秒 | 0.5-1 秒 |
| 内存占用 | 200-300 MB | 100-150 MB |
| CPU 占用 | 中 (解释执行) | 低 (编译执行) |
| EXE 大小 | 150-250 MB | 50-100 MB |
| 图像识别速度 | Python 慢 | C++ 快 (10x) |

---

## 6. 选择决策树

```
项目类型?
├─ Python (纯脚本/GUI)
│  └─ 用户群体?
│     ├─ 非技术用户
│     │  └─ PyAppify ✅ (单 EXE)
│     └─ 开发者
│        └─ PyInstaller (也可以)
│
├─ C++ (高性能)
│  └─ 跨平台?
│     ├─ 是
│     │  └─ CMake ✅ (Unix Makefiles + MSVC)
│     └─ 否 (Windows Only)
│        └─ Visual Studio 或 CMake (简化)
│
└─ 混合 (C++ 核心 + Python 绑定)
   └─ MAA 模式 ✅ (C++ + Python binding)
```

---

## 7. 实施建议

### 快速启动 (PyAppify)
```
1. 安装 PyAppify: pip install pyappify
2. 创建 pyappify.yml:
   name: "my-app"
   profiles:
     - name: "Release"
       main_script: "main.py"
       requirements: "requirements.txt"
3. 在项目根目录运行: pyappify build-exe-only
4. 输出: dist/my-app.exe
```

### 持续集成 (GitHub Actions)
```yaml
name: Build
on:
  push:
    tags: ['v*']
jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: pip install pyappify
      - run: pyappify build-exe-only
      - uses: softprops/action-gh-release@v2
        with:
          files: dist/*.exe
```

---

## 参考资源

- **PyAppify**: https://github.com/ok-oldking/pyappify
- **ok-wuthering-waves**: https://github.com/ok-oldking/ok-wuthering-waves
- **MAA**: https://github.com/MaaAssistantArknights/MaaAssistantArknights
- **CMake 文档**: https://cmake.org/cmake/help/latest/
- **PyInstaller**: https://pyinstaller.org/

---

## 更新时间
2026/04/07
