# 参考项目的打包与分发方案

## 1. ok-wuthering-waves (鸣潮) — Python + PyAppify

### 打包工具
- **核心工具**: [PyAppify](https://github.com/ok-oldking/pyappify) (作者自研)
- **Python 版本**: 3.12
- **打包方式**: Python → 可执行 EXE (自动化，CI/CD 集成)

### 分发方式
- **单一可执行文件**: `ok-ww-win32.exe` (包含所有运行时)
- **安装程序**: `ok-ww-win32-China-setup.exe` / `ok-ww-win32-Global-setup.exe`
  - China: 从 CNB (阿里云) 拉取更新
  - Global: 从 GitHub + PyPi 拉取更新
- **无需解压**: 直接运行 EXE

### 依赖处理
- **主依赖** (requirements.txt):
  ```
  ok-script==1.0.87              # 作者自研框架
  pyappify==1.0.2                # 打包工具
  onnxocr-ppocrv5==0.0.14        # OCR (ONNX)
  opencv-python==4.12.0.88
  openvino==2026.0.0
  playwright==1.57.0
  pyside6==6.9.1                 # GUI 框架
  pyside6-fluent-widgets==1.8.3
  pywin32==311
  requests==2.32.4
  psutil==7.0.0
  ```
- **打包时策略**: PyAppify 自动将 requirements.txt 内联到 EXE 中
  - 用户无需手动安装依赖
  - 所有 .pyd / .so 文件内嵌到 EXE

### PyAppify 配置 (pyappify.yml)
```yaml
name: "ok-ww"
uac: true                          # 需要管理员权限
profiles:
  - name: "China"
    git_url: "https://cnb.cool/.../ok-wuthering-waves.git"
    admin: true
    main_script: "main.py"
    requires_python: "3.12"
    requirements: "requirements.txt"
    use_pythonw: true              # 无控制台窗口
    show_add_defender: true        # 提示添加到 Windows Defender 白名单

  - name: "Global"
    git_url: "https://github.com/ok-oldking/ok-w-update.git"
    main_script: "main.py"
    requirements: "requirements.txt"

  - name: "Debug"
    git_url: "https://cnb.cool/.../ok-wuthering-waves.git"
    main_script: "main_debug.py"
    requirements: "requirements.txt"
```

### 构建流程 (GitHub Actions)
**文件**: `.github/workflows/build.yml`

1. **触发**: 标签推送 (`push tags v*`)
2. **环境**: Windows Latest, Python 3.12
3. **步骤**:
   ```
   checkout (含 submodules 和 LFS)
     ↓
   setup Python 3.12
     ↓
   pip install requirements.txt + requirements-dev.txt
     ↓
   run tests (tests/*.py)
     ↓
   inline_ok_requirements (脚本化内联依赖)
     ↓
   Sync 到 CNB 和 GitHub 更新仓库
     ↓
   pyappify build-exe-only (构建单 EXE)
     ↓
   可选: SignPath 代码签名
     ↓
   pyappify build-setup-exe (构建安装程序)
     ↓
   Release to GitHub + MirrorChyan
   ```

4. **输出**:
   - `ok-ww-win32.exe` (单一可执行文件)
   - `ok-ww-win32-China-setup.exe` (完整安装包)
   - `ok-ww-win32-Global-setup.exe` (完整安装包)

### 分发渠道
- **GitHub Releases**: 主发布渠道
- **MirrorChyan**: 国内加速下载 (需付费订阅)
- **Quark Drive**: 免费百度盘式存储

### 关键特性
- ✅ **单 EXE 分发**: 无需用户配置 Python 环境
- ✅ **后台更新**: 通过 Git 自动拉取更新
- ✅ **多地域构建**: China/Global 两条线
- ✅ **自动化测试**: 每次构建都跑 tests/
- ✅ **代码签名**: 可选 SignPath 集成，防止浏览器警告
- ✅ **管理员检查**: 首运行时提示添加 Defender 白名单

---

## 2. MaaAssistantArknights (明日方舟) — C++ 核心 + 多语言绑定

### 打包工具
- **核心**: C++20 编译 → 静态链接 / 动态链接混合
- **构建系统**: CMake 3.28+
- **GUI**: .NET + WPF (自包含部署)
- **多语言绑定**: Python, Java, Rust, Go, TypeScript, Dart

### 分发方式
- **GUI**: `MAA-<版本>-win-x64.zip` / `MAA-<版本>-macos-universal.dmg`
  - **Windows**: ZIP 解压后包含所有文件
  - **macOS**: DMG 磁盘镜像，拖到 Applications
- **CLI**: maa-cli (独立 Rust 工具)
- **无需编译**: 所有用户是预编译二进制

### 依赖处理
**Windows**:
- Visual C++ Redistributable x64 (VCRedist) — 需用户单独安装
- 提供脚本: `DependencySetup_依赖库安装.bat` (自动化安装)
- 内置 .NET 运行时 (自包含部署)
- OpenCV, PaddleOCR, ONNX Runtime 全部静态/动态链接到主 EXE

**macOS**:
- 自包含部署，用户无需额外操作

### 构建流程 (GitHub Actions)
**文件**: `.github/workflows/ci.yml` + `release-preparation.yml`

1. **触发**: 
   - Tag 推送 (`v*`)
   - `dev-v2` 分支变更
   - PR 检查

2. **并行构建任务** (matrix):
   - Windows x64, x86, arm64
   - macOS universal
   - Linux x64, arm64

3. **步骤** (以 Windows x64 为例):
   ```
   checkout (fetch-depth: 0)
     ↓
   Setup MSVC (Visual Studio)
     ↓
   Download dependencies (OpenCV, PaddleOCR, ONNX Runtime 等)
     ↓
   CMake configure + build
     ↓
   Code signing (Authenticode)
     ↓
   Create release package (ZIP)
     ↓
   Upload to GitHub Releases
   ```

4. **输出**:
   - `MAA-v2.X.Y-win-x64.zip` (150-300 MB)
   - `MAA-v2.X.Y-win-arm64.zip`
   - `MAA-v2.X.Y-macos-universal.dmg`

### 分发渠道
- **GitHub Releases**: 主渠道
- **WinGet**: `winget install maa` (官方包管理)
- **MirrorChyan**: 国内加速 (付费)
- **QQ 群文件**: 社区备份

### 安装流程
**Windows**:
```
解压 ZIP
  ↓
以管理员身份运行 DependencySetup_依赖库安装.bat (安装 VCRedist)
  ↓
双击 MAA.exe
```

**macOS**:
```
打开 DMG
  ↓
拖 MAA.app 到 /Applications
  ↓
Finder 启动 MAA.app
```

### 关键特性
- ✅ **跨平台**: Windows, macOS, Linux
- ✅ **多语言绑定**: 支持 Python, Java, Rust 等调用
- ✅ **模块化架构**: Core (C++) 独立于 GUI (WPF)
- ✅ **自包含部署**: .NET 运行时内嵌
- ✅ **代码签名**: Windows Authenticode + Apple 签名
- ✅ **OTA 更新**: 独立更新系统 (release-ota.yml)
- ✅ **多渠道分发**: GitHub, WinGet, Mirror酱

---

## 3. M9A (重返未来1999) — Python + MaaFramework

### 打包策略
- **类型**: Python 脚本 (非独立 EXE)
- **运行方式**: 作为 MaaPiCli 的子进程
- **依赖**: `requirements.txt` 中的 maafw==v5.9.2

### 分发方式
- **源代码**: 直接 Git clone 到 MaaPiCli 资源目录
- **自动更新**: MaaPiCli 自动拉取最新版本
- **无需用户操作**: 集成到 MaaPiCli 生态

### 依赖处理
```
requirements.txt:
maafw==v5.9.2      # MaaFramework (已包含 OpenCV, OCR, ONNX)
```

### 关键特性
- ✅ **即插即用**: 无需编译，直接 Python 解释
- ✅ **依赖轻量**: 只依赖 MaaFramework
- ✅ **生态集成**: 作为 MaaPiCli 官方脚本分发
- ✅ **跨平台**: 通过 MaaFramework 支持 Win/Linux/macOS

---

## 4. BetterGI Scripts — JavaScript + 引擎集成

### 打包方式
- **类型**: 脚本集合 (JSON + JS + TXT)
- **引擎**: 独立的 BetterGI (C# 编写)
- **分发**: 社区脚本库 (GitHub)

### 分发渠道
- **GitHub 仓库**: bettergi-scripts-list
- **社区脚本库**: 即插即用
- **无需打包**: 文本文件直接发布

---

## 总结: 各方案对比

| 项目 | 语言 | 打包工具 | 分发形式 | 用户体验 | 平台 |
|------|------|---------|---------|---------|------|
| **ok-ww** | Python | PyAppify | 单 EXE | 双击即用，零配置 | Windows |
| **MAA** | C++ | CMake | ZIP + DMG | 解压+简单配置 | Win/Mac/Linux |
| **M9A** | Python | 无 | 源代码 | 通过 MaaPiCli | Win/Mac/Linux |
| **BetterGI** | JS/JSON | 无 | 脚本文件 | 社区脚本库 | Win |

### 推荐选择矩阵

**场景 1**: 想要最简单的用户体验（非技术用户）
- ✅ **推荐**: ok-ww 的 PyAppify 方案
- 理由: 单 EXE，双击即用，无需配置

**场景 2**: 想要跨平台支持且用户有基础
- ✅ **推荐**: MAA 的 C++ 编译 + CMake 方案
- 理由: 更高性能，支持多平台，社区成熟

**场景 3**: 轻量级 Python 脚本
- ✅ **推荐**: PyAppify (ok-ww 方案)
- 理由: 构建快，分发简单

**场景 4**: 需要跨平台 + 多语言绑定
- ✅ **推荐**: 混合方案
- 理由: C++ 核心 + Python 绑定 (MAA 模式)

---

## 实现建议

### 对于 ok-wuthering-waves 的学习
1. 研究 PyAppify 配置 (`pyappify.yml`)
2. 学习 GitHub Actions 自动化流程
3. 理解依赖内联机制 (`inline_ok_requirements`)
4. 测试 UAC 和 Defender 白名单提示

### 对于项目自身的选择
**最适合**: PyAppify (ok-ww 方案)
- 理由 1: 项目主要是 Python (快速迭代)
- 理由 2: 目标用户群体多为非技术人员
- 理由 3: Windows 优先 (ok-ww 也是 Windows Only)
- 理由 4: 构建简单，迭代快速

**配置示例**:
```yaml
# 类似 ok-ww 的 pyappify.yml
name: "anime-game-afk"
profiles:
  - name: "Release"
    main_script: "main.py"
    requires_python: "3.11"
    requirements: "requirements.txt"
    use_pythonw: true
    show_add_defender: true
```

---

## 更新日期
2026/04/07
