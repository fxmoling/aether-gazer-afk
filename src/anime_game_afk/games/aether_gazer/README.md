# AetherGazer (深空之眼) Game Module

Game-specific automation for AetherGazer, built on the layered architecture.

## Directory Structure

```
aether_gazer/
├── knowledge/          # Layer 4: Pure data (pages, nav graph, keys, constants)
├── ops/                # Layer 5: Atomic operations (perception, navigate, interact, combat)
├── tasks_v2/           # Layer 6: Composable multi-step tasks
├── processes/          # Layer 7: Complete user-visible features
├── orchestrator/       # Layer 8: Pipeline execution and recovery
├── config.py           # Game configuration (window title, MaaFw settings)
├── adapter.py          # Game-specific adapter utilities
└── __init__.py
```

## Deprecated Directories (to be removed)

The following directories contain deprecation wrappers that redirect to new locations:

- `pages/` → migrated to `knowledge/pages.py` + `ops/perception/`
- `nav/` → migrated to `knowledge/navigation.py` + `ops/navigate/`
- `tasks/` (old) → migrated to `tasks_v2/` (Layer 6) + `processes/` (Layer 7)

## Layer Dependencies

```
Layer 8: orchestrator/ → imports from processes/, tasks_v2/, ops/, knowledge/, runtime/, core/
Layer 7: processes/    → imports from tasks_v2/, ops/, knowledge/, runtime/, core/
Layer 6: tasks_v2/     → imports from ops/, knowledge/, runtime/, core/
Layer 5: ops/          → imports from knowledge/, vision/, runtime/, core/
Layer 4: knowledge/    → imports nothing (pure data)
```

## Key Resources

- Page templates: `assets/aether_gazer/templates/` (20 PNG, 15 pages)
- Text templates: `assets/aether_gazer/templates/text/` (9 PNG for state detection)
- Design resolution: 1600x900

