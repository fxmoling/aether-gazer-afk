# AetherGazer (深空之眼) Game Module

Game-specific automation for AetherGazer, built on the layered architecture.

## Directory Structure

```
aether_gazer/
├── knowledge/          # Layer 4: Pure data (pages, nav graph, keys, constants)
├── ops/                # Layer 5: Atomic operations (perception, navigate, interact)
├── checks/             # Layer 5A: Checks — observe game state without side effects
├── tasks/              # Layer 6: Composable multi-step tasks
├── processes/          # Layer 7: Complete user-visible features
├── orchestrator/       # Layer 8: Pipeline execution and recovery
├── config.py           # Game configuration (window title, MaaFw settings)
└── __init__.py
```

## Layer Dependencies

```
Layer 8: orchestrator/ → imports from processes/, tasks/, ops/, knowledge/, runtime/, core/
Layer 7: processes/    → imports from tasks/, ops/, knowledge/, runtime/, core/
Layer 6: tasks/        → imports from ops/, knowledge/, runtime/, core/
Layer 5: ops/          → imports from knowledge/, vision/, runtime/, core/
Layer 4: knowledge/    → imports nothing (pure data)
```

## Key Resources

- Page templates: `assets/aether_gazer/templates/` (20 PNG, 15 pages)
- Design resolution: 1600x900

