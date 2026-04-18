# games/

Per-game implementations. Each subdirectory is a complete game automation module.

## Structure

```
games/
└── aether_gazer/    # 深空之眼 (AetherGazer)
```

## Adding a New Game

Create `games/<game_id>/` with subdirectories for each layer:
- `knowledge/` (Layer 4) — pure data models
- `ops/` (Layer 5) — atomic operations
- `tasks/` (Layer 6) — composable tasks
- `processes/` (Layer 7) — user-visible features
- `orchestrator/` (Layer 8) — pipeline execution

## Isolation Rule

Game A never imports from Game B. Shared infrastructure lives in core/, vision/, runtime/ (Layers 1-3).
