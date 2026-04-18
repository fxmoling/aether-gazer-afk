# processes/

User-visible processes (Layer 7) for AetherGazer automation.

## Purpose

Processes are the top-level features that users enable (e.g. "Push main story",
"Complete daily tasks"). They compose Layer 6 tasks into complete user-visible
workflows. Processes are NOT composable by each other — they are terminal.

## Layer Dependencies

- **Depends on**: Layer 6 (tasks), Layer 5 (ops), Layer 4 (knowledge)
- **Must not depend on**: other processes — no lateral process imports

## Files

| File | Responsibility |
|------|---------------|
| `base.py` | `ProcessResult`, `ProcessContext` (with listener), `Process` protocol |
| `push_main_story.py` | `PushMainStory` — clear story stages until done or out of stamina |
| `daily_routine.py` | `DailyRoutine` — 11 daily tasks with event callbacks and enabled_tasks filtering |

## Key Patterns

- **Event callbacks**: `ctx.notify_task(task_id, status)` fires `PipelineListener.on_task_status()`
- **Task filtering**: `ctx.config["enabled_tasks"]` controls which tasks run (UI passes this)
- **Task discovery**: `DailyRoutine.task_defs()` returns metadata for UI rendering

## Usage

```python
from anime_game_afk.games.aether_gazer.processes.base import ProcessContext

ctx = ProcessContext(
    device=device,
    config={"enabled_tasks": ["mail", "stamina_packs"]},
    listener=my_listener,  # optional
)
result = await DailyRoutine().execute(ctx)
```
