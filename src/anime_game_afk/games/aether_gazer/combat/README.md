# combat/ — Auto-Battle System (Layer 5B)

YAML-driven combat scripts + execution engine + battle state monitoring.

## Files

| File | Purpose |
|------|---------|
| `script.py` | `CombatScript` + `CombatStep` data model. YAML loader from `config/combat_scripts/{name}.yaml`. Pure data. |
| `runner.py` | `execute_cycle()` runs one pass of all script steps. `CombatRunner` loops while `active=True`. |
| `service.py` | `AutoBattleService` — toggle-based auto-battle with two patterns: user-driven toggle or run-once task-driven. |

## Step Types

- **press** — Tap key once, then wait `interval` seconds
- **hold** — Hold key for `duration` seconds, then wait `interval` seconds
- **wait** — Sleep for `duration` seconds

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
