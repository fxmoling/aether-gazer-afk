# AetherGazer AFK — 深空之眼自动日常工具

[![Release](https://img.shields.io/github/v/release/fxmoling/anime-game-afk?style=flat-square)](https://github.com/fxmoling/anime-game-afk/releases/latest)
[![License: GPL-3.0](https://img.shields.io/github/license/fxmoling/anime-game-afk?style=flat-square)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)](https://python.org)

自动完成深空之眼每日任务：邮件、商店、体力、公会、游园街、联防协议等。
通过截图+图像识别操作游戏，后台运行，不抢焦点。

---

## ✨ 功能特性

| 任务 | 说明 |
|------|------|
| 🎮 启动游戏 | 自动检测游戏路径、跳过开屏弹窗 |
| 📬 领取邮件 | 一键领取所有邮件 |
| 🛒 购买情报 | 每日商店情报碎片 |
| 🔋 领取体力包 | 吨吨值福利包（每日补给） |
| 🏪 商店免费体力 | 商店冷却剂/移转之辉 |
| 🔭 弥弥观测站 | 缩短回归 + 领取奖励 |
| 🏰 公会补给 | 矩阵补给 + 公会任务奖励 |
| 🎡 游园街日常 | 自动放置、投喂、领取、委托、游园任务 |
| ⚔️ 联防协议 | 自动扫荡 + 领取奖励 |
| 📋 每日周常任务 | 一键领取任务奖励 |
| 📝 对策协议 | 领取任务奖励 |
| 🎲 多维变量 | 自动重复挑战，累积积分（独立流程） |

---

## 📦 下载与使用

### 1. 下载

从 [Releases](https://github.com/fxmoling/anime-game-afk/releases/latest) 页面下载最新版 `anime-game-afk.zip`。

### 2. 解压并运行

1. 解压到任意目录（建议英文路径，不要放在 C 盘 Program Files 下）
2. 双击 `anime-game-afk.exe`
3. 勾选要执行的任务，点击 **▶ 开始**

### 3. 系统要求

- **Windows 10/11**（需要 Edge / WebView2 Runtime，系统一般自带）
- **深空之眼 PC 版**，窗口化运行，16:9 分辨率
- 操控模式选择「键盘」（非键鼠模式）
- 游戏窗口不要最小化（可以在后台，但不能最小化）

---

## ❓ 常见问题

**Q: 连接失败 / 找不到游戏窗口**
A: 确认游戏已启动且处于主界面。窗口标题应为 "AetherGazer"。

**Q: 任务执行失败**
A: 确保游戏处于主界面（大厅），不在战斗/加载中。查看日志页面了解详情。

**Q: 自动启动游戏找不到路径**
A: 在设置页面手动指定游戏 exe 路径，或确保桌面有游戏快捷方式。

**Q: 如何关闭自动更新检查？**
A: 在设置页面关闭「自动检查更新」开关。

**Q: 多维变量挑战传送门对不准？**
A: 确保游戏分辨率为 16:9（如 1920×1080），操控模式为「键盘」。如修改了战斗快捷键，请在工具设置页同步配置。

---

| 层 | 技术 |
|----|------|
| 核心 | Python 3.11 + [MaaFramework](https://github.com/MaaXYZ/MaaFramework) |
| 视觉 | OpenCV 模板匹配 + RapidOCR |
| 前端 | Vue 3 + Vite |
| 窗口 | pywebview + WebView2 |
| 打包 | PyInstaller |

---

## 👨‍💻 开发

```bash
# 克隆项目
git clone https://github.com/fxmoling/anime-game-afk.git
cd anime-game-afk

# 安装 Python 依赖
pip install -e ".[dev]"

# 安装前端依赖并构建
cd frontend && npm install && npm run build && cd ..

# 运行测试
pytest tests/

# 启动开发模式
python launcher.py

# 构建发布版
pip install pyinstaller
python build.py --zip
```

### 发布流程

推送版本标签即可触发自动构建和发版：

```bash
git tag v0.2.0
git push origin v0.2.0
```

GitHub Actions 会自动：构建 → 测试 → 打包 → 创建 Release。

---

## 📄 许可证

本项目使用 [GPL-3.0](LICENSE) 许可证。

本项目使用了以下开源组件，详见 [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)：
- [MaaFramework](https://github.com/MaaXYZ/MaaFramework) (LGPL-3.0)
- [OpenCV](https://github.com/opencv/opencv) (Apache-2.0)
- [Vue.js](https://github.com/vuejs/core) (MIT)
- 及其他 — 完整列表见第三方许可证文件

---

## ⚠️ 免责声明

本工具仅供学习交流使用。
仅通过截图 + 图像识别读取画面，通过模拟鼠标键盘操作游戏，不涉及抓包、协议分析或内存修改。
使用本工具产生的任何后果由用户自行承担。
