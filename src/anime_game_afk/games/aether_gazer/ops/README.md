# ops/ — Atomic Operations (Layer 5)

Smallest executable units. Each op does ONE thing, returns OpResult.

## Structure
| Subdir | Purpose |
|--------|---------|
| base.py | Op protocol, OpResult, OpContext, GameState |
| perception/ | "See" — read game state from screenshots |
| navigate/ | "Go" — move between pages |
| interact/ | "Act" — click, confirm, skip |
| combat/ | "Fight" — battle-specific actions |

## Rules
- Each file = one op (or small family)
- Ops complete in <10 seconds
- Ops do NOT call other ops
- Ops handle their own retries, NOT cross-op recovery
- Depends on: Layers 1-4 only
