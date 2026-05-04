# combat/ — Auto-Battle System (Layer 5B)

YAML-driven combat scripts + execution engine + battle state monitoring + combo recording.

## Files

| File | Purpose |
|------|---------|
| `script.py` | `CombatScript` + `CombatStep` data model. YAML loader from `config/combat_scripts/{name}.yaml`. Pure data. |
| `runner.py` | `execute_cycle()` runs one pass of all script steps. `CombatRunner` loops while `active=True`. |
| `service.py` | `AutoBattleService` — toggle-based auto-battle with two patterns: user-driven toggle or run-once task-driven. |
| `recorder.py` | `ComboRecorder` — capture keyboard inputs via pynput, compile to press/hold/wait steps. Global hotkeys F9/F11. |

## Step Types

- **press** — Tap key once, then wait `interval` seconds
- **hold** — Hold key for `duration` seconds, then wait `interval` seconds
- **wait** — Sleep for `duration` seconds

## Combo Recording

The `ComboRecorder` captures keyboard input during gameplay and compiles
it into CombatScript-compatible steps:

```python
from anime_game_afk.games.aether_gazer.combat.recorder import ComboRecorder

rec = ComboRecorder()
rec.start()                          # start global hotkey listener
rec.begin_recording("loop", countdown=3)  # 3s countdown, then capture
# ... user plays game ...
steps = rec.stop_recording()         # returns list[CompiledStep]
result = rec.consume_result()        # get buffered result dict
rec.stop()                           # cleanup
```

Key design decisions:
- Only game keys captured (j/u/i/o/r/1/2/space/wasd)
- Short press (<250ms) → press, long press → hold
- Gaps >300ms → wait steps
- Results are buffered for async consumption by frontend
- Hotkey F9 toggles, F11 force-stops

## Usage

```python
from anime_game_afk.games.aether_gazer.combat import AutoBattleService, load_script

script = load_script("auto_attack")  # config/combat_scripts/auto_attack.yaml
service = AutoBattleService(script, check_interval=2.0)
await service.start(ctx)
```

## Layer Dependencies

- **Depends on**: Layer 1 (device), Layer 4 (knowledge/keys), Layer 5A (checks)
- **Must not depend on**: Layer 6+ — no upward imports
