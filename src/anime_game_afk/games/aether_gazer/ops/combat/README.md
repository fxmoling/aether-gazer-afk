# combat/ — Combat Ops (Layer 5)

"Fight" ops — battle-specific key sequences and action handlers.

## Files
| File | Purpose |
|------|---------|
| attack_cycle.py | Full rotation: J J U J I J O R 1 2 |
| handle_revive.py | Accept revival prompt (Enter) |
| walk_forward.py | Hold W for configurable duration |

## Notes
- `AttackCycleOp(interval=0.0)` for tests (no real-time delay)
- Default interval is 0.25s (BATTLE_KEY_INTERVAL from constants)
- `WalkForwardOp` adds 0.2s buffer after hold_key returns
