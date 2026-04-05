# 项目概述

## 目标

游戏自动化平台，先深度支持深空之眼，再扩展为多游戏平台。

## 合规要求

- **只能**通过截图 + 图像识别作为输入
- **只能**通过模拟鼠标键盘作为输出
- **禁止**抓包、协议分析、内存修改

## 三大核心能力

1. **完全后台运行**（核心，Phase 1）— 不抢焦点，不影响用户操作
2. **定时任务**（Phase 2）— Windows Task Scheduler + 虚拟显示器
3. **跨游戏编排**（Phase 3）— 多游戏任务串联

## 技术路线

- MaaFramework（C++ 核心，LGPL-3.0）+ Python 3.11+ 应用层
- 三层任务架构：JSON 管线 → 条件 JSON → Python 脚本
- 专用引擎：战斗引擎（3D 动作实时控制）、导航引擎（地图移动）

## 初始游戏

深空之眼（AetherGazer）— 3D 动作游戏，优先实现日常任务和关卡推进

## 项目路径

- 工作目录: `c:/Users/Administrator/Desktop/anime-game-afk/`
- 参考项目: `.references/` 目录下（M9A, MAA, ok-ww, BetterGI）
