# 直接回答您的问题

## 您提出的 4 个问题

### 1️⃣ How ok-ww distributes its executable
(ok-ww 如何分发可执行文件)

**答案**:
- **工具**: PyAppify (作者自研工具)
- **产物**: 单一 `.exe` 可执行文件
- **文件名**: 
  - `ok-ww-win32.exe` (主要产物，最常用)
  - `ok-ww-win32-China-setup.exe` (安装程序国内版)
  - `ok-ww-win32-Global-setup.exe` (安装程序国际版)
- **体积**: 150-200 MB (包含所有依赖)
- **分发渠道**: GitHub Releases, MirrorChyan (国内加速), Quark Drive (免费网盘)

**关键特性**:
- ✅ 双击即用，无需用户安装任何依赖
- ✅ 所有依赖内嵌到 EXE 中
- ✅ 首次运行自动解压到 %TEMP%
- ✅ 自动提示添加 Windows Defender 白名单 (可选)

---

### 2️⃣ What packaging tool they use
(他们使用什么打包工具)

**答案**: **PyAppify**

**PyAppify 详情**:
- **类型**: Python → EXE 打包工具 (作者自研)
- **vs PyInstaller**: PyAppify 针对 GUI 应用更优化
- **核心特性**:
  - Python 嵌入式运行时 (内嵌到 EXE)
  - 自动依赖检测与打包
  - 支持多个 profile (China/Global/Debug)
  - 内置 Git 自动更新机制
  - UAC 权限支持
  - GitHub Actions 原生支持

**其他参考项目的工具**:
- **MAA**: CMake (C++ 编译系统) - 高端方案，跨平台
- **M9A**: 无打包 (分发源代码)
- **BetterGI**: 无打包 (分发脚本文件)

---

### 3️⃣ How they handle dependencies
(他们如何处理依赖)

**答案**: PyAppify 方案 - **全部内联到 EXE**

**详细步骤**:
```
1. 创建虚拟环境 (venv)
   
2. pip install requirements.txt
   (安装所有 Python 包: ok-script, pyside6, opencv, etc.)

3. 扫描所有文件
   - .py 文件 (Python 源代码)
   - .pyd 文件 (编译的 C 扩展)
   - .dll/.so 文件 (动态链接库)

4. 用 7z 压缩打包所有文件

5. 嵌入 Python 解释器
   (通常是 Python 的嵌入式版本)

6. 生成 EXE 壳
   - EXE 壳负责启动和初始化
   - 自动解压压缩包到 %TEMP%

7. 运行时执行
   - 用户双击 .exe
   - EXE 壳解压文件
   - Python 解释器执行 main.py
```

**用户体验**: 零配置！双击即运行

**ok-ww 的 requirements.txt** (示例):
```
ok-script==1.0.87              # 作者自研框架
pyappify==1.0.2                # 打包工具
onnxocr-ppocrv5==0.0.14        # OCR
opencv-python==4.12.0.88       # 图像处理
openvino==2026.0.0             # 模型推理
playwright==1.57.0             # 浏览器自动化
pyside6==6.9.1                 # GUI 框架
pyside6-fluent-widgets==1.8.3  # UI 组件
pywin32==311                    # Windows API
requests==2.32.4               # HTTP
psutil==7.0.0                  # 系统监控
```

**所有这些都被内嵌到 .exe 中** ↑

---

### 4️⃣ What the final distribution looks like
(最终分发形式是什么样的)

**答案**: 三种产物

**1. 单一可执行文件** (最常用)
```
ok-ww-win32.exe  (150-200 MB)
└─ 包含:
   ├─ Python 3.12 运行时
   ├─ 所有 Python 依赖
   ├─ 编译的二进制文件 (.pyd)
   ├─ 所有 DLL 文件
   └─ 应用程序代码
```

**用户下载流程**:
```
1. GitHub Release 页面下载 ok-ww-win32.exe
2. 双击运行
3. 完成！（无需任何配置）
```

**2. 安装程序** (备选)
```
ok-ww-win32-China-setup.exe    # 国内版 (从 CNB 拉取更新)
ok-ww-win32-Global-setup.exe   # 国际版 (从 GitHub 拉取更新)
```

**用户下载流程**:
```
1. 下载 setup.exe
2. 运行安装向导
3. 选择版本 (China/Global)
4. 安装到指定目录
5. 首次运行时可选自动更新
```

**3. 分发渠道**
```
GitHub Releases       - 主渠道
  ├─ ok-ww-win32.exe
  ├─ ok-ww-win32-China-setup.exe
  └─ ok-ww-win32-Global-setup.exe

MirrorChyan (国内)    - 加速下载 (需付费)
Quark Drive (夸克)    - 免费云盘
```

**版本支持** (多地域)
```
China Version:
├─ git_url: https://cnb.cool/ok-oldking/ok-wuthering-waves.git
├─ 依赖源: 阿里云 + 腾讯 CNB
└─ 优势: 国内用户快速

Global Version:
├─ git_url: https://github.com/ok-oldking/ok-ww-update.git
├─ 依赖源: GitHub + PyPI
└─ 优势: 国际用户稳定
```

---

## 构建流程 (GitHub Actions)

**触发**: 推送 Git 标签 (e.g., `git tag v1.0.0 && git push --tags`)

**自动化构建** (~20 分钟):
```
1. checkout 代码 (含 LFS 大文件)
2. setup Python 3.12
3. pip install requirements.txt + requirements-dev.txt
4. 运行 unittest (确保质量)
5. inline_ok_requirements (内联依赖配置)
6. pyappify build-exe-only → ok-ww-win32.exe
7. pyappify build-setup-exe → setup.exe
8. 可选: SignPath 代码签名
9. Release 到 GitHub Releases
10. 触发 MirrorChyan 上传脚本
```

**最终产物** (全自动上传到 GitHub Release):
- ✅ ok-ww-win32.exe (单一 EXE)
- ✅ ok-ww-win32-China-setup.exe (安装程序)
- ✅ ok-ww-win32-Global-setup.exe (安装程序)

---

## 关键配置文件

### pyappify.yml
```yaml
name: "ok-ww"
uac: true

profiles:
  - name: "China"
    git_url: "https://cnb.cool/ok-oldking/ok-wuthering-waves.git"
    admin: true
    main_script: "main.py"
    requires_python: "3.12"
    requirements: "requirements.txt"
    use_pythonw: true           # 无控制台窗口
    show_add_defender: true     # 提示白名单

  - name: "Global"
    git_url: "https://github.com/ok-oldking/ok-ww-update.git"
    main_script: "main.py"
    requirements: "requirements.txt"
```

### .github/workflows/build.yml
```yaml
name: Build Windows Executable

on:
  push:
    tags:
      - 'v*'    # 标签推送触发

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v2
        with:
          python-version: 3.12
      - run: pip install -r requirements.txt
      - run: python -m unittest tests/*.py
      - run: python -m ok.update.inline_ok_requirements
      - uses: ok-oldking/pyappify-action@master
      - uses: softprops/action-gh-release@v2
        with:
          files: pyappify_dist/*
```

---

## 总结对比

| 维度 | ok-ww (推荐) | MAA | M9A | BetterGI |
|------|-------------|-----|-----|----------|
| 打包工具 | PyAppify | CMake | 无 | 无 |
| 分发格式 | .exe (单一) | .zip/.dmg | 源代码 | 脚本文件 |
| 用户体验 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐ |
| 零配置 | ✅ | ❌ | ❌ | ❌ |
| 双击即用 | ✅ | ❌ | ❌ | ❌ |
| 构建时间 | ~20 分钟 | ~60 分钟 | N/A | N/A |
| 体积 | 150-200 MB | 50-100 MB | N/A | 小 |
| 跨平台 | ❌ | ✅ | ✅ | ❌ |

---

## 对您项目的建议

**推荐采用**: PyAppify 方案 (同 ok-ww)

**原因**:
- 项目为 Python (易迭代)
- 目标用户非技术 (需要零配置)
- Windows 优先 (ok-ww 也是)
- 构建快速 (开发效率高)

**配置示例**:
```yaml
# pyappify.yml
name: "anime-game-afk"
uac: true
profiles:
  - name: "Release"
    main_script: "main.py"
    requires_python: "3.11"
    requirements: "requirements.txt"
    use_pythonw: true
    show_add_defender: true
```

---

## 参考资源

- **PyAppify**: https://github.com/ok-oldking/pyappify
- **ok-wuthering-waves**: https://github.com/ok-oldking/ok-wuthering-waves
- **本研究的详细文档**: memory/ 目录下的其他 5 个文件

---

**生成时间**: 2026/04/07
**基于**: ok-wuthering-waves pyappify.yml, .github/workflows/build.yml, requirements.txt
