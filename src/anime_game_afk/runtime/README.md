# runtime/ — Runtime Services (Layer 3)

Cross-cutting infrastructure services. Passive — provides tools, does not drive game logic.

## Files

| File | Purpose |
|------|---------|
| `logger.py` | Structured logging (wraps loguru) with context tags |
| `config.py` | Configuration loading from YAML/dict with dot-path access |
| `state.py` | Persistent JSON state store *(planned)* |
| `clock.py` | Time utilities, cooldowns, timers *(planned)* |
| `events.py` | Infrastructure-level event bus *(planned)* |
| `errors.py` | Recovery strategy framework *(planned)* |

## Scope

- `events.py` handles **only** infrastructure events (`device_disconnected`, `window_lost`, etc.)
- **Not** game events (`battle_started`, `character_died`) — those live in the game layer
- Each module wraps a proven library (`loguru`, `pyyaml`, `json`, `time`)

## Usage

### Structured logger

```python
from anime_game_afk.runtime import get_logger

log = get_logger("aether_gazer")
log.info("Session started")

# Add context for structured filtering
task_log = log.with_context(task="daily_missions", step="login")
task_log.info("Clicking login button")
# → [aether_gazer] [task=daily_missions, step=login] Clicking login button

# Chain additional context
step_log = task_log.with_context(step="stamina_purchase")
step_log.debug("Checking stamina: current={}", 80)
```

### Configuration store

```python
from anime_game_afk.runtime import ConfigStore

# Load from YAML
cfg = ConfigStore.from_yaml("config/settings.yaml")

# Typed access with defaults
width  = cfg.get("game.resolution.width", 1600)
height = cfg.get("game.resolution.height", 900)

# Check existence (safe even when value is None)
if cfg.has("game.server"):
    server = cfg.get("game.server")

# Mutate at runtime
cfg.set("game.resolution.width", 1920)

# Create from dict (testing / dynamic config)
cfg = ConfigStore.from_dict({"fps": 60, "vsync": True})
```

## Design Notes

- `Logger` is immutable with respect to context: `with_context()` returns a **new** instance,
  leaving the parent unchanged. This makes it safe to pass loggers into nested call frames.
- `ConfigStore.get()` uses a sentinel internally so that `None` values stored explicitly are
  distinguishable from missing keys via `has()`.
- Both classes are synchronous and thread-safe for reads; concurrent writes to `ConfigStore`
  should be serialised by the caller if needed.
