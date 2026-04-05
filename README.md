# anime-game-afk

Automated game task execution for mobile/PC games using MaaFramework.

## Supported Games

- **深空之眼 (AetherGazer)** — daily routines, main story push, resource farming

## Architecture

9-layer design with strict downward dependencies:

| Layer | Location | Purpose |
|-------|----------|---------|
| 0 | (external) | MaaFramework C++ engine |
| 1 | `core/` | Device adapter — screenshot, click, key press |
| 2 | `vision/` | Game-agnostic computer vision tools |
| 3 | `runtime/` | Logging, config, state management |
| 4 | `games/*/knowledge/` | Pure game data models |
| 5 | `games/*/ops/` | Atomic operations |
| 6 | `games/*/tasks/` | Composable multi-step tasks |
| 7 | `games/*/processes/` | User-visible features |
| 8 | `games/*/orchestrator/` | Pipeline + YAML plan execution |

See `docs/superpowers/specs/2026-04-05-architecture-redesign-design.md` for full spec.

## Quick Start

```bash
# Install dependencies
pip install -e .

# Run with default plan
python scripts/run.py

# Run with custom plan
python scripts/run.py --plan my_plan.yaml
```

## Development

- Python 3.11+
- `docs/coding-standards.md` — coding conventions
- `docs/pages/aether_gazer/` — game page documentation with coordinates
- `memory/` — project memory for AI-assisted development

## Status

Wave 1 (Layers 1-3) and Wave 2 (Layers 4-5) complete. 284 tests passing. Wave 3-4 in progress.
