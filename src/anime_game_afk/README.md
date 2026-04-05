# anime_game_afk — Source Root

Layered game automation framework built on MaaFramework.

## Architecture

```
src/anime_game_afk/
├── core/              # Layer 1: Device adapter (MaaFw wrapper)
├── vision/            # Layer 2: Game-agnostic computer vision
├── runtime/           # Layer 3: Logging, config, state, events, errors
├── config/            # Application configuration models
└── games/
    └── aether_gazer/  # Game-specific layers (4-8)
        ├── knowledge/     # Layer 4: Pure data models
        ├── ops/           # Layer 5: Atomic operations
        ├── tasks_v2/      # Layer 6: Composable tasks
        ├── processes/     # Layer 7: Complete features
        └── orchestrator/  # Layer 8: Pipeline execution
```

## Dependency Rule

Layer N may only import from Layers 0..(N-1).
Game-specific code (Layers 4-8) never imports from another game.
Shared infrastructure (Layers 1-3) is game-agnostic.

## Entry Point

Users run automation via `scripts/run.py`, which loads a YAML plan
and executes the Layer 8 pipeline.

## Status

Wave 4 complete. All 8 layers implemented for AetherGazer.

