# Orchestrator (Layer 8)

Top-level pipeline that executes a user-configured selection of game processes.

## Files

| File | Purpose |
|---|---|
| `types.py` | Data types: ProcessDef, PlanConfig, PipelineResult, load_plan() |
| `executor.py` | Run individual processes with logging, timing, error handling |
| `recovery.py` | Cross-process infrastructure recovery strategies |
| `pipeline.py` | Main Pipeline class: load plan → build process list → execute |
| `plans/default.yaml` | Default plan template for new users |

## Architecture

- **Pipeline** loads a YAML plan, filters enabled processes, delegates to Executor
- **Executor** runs each process with timing, logs results, catches errors
- **Recovery** handles ONLY infrastructure failures: device_disconnected, window_lost,
  screenshot_timeout, game_crash, session_expired
- Game-level failures (battle failed, stamina empty) are handled within processes (Layer 7)

## Dependency Rule

Layer 8 imports from Layers 0-7. No other layer imports from Layer 8.

## Usage

```python
from anime_game_afk.games.aether_gazer.orchestrator import (
    Pipeline, ProcessRegistry, load_plan
)

registry = ProcessRegistry()
registry.register("daily_routine", DailyRoutine)
registry.register("push_main_story", PushMainStory)

pipeline = Pipeline(
    registry=registry,
    device=device_adapter,
    context_factory=lambda proc_def: ProcessContext(
        device=device_adapter,
        config=proc_def.config,
        logger=get_logger(f"process.{proc_def.name}"),
    ),
)
result = await pipeline.run("plans/default.yaml")
print(f"Succeeded: {result.succeeded}/{result.total}")
```

## Plan YAML Format

```yaml
game: aether_gazer

processes:
  - name: daily_routine
    enabled: true

  - name: push_main_story
    enabled: true
    config:
      max_stages: 20
```
