# 打包与分发方案完整指南

> 本指南汇总了从四大参考项目中提取的打包最佳实践

## 📚 文档结构

### 1. **PACKAGING-SUMMARY-TABLE.md** (⭐ 先看这个)
**快速参考表** — 适合快速查询
- 四大项目打包对比表
- 10 个常见问题速答
- 性能基准对比
- 推荐决策表

**何时查看**: 需要快速了解或对比方案时

---

### 2. **PACKAGING-QUICK-REFERENCE.md** (🔧 实操必读)
**快速参考指南** — 适合实际操作
- ok-ww PyAppify 配置要点
- GitHub Actions 构建步骤
- 依赖对比
- 分发渠道对比
- 当前项目推荐方案

**何时查看**: 准备实施打包方案时

---

### 3. **03-packaging-distribution.md** (📖 完整方案)
**完整方案分析** — 适合深入理解
- 4 个参考项目的详细方案
- 打包工具、分发方式、依赖处理
- PyAppify/CMake 工作流详解
- 各方案的优缺点分析

**何时查看**: 需要理解各方案的完整细节时

---

### 4. **PACKAGING-TECHNICAL-DETAILS.md** (🏗️ 深度分析)
**技术深度分析** — 适合开发者
- PyAppify 核心机制 (7 步构建流程)
- CMake 构建流程 (并行多平台)
- 依赖打包对比 (全内联 vs 混合链接)
- CI/CD 流程对比 (构建时间分析)
- 性能对比表格
- 选择决策树
- 实施建议代码示例

**何时查看**: 需要深入技术细节或自定义方案时

---

## 🎯 快速导航

### 我是...想要...

| 角色 | 目标 | 推荐文档 |
|------|------|---------|
| **用户** | 理解怎样下载和安装 | `02-reference-projects.md` → 分发渠道章节 |
| **项目经理** | 选择最佳打包方案 | `PACKAGING-SUMMARY-TABLE.md` → 推荐决策表 |
| **开发者** | 快速上手实施 | `PACKAGING-QUICK-REFERENCE.md` → 配置要点 |
| **架构师** | 深入技术分析 | `PACKAGING-TECHNICAL-DETAILS.md` → 全部 |
| **运维人员** | 故障排查 | `PACKAGING-SUMMARY-TABLE.md` → 故障排查速查 |

---

## ✅ 核心发现总结

### 1. ok-wuthering-waves (推荐使用 ✅)

**打包工具**: PyAppify (作者自研)
**分发格式**: 单一 .exe (150-200 MB)
**用户体验**: 双击即用，零配置
**构建时间**: ~20 分钟
**平台**: Windows Only

**关键优势**:
- 最简单的用户体验
- 自动化程度最高
- 快速迭代
- 多地域支持 (China/Global)

**关键配置**:
```yaml
# pyappify.yml
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

### 2. MaaAssistantArknights (高端方案)

**打包工具**: CMake
**分发格式**: ZIP (Windows) / DMG (macOS)
**用户体验**: 解压 + 简单配置
**构建时间**: ~60 分钟 (全平台)
**平台**: Win/Mac/Linux

**关键优势**:
- 跨平台支持
- 高性能 (C++ 编译)
- 多语言绑定
- 社区成熟

---

### 3. M9A (轻量级方案)

**分发方式**: 源代码 (不打包)
**运行方式**: MaaPiCli 子进程
**优势**: 即插即用，零打包复杂度

---

### 4. BetterGI (脚本方案)

**分发方式**: 脚本文件 (JSON + JS + TXT)
**优势**: 文本文件，社区贡献

---

## 🚀 对于当前项目的建议

### ✅ 推荐方案: PyAppify (ok-ww 模式)

**为什么?**
1. ✅ 项目为 Python (易迭代)
2. ✅ 目标用户非技术 (需要零配置)
3. ✅ Windows 优先 (ok-ww 也是 Windows Only)
4. ✅ 构建快速 (开发效率高)

**实施步骤**:

```bash
# 1. 创建 pyappify.yml
cat > pyappify.yml << 'CONFIG'
name: "anime-game-afk"
uac: true
profiles:
  - name: "Release"
    main_script: "main.py"
    requires_python: "3.11"
    requirements: "requirements.txt"
    use_pythonw: true
    show_add_defender: true
CONFIG

# 2. 本地测试构建
pip install pyappify
pyappify build-exe-only

# 3. 创建 GitHub Actions (参见下面)
```

### GitHub Actions 工作流

```yaml
# .github/workflows/build.yml
name: Build Windows Executable
on:
  push:
    tags: ['v*']

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install pyappify
      - run: pyappify build-exe-only
      - uses: softprops/action-gh-release@v2
        with:
          files: pyappify_dist/*.exe
```

**发布流程**:
```bash
git tag v1.0.0
git push --tags  # 自动触发 GitHub Actions
# → 生成 anime-game-afk.exe
# → 上传到 GitHub Releases
```

---

## 📋 检查清单

### 本地开发环境
- [ ] Python 3.11+ 已安装
- [ ] requirements.txt 已锁定版本
- [ ] pyappify 已安装 (`pip install pyappify`)
- [ ] 本地构建测试成功 (`pyappify build-exe-only`)

### 项目配置
- [ ] pyappify.yml 已创建
- [ ] main_script 指向正确入口
- [ ] requirements.txt 没有本地路径依赖
- [ ] 没有硬编码的绝对路径

### CI/CD 设置
- [ ] .github/workflows/build.yml 已创建
- [ ] GitHub Secrets 已配置 (如需要)
- [ ] 触发条件为 `push tags v*`
- [ ] Release 注释格式已定义

### 发布前检查
- [ ] 本地单元测试全部通过
- [ ] 版本号已更新
- [ ] CHANGELOG 已更新
- [ ] 标签格式为 v X.Y.Z

---

## 📊 性能对比快查

| 指标 | ok-ww | MAA | 结论 |
|------|-------|-----|------|
| 用户体验 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ok-ww 更好 |
| 启动速度 | 3-5 秒 | 0.5-1 秒 | MAA 快 |
| 内存占用 | 200-300 MB | 100-150 MB | MAA 少 |
| 构建速度 | ~20 min | ~60 min | ok-ww 快 |
| 跨平台 | ❌ | ✅ | MAA 赢 |
| 难度 | ⭐ (最简) | ⭐⭐⭐ | ok-ww 简 |

---

## 🔗 参考资源

| 资源 | 链接 | 备注 |
|------|------|------|
| PyAppify | https://github.com/ok-oldking/pyappify | ok-ww 依赖的打包工具 |
| ok-wuthering-waves | https://github.com/ok-oldking/ok-wuthering-waves | 参考实现 |
| MAA | https://github.com/MaaAssistantArknights | 高端方案参考 |
| CMake 文档 | https://cmake.org | C++ 构建系统 |

---

## 📝 文档更新历史

| 日期 | 作者 | 内容 | 版本 |
|------|------|------|------|
| 2026/04/07 | Claude | 初始版本 (4 个文档) | 1.0 |
| - | - | - | - |

---

## ❓ 常见问题速答

### Q: 用什么来代替 PyInstaller?
**A**: PyAppify (专为 GUI 应用优化)

### Q: 体积太大怎么办?
**A**: 这是 Python 嵌入式运行时的代价，无法避免
- 可以考虑 Nuitka (但需要 C 编译器)
- 或者迁移到 C++ (但工作量大)

### Q: 支持 macOS/Linux 吗?
**A**: PyAppify 目前仅支持 Windows
- 需要跨平台可考虑 MAA 的 CMake 方案
- 或继续用 PyInstaller (支持全平台)

### Q: 自动更新怎样实现?
**A**: PyAppify 内置 Git 更新机制
- 配置 `git_url` 在 pyappify.yml
- 用户首次运行时可选从指定 Git repo 拉取

### Q: 代码签名必须吗?
**A**: 不是必须，但推荐
- 防止浏览器提示 "未知发行商" 警告
- SignPath 可集成到 GitHub Actions

---

## 🎓 学习路径

**初学者** (1 小时):
1. 阅读 `PACKAGING-SUMMARY-TABLE.md` 第 1-3 节
2. 浏览 `PACKAGING-QUICK-REFERENCE.md` 全部
3. 尝试本地 `pyappify build-exe-only`

**中级开发者** (3 小时):
1. 阅读 `03-packaging-distribution.md` 全部
2. 学习 ok-ww 的 `.github/workflows/build.yml`
3. 自己创建 `pyappify.yml` + GitHub Actions

**高级开发者** (1 天):
1. 深度阅读 `PACKAGING-TECHNICAL-DETAILS.md`
2. 对比 PyAppify vs CMake vs PyInstaller
3. 评估是否需要 C++ 迁移

---

## 📞 获取帮助

如有疑问，参考:
1. 本指南的对应章节
2. ok-wuthering-waves 官方文档
3. PyAppify GitHub Issues
4. MAA 官方社区

---

**生成时间**: 2026/04/07  
**文档版本**: 1.0  
**维护者**: Claude Code
