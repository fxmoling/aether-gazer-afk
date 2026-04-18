# Worker/Pipeline Integration — Design Spec

**Date**: 2026-04-18
**Scope**: Fix 3 functional issues in the UI/worker layer
**Principle**: Clean, no intermediate states, small files/classes, appropriate extensibility

## Problem

The `worker.py` subprocess bypasses the orchestrator layer:
1. Hardcodes `daily_routine` — `if pipeline_id != "daily_routine": error`
2. Iterates `_DAILY_TASKS` directly — skips Pipeline/Executor/Recovery
3. Creates its own DeviceAdapter while main process also holds one (double connection)

## Solution Overview

Three changes, each small and independent:

### 1. PipelineListener — Event callback protocol

**File**: `games/aether_gazer/orchestrator/listener.py` (new, ~40 lines)

```python
@runtime_checkable
class PipelineListener(Protocol):
    def on_task_status(self, task_id: str, status: str, message: str = "") -> None: ...
    def on_process_status(self, name: str, status: str, message: str = "") -> None: ...
    def on_connected(self, resolution: str) -> None: ...
    def on_done(self, completed: int, failed: int, elapsed_s: float) -> None: ...

class NullListener:
    """Default no-op listener."""
    def on_task_status(self, task_id, status, message=""): pass
    def on_process_status(self, name, status, message=""): pass
    def on_connected(self, resolution): pass
    def on_done(self, completed, failed, elapsed_s): pass
```

**ProcessContext gets a listener field**:
```python
@dataclass
class ProcessContext(TaskContext):
    config: dict[str, Any] = field(default_factory=dict)
    listener: PipelineListener | None = None
```

### 2. Process emits task events

**DailyRoutine.execute()** fires `ctx.listener.on_task_status(task_id, status)` before/after each task.

**DailyRoutine.task_defs()** class method returns task metadata for UI discovery:
```python
@classmethod
def task_defs(cls) -> list[dict[str, Any]]:
    return [{"id": id, "name": name, "description": desc, "safe": safe}, ...]
```

**DailyRoutine.execute()** reads `ctx.config.get("enabled_tasks")` to filter which tasks run. If not specified, all tasks run (backward compatible).

### 3. Worker uses Pipeline.run()

**Rewrite worker.py** to:
- Build ProcessRegistry via shared `build_registry()` from a new `games/aether_gazer/registry.py`
- Create DeviceAdapter + connect (only the worker connects, not main process)
- Build Pipeline with context_factory that injects JsonLineListener
- Construct PlanConfig from CLI args (pipeline_id + enabled_tasks in config)
- Call `await pipeline.run(plan)` — gets Recovery/Executor for free
- JsonLineListener translates events to JSON lines on stdout

### 4. Main process: verify-then-release connection

**TaskManager.connect()**: Creates DeviceAdapter, verifies connection, gets resolution, immediately `disconnect()`. Stores `_game_verified: bool` and `_resolution: str`.

**TaskManager.start()**: Checks `_game_verified` instead of `self._device.connected`. Launches worker subprocess (worker owns the real connection).

**TaskManager._device removed**: No persistent DeviceAdapter in main process.

### 5. Shared ProcessRegistry builder

**New file**: `games/aether_gazer/registry.py` (~20 lines)
```python
def build_registry() -> ProcessRegistry:
    registry = ProcessRegistry()
    registry.register("daily_routine", DailyRoutine)
    registry.register("push_main_story", PushMainStory)
    return registry
```

Used by: worker.py, launcher.py CLI mode, TaskManager._load_pipelines().

### 6. TaskManager._load_pipelines() uses Process metadata

Replaces hardcoded `_DAILY_TASKS` import + `_TASK_NAMES` dict with:
```python
registry = build_registry()
for name in registry.available():
    process_cls = registry.get_class(name)
    if hasattr(process_cls, "task_defs"):
        tasks = [TaskState(**td) for td in process_cls.task_defs()]
    pipelines.append(PipelineDef(id=name, ..., tasks=tasks))
```

## File Change Summary

| File | Change |
|------|--------|
| `orchestrator/listener.py` | NEW — PipelineListener protocol + NullListener |
| `orchestrator/pipeline.py` | ProcessRegistry.get_factory(name) method — returns the registered callable without instantiating, so callers can access class methods like task_defs() |
| `processes/base.py` | ProcessContext.listener field |
| `processes/daily_routine.py` | Fire task events, read enabled_tasks from config, add task_defs() |
| `processes/push_main_story.py` | Add task_defs() if applicable |
| `games/aether_gazer/registry.py` | NEW — shared build_registry() |
| `ui/worker.py` | REWRITE — use Pipeline.run() + JsonLineListener |
| `ui/task_manager.py` | Remove _device, verify-then-release, use registry for pipeline discovery |
| `launcher.py` | Use shared build_registry() instead of inline construction |

## Backward Compatibility

- CLI mode (`launcher.py --cli`) uses the same Pipeline.run() path — unchanged behavior
- Process.execute() without listener works (NullListener / None check)
- DailyRoutine without enabled_tasks in config runs all tasks (existing behavior)
- Frontend JS unchanged — same JSON line protocol, same pywebview API

## Testing Strategy

- Unit test PipelineListener protocol conformance
- Unit test DailyRoutine.task_defs() returns correct metadata
- Unit test JsonLineListener output format
- Integration: verify worker.py → Pipeline → DailyRoutine → events → JSON lines
- Existing 535 tests must stay green (no regressions)
