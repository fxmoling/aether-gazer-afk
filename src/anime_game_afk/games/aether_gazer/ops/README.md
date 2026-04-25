# ops/ — Atomic Operations (Layer 5)

Smallest executable units. Each op does ONE thing, returns OpResult.

## Structure
| Subdir | Purpose |
|--------|---------|
| base.py | Op protocol, OpResult, OpContext |
| perception/ | "See" — identify pages from screenshots |
| navigate/ | "Go" — move between pages |
| interact/ | "Act" — rapid click |

## Rules
- Each file = one op (or small family)
- Ops complete in <10 seconds
- Ops do NOT call other ops
- Ops handle their own retries, NOT cross-op recovery
- Depends on: Layers 1-4 only
