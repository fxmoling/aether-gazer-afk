# Subprocess Worker for Reliable Stop

**日期**: 2026-04-08
**状态**: Approved
**范围**: `ui/task_manager.py` 重构 + 新增 `ui/worker.py`

## 问题

当前 `TaskManager` 在同进程的 background thread 中用 `asyncio.Task.cancel()` 实现 stop。但 MaaFramework 的 C++ 调用（截图、点击）会阻塞 Python 事件循环数百毫秒到数秒，cancel 信号无法穿透 C++ 阻塞层，导致 stop 按钮经常无效。

## 方案

将任务执行从 background thread 改为 **subprocess**。Stop = `process.kill()`，操作系统级终止，无论 C++ 在做什么都立即生效。

## 架构

```
主进程 (UI + pywebview)
├── TaskManager
│   ├── start() → subprocess.Popen(worker)
│   ├── stop()  → process.kill()
│   └── _reader_thread → 读 stdout JSON lines → push_js 到前端
│
└── worker 子进程 (python -m anime_game_afk.ui.worker)
    ├── 解析 CLI 参数 (--pipeline, --tasks)
    ├── DeviceAdapter.connect()
    ├── 逐个执行 task，stdout 输出 JSON lines
    └── 退出码: 0=成功, 1=失败, 137/非零=被 kill
```

## 通信协议：stdout JSON lines

子进程通过 stdout 输出 JSON lines，每行一个 JSON 对象：

```jsonl
{"type": "connected", "resolution": "1600x900"}
{"type": "task_status", "id": "mail", "status": "running"}
{"type": "task_status", "id": "mail", "status": "success", "message": "mail_collected"}
{"type": "task_status", "id": "intel_shards", "status": "running"}
{"type": "task_status", "id": "intel_shards", "status": "success", "message": "Purchased 4"}
{"type": "log", "level": "info", "msg": "=== DailyRoutine complete ==="}
{"type": "done", "completed": 11, "failed": 0, "elapsed_s": 499.2}
```

错误情况：
```jsonl
{"type": "error", "msg": "Window not found: 'AetherGazer'"}
```

### 消息类型

| type | 字段 | 说明 |
|------|------|------|
| `connected` | `resolution` | 设备连接成功 |
| `task_status` | `id`, `status`, `message?` | task 状态变更 (running/success/failed/skipped) |
| `log` | `level`, `msg` | 日志消息（可选，用于 UI 日志面板） |
| `done` | `completed`, `failed`, `elapsed_s` | 全部完成 |
| `error` | `msg` | 致命错误，worker 即将退出 |

## 新增文件：`ui/worker.py`

### CLI 接口

```bash
python -m anime_game_afk.ui.worker --pipeline daily_routine --tasks mail,intel_shards,stamina_packs
```

参数：
- `--pipeline`: pipeline ID (目前只有 `daily_routine`)
- `--tasks`: 逗号分隔的启用 task ID 列表

### 内部流程

1. 解析 CLI 参数
2. `DeviceAdapter.connect()` → stdout `{"type": "connected", ...}`
3. 构建 `ProcessContext`
4. 按 `_DAILY_TASKS` 定义顺序，只执行 `--tasks` 中包含的 task
5. 每个 task 执行前 stdout `{"type": "task_status", "id": "...", "status": "running"}`
6. 执行完 stdout `{"type": "task_status", "id": "...", "status": "success/failed/skipped"}`
7. task 之间调用 `ReturnToHubAction`
8. 全部完成 stdout `{"type": "done", ...}`
9. `sys.exit(0)` 正常退出

### 日志重定向

worker 子进程的 loguru 日志默认也写到 stderr/stdout。需要配置：
- **loguru 输出 → stderr**（不干扰 stdout JSON 协议）
- 可选：同时输出 `{"type": "log", ...}` JSON 到 stdout 供 UI 显示

### 错误处理

- `WindowNotFoundError` → stdout `error` 消息 → `sys.exit(1)`
- 未捕获异常 → stderr traceback + stdout `error` 消息 → `sys.exit(1)`

## 修改文件：`ui/task_manager.py`

### start() 修改

```python
def start(self, pipeline_id: str) -> dict:
    enabled = [t.id for t in pipeline.tasks if t.enabled]
    
    self._process = subprocess.Popen(
        [sys.executable, "-m", "anime_game_afk.ui.worker",
         "--pipeline", pipeline_id,
         "--tasks", ",".join(enabled)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    
    self._reader = threading.Thread(
        target=self._read_worker_output, daemon=True
    )
    self._reader.start()
    self._running = True
```

### stop() 修改

```python
def stop(self) -> dict:
    proc = self._process
    if proc and proc.poll() is None:
        proc.kill()
        proc.wait(timeout=5)
    self._running = False
    # reader 线程会因 stdout EOF 自动退出
```

### _read_worker_output() 新增

```python
def _read_worker_output(self):
    """Reader 线程：读子进程 stdout，推送到前端。"""
    try:
        for line in self._process.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            
            if msg["type"] == "task_status":
                task_id = msg["id"]
                status = msg["status"]
                with self._lock:
                    for p in self._pipelines:
                        for t in p.tasks:
                            if t.id == task_id:
                                t.status = status
                self._push_task_status(task_id, status)
                if status == "success":
                    self._completed_count += 1
            
            elif msg["type"] == "done":
                pass  # 正常完成
            
            elif msg["type"] == "error":
                self._push_js(
                    f"window.onError && window.onError({json.dumps(msg['msg'])})"
                )
    finally:
        self._running = False
        self._push_js("window.onRunComplete && window.onRunComplete()")
```

### 删除的代码

- `_run_pipeline()` 方法 — 被子进程替代
- `_async_run()` 方法 — 被子进程替代
- `_resolve_task_class()` 方法 — 移到 worker.py
- `_async_loop` / `_async_task` 字段 — 不再需要
- `connect()` 方法可以简化为检测游戏窗口是否存在（不持有 controller）

### 保留的代码

- `_load_pipelines()` — UI 仍需知道有哪些 task
- `_load_config()` / `_save_config()` — 持久化 task 启用状态
- `get_pipelines()` / `set_task_enabled()` — 前端 API
- `get_status()` — 前端轮询
- `_push_task_status()` / `_push_js()` — 前端推送

## 行为矩阵

| 场景 | 行为 |
|------|------|
| 正常执行完成 | worker stdout `done` → reader 标记完成 → `onRunComplete` |
| 用户按 Stop | `process.kill()` → worker 立即死亡 → reader 读到 EOF → 标记完成 |
| 游戏窗口不存在 | worker stdout `error` → reader 推送错误 → worker `exit(1)` → reader EOF |
| worker 崩溃 | stderr 有 traceback → reader 读到 EOF → 标记失败 |
| 重复按 Start | `_running=True` 时拒绝，返回错误 |
| Start 后 Stop 后再 Start | process 已被 kill → reader 已退出 → `_running=False` → 允许新 Start |

## 不变的部分

- 前端 JS (`app.js`) — `start/stop/status` API 接口不变
- `api.py` — 暴露给前端的方法签名不变
- 所有 task/action/check/op — 零修改
- `bridge.py` — 不变

## 测试策略

- 单元测试 `worker.py`：mock DeviceAdapter，验证 stdout JSON 格式正确
- 单元测试 `task_manager.py`：mock subprocess.Popen，验证 start/stop/reader 逻辑
- 手动测试：启动 UI → Start → 观察 task 状态更新 → Stop → 确认立即停止
