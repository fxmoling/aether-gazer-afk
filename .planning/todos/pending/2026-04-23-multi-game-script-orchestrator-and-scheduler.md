---
created: 2026-04-23T15:27:15.256Z
title: "Multi-game script orchestrator and scheduler"
area: general
files:
  - src/anime_game_afk/ui/task_manager.py
  - src/anime_game_afk/config/user_config.py
  - frontend/src/views/TasksView.vue
---

## Problem

用户玩多款游戏（深空之眼、鸣潮、原神、明日方舟、重返未来1999、绝区零、崩坏：星穹铁道、终末地等），每款游戏有独立的自动化脚本工具。目前需要手动逐个启动各工具，无法统一调度。

需要构建一个"总调度器"，能够：
1. 按时间排程依次调起各脚本工具执行特定任务
2. 监控每个工具的执行状态（成功/失败/超时）
3. 集成 Windows 任务计划程序实现定时执行
4. 提供统一的 UI 配置界面

## Solution

### 已调研的各工具 CLI 接口

| 工具 | 启动方式 | 任务选择 | 自动退出 |
|------|---------|---------|---------|
| ok-ww (鸣潮) | `ok-ww.exe -t <idx> -e` | 任务索引 | ✅ `-e` |
| BetterGI (原神) | `BetterGI.exe startOneDragon [配置名]` / `--startGroups 组名` | 配置名/组名 | ⚠️ 需监控进程 |
| MAA (明日方舟) | Python API `asst.append_task()` | 任务名字符串 | ✅ callback |
| M9A (重返未来1999) | `python agent/main.py <socket_id>` (Agent Server) | socket 协议 | ✅ |
| ZZZ-OneDragon (绝区零) | `launcher.py -o -c -s 60 -i 1,2` | 实例索引 | ✅⭐ 最完善 |
| MaaEnd (终末地) | MaaFramework 系 | JSON pipeline | ✅ |
| anime-game-afk (深空之眼) | 我们自己的工具 | 内部 Process/Task | ✅ |

### 核心模块设计

1. **ToolAdapter 抽象层** — 每个第三方工具一个 adapter，统一接口：`launch(task) → process_handle`
2. **TaskScheduler** — Windows Task Scheduler 集成（参考 ok-script 的 `WindowsScheduleManager` 实现，使用 COM API + schtasks 降级）
3. **ProcessMonitor** — 监控子进程退出码/超时 kill/日志收集
4. **SequenceRunner** — 按用户定义的顺序依次执行多个工具任务
5. **UI 配置界面** — 工具路径配置、任务选择、排程编辑、执行历史

### 参考实现

- ok-script `ok/util/windows_schedule.py` — WindowsScheduleManager（COM API + schtasks XML 模板）
- ok-script `ok/gui/tasks/ScheduleTaskTab.py` — 计划任务 GUI
- BetterGI `CommandLineOptions.cs` — CLI 参数解析模式

### 注意事项

- 关机状态下无法执行，需配合 BIOS 定时开机 + Windows 自动登录
- 每个工具需要用户自行安装并配置路径
- 不同工具的任务标识方式不同，adapter 层需逐个适配
- 需要处理同一台电脑同时只能运行一个游戏的约束（串行执行）
