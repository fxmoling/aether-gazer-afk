# Lightweight Scheduler — Design Spec

> **Date**: 2026-04-25
> **Status**: Draft → Pending approval
> **Reference**: ok-script `ok/util/windows_schedule.py` + `ok/gui/tasks/ScheduleTaskTab.py`

## 1. Problem Statement

用户需要定时执行每日任务（如凌晨 4 点自动做日常），即使 app 没有运行也能触发。
任务完成后可选择：退出 app、关闭游戏进程、或什么都不做。
失败时可选重试 1 次。

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│  Windows Task Scheduler                              │
│  ┌─────────────────────────────────────────────┐     │
│  │ AetherGazerAFK\DailyTask                    │     │
│  │ Trigger: Daily 04:00 (Mon-Fri)              │     │
│  │ Action: anime-game-afk.exe --scheduled      │     │
│  └──────────────────┬──────────────────────────┘     │
└─────────────────────┼───────────────────────────────┘
                      │ (Windows launches exe)
                      ▼
┌─────────────────────────────────────────────────────┐
│  launcher.py                                         │
│  ├─ --scheduled flag detected                        │
│  ├─ HeadlessRunner.run()                             │
│  │   ├─ Launch game (if not running)                 │
│  │   ├─ Connect to game window                       │
│  │   ├─ Execute daily pipeline                       │
│  │   ├─ On failure: retry once (if configured)       │
│  │   └─ Post-action: exit_app / kill_game / nothing  │
│  └─ Exit process                                     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Frontend (Vue)                                      │
│  ┌─────────────────────────────────────────────┐     │
│  │ ScheduleView.vue                            │     │
│  │ ├─ 启用/禁用定时任务 toggle                  │     │
│  │ ├─ 时间选择器 (HH:MM)                       │     │
│  │ ├─ 星期几多选 (Mon-Sun)                      │     │
│  │ ├─ 完成后动作 dropdown                       │     │
│  │ ├─ 失败重试 toggle                           │     │
│  │ └─ 状态显示 (下次运行/上次结果)              │     │
│  └─────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────┘
```

## 3. Components

### 3.1 `src/anime_game_afk/runtime/scheduler.py` — Windows Task Scheduler 封装

**职责**：创建/删除/查询/启用/禁用 Windows 计划任务。

```python
class WinScheduler:
    TASK_FOLDER = "\\AetherGazerAFK"
    TASK_NAME = "DailyTask"

    def create_task(self, config: ScheduleConfig) -> bool
    def delete_task(self) -> bool
    def enable_task(self, enabled: bool) -> bool
    def query_task(self) -> ScheduleTaskInfo | None
    def is_task_registered(self) -> bool
```

**实现策略**（参考 ok-script）：
- 优先使用 `schtasks.exe`（无需 `win32com` 依赖，兼容性最佳）
- `schtasks /Create /XML <file>` 通过 XML 模板创建任务，支持完整配置
- 不使用 COM API（避免 `pywin32` 额外依赖 + PyInstaller 打包问题）
- 任务注册在 `\AetherGazerAFK\DailyTask` 路径下

**XML 模板**：生成标准 Windows Task Scheduler XML，包含：
- `<CalendarTrigger>` 或 `<TimeTrigger>` 定义触发时间
- `<Exec>` 指向 `anime-game-afk.exe --scheduled`
- `<Settings>` 设置运行策略（无需登录、电池模式允许等）

### 3.2 `src/anime_game_afk/runtime/headless.py` — 无头执行入口

**职责**：定时触发时，以无 GUI 模式执行日常任务。

```python
class HeadlessRunner:
    def __init__(self, config: ScheduleConfig):
        self.config = config
        self.logger = get_logger("headless")

    def run(self) -> int:
        """Execute scheduled pipeline. Returns 0 on success, 1 on failure."""
        # 1. Load schedule config
        # 2. Launch game if not running (via GameLauncher)
        # 3. Wait for game window
        # 4. Connect DeviceAdapter
        # 5. Execute daily pipeline (reuse worker.py logic)
        # 6. On failure + retry_enabled: retry once
        # 7. Post-action: kill game / exit app / nothing
        # 8. Write result to schedule_log.json
        return exit_code
```

**日志**：写入 `config/schedule_log.json`，记录每次执行的时间戳、结果、耗时。
前端可读取并显示历史记录。

### 3.3 `config/scheduler.yaml` — 配置持久化

```yaml
scheduler:
  enabled: false
  time: "04:00"           # HH:MM (24h)
  days:                   # 空 = 每天；指定则按星期
    - mon
    - tue
    - wed
    - thu
    - fri
  pipeline_id: "daily_tasks"
  retry_on_failure: false  # 失败后重试 1 次
  post_action: "nothing"   # nothing | exit_app | kill_game
```

### 3.4 `launcher.py` — CLI 参数扩展

在现有 launcher 中添加 `--scheduled` 分支：

```python
if "--scheduled" in sys.argv:
    from anime_game_afk.runtime.headless import HeadlessRunner
    from anime_game_afk.runtime.schedule_config import load_schedule_config
    config = load_schedule_config()
    runner = HeadlessRunner(config)
    sys.exit(runner.run())
```

### 3.5 Frontend — `ScheduleView.vue`

**UI 元素**：
1. **启用开关** — toggle，开启时自动注册 Windows 计划任务，关闭时删除
2. **执行时间** — 双数字输入 HH:MM
3. **星期选择** — 7 个 chip/checkbox（周一到周日），不选 = 每天
4. **Pipeline 选择** — dropdown（目前只有 daily_tasks）
5. **失败重试** — toggle
6. **完成后动作** — dropdown（什么都不做 / 退出程序 / 关闭游戏）
7. **状态面板** — 下次运行时间、上次运行结果、运行历史

**API 端点**：

```python
# api.py 新增
def get_schedule(self) -> dict            # 获取当前定时配置
def save_schedule(self, config) -> dict   # 保存配置并注册/更新 Windows 任务
def delete_schedule(self) -> dict         # 删除 Windows 任务
def get_schedule_history(self) -> list    # 获取历史执行记录
```

### 3.6 Sidebar 更新

在 `Sidebar.vue` 的 `items` 数组中添加：
```js
{ page: 'schedule', icon: '⏰', label: '定时' }
```

## 4. Post-Action 详细逻辑

| Action | 实现 |
|--------|------|
| `nothing` | 执行完毕，进程自然退出（无头模式） |
| `exit_app` | 同 `nothing`（无头模式本身就会退出） |
| `kill_game` | 执行完毕后 `taskkill /F /IM AetherGazer.exe`，然后退出 |

> 注意：在无头模式下，`nothing` 和 `exit_app` 效果相同（进程自然退出）。
> 区分这两个选项是为未来 app 常驻模式预留。

## 5. Failure & Retry Logic

```
Execute pipeline
  ├─ Success → post_action → exit(0)
  └─ Failure
       ├─ retry_on_failure=false → log error → exit(1)
       └─ retry_on_failure=true
            ├─ Wait 30s
            ├─ Re-execute pipeline
            │   ├─ Success → post_action → exit(0)
            │   └─ Failure → log error → exit(1)
```

## 6. Logging Strategy

- **loguru** 写入 `logs/scheduled_YYYY-MM-DD.log`（文件自动轮转）
- **schedule_log.json** 追加结构化记录：

```json
[
  {
    "timestamp": "2026-04-26T04:00:12",
    "pipeline": "daily_tasks",
    "result": "success",
    "duration_s": 342.5,
    "retried": false,
    "post_action": "kill_game"
  }
]
```

- 前端 ScheduleView 读取并展示最近 10 条记录

## 7. Error Handling

| 场景 | 处理 |
|------|------|
| 游戏未安装/路径错误 | 记录错误日志，exit(1) |
| 游戏无法启动 | 重试 1 次（如果启用），否则 exit(1) |
| 游戏窗口连接失败 | 同上 |
| Pipeline 执行中异常 | 捕获异常，记录堆栈，按重试策略处理 |
| `schtasks` 命令失败 | 前端显示具体错误信息 |
| 权限不足（极少见） | 提示用户以管理员身份运行 |

## 8. PyInstaller 注意事项

- `--scheduled` 模式不启动 pywebview/GUI，避免不必要的 DLL 加载
- `headless.py` 需要加入 `build.py` 的 `hiddenimports`
- 无头模式的 exe 路径通过 `sys.executable` 获取（frozen 模式下正确指向 exe）

## 9. File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `src/.../runtime/scheduler.py` | **New** | Windows Task Scheduler 封装 |
| `src/.../runtime/headless.py` | **New** | 无头执行入口 |
| `src/.../runtime/schedule_config.py` | **New** | 配置加载/保存 |
| `src/.../ui/api.py` | **Edit** | 新增 schedule API 端点 |
| `launcher.py` | **Edit** | 添加 `--scheduled` 分支 |
| `build.py` | **Edit** | 添加 hiddenimports |
| `config/scheduler.yaml` | **New** | 默认配置模板 |
| `frontend/src/views/ScheduleView.vue` | **New** | 定时任务 UI |
| `frontend/src/components/Sidebar.vue` | **Edit** | 添加定时 tab |
| `frontend/src/App.vue` | **Edit** | 添加 ScheduleView 路由 |
| `frontend/src/composables/useApi.js` | **Edit** | 新增 API 调用 |

## 10. Scope Exclusions

- ❌ 定时开关机（以后再做）
- ❌ COM API（避免 pywin32 依赖，纯 schtasks.exe）
- ❌ 多任务调度（只支持一个定时计划）
- ❌ cron 表达式（用 HH:MM + 星期几，足够）
