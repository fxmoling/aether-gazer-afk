# Auto-Battle System Design

## Problem

`duowei_tasks.py._fight_battle()` has ~40 lines of inline combat logic (key sequence + OCR-based battle-end detection) that is:
1. Not reusable by other tasks or future auto-battle features
2. Hardcoded key sequence with no user customization
3. Uses OCR for battle-end detection instead of the faster InBattleCheck

We need a standalone auto-battle module that:
- Loads user-customizable combat scripts (YAML)
- Executes key sequences in a loop while in battle
- Uses InBattleCheck (triple-signal, ~1ms) for state monitoring
- Works as a toggle service: monitor → fight → monitor → …

## Architecture

### Layer Placement

| Component | Layer | Location |
|-----------|-------|----------|
| `CombatScript` (data model) | Layer 4 Knowledge | `combat/script.py` |
| `CombatRunner` (execution) | Layer 5B Ops | `combat/runner.py` |
| YAML script files | User config | `config/combat_scripts/` |

The `combat/` package lives under `src/anime_game_afk/games/aether_gazer/combat/`.

### Concurrency Model

AsyncIO with two concurrent tasks sharing a boolean flag:

```
toggle ON
  ├─ monitor_loop (asyncio.Task):
  │    every 2s: InBattleCheck → set _in_battle flag
  └─ combat_loop (asyncio.Task):
  │    while _in_battle: execute script steps
  │    while not _in_battle: idle (sleep 0.5s)
  │
toggle OFF → both loops exit
```

`_in_battle` is a plain `bool` (safe for single-threaded asyncio — only monitor writes, combat reads).

## YAML Combat Script Format

### Schema

```yaml
name: <string>              # Display name
description: <string>       # Optional human-readable description
interval: <float>           # Default seconds between steps (default: 0.12)
steps:                      # Ordered list of actions
  - press: <key>            # Press and release a key
  - press: <key>
    interval: <float>       # Override default interval for this step
  - hold: <key>             # Hold a key for duration
    duration: <float>       # Seconds to hold (required for hold)
  - wait: <float>           # Explicit sleep (no key press)
```

### Key Names

Single characters (`j`, `u`, `i`, `o`, `r`, `1`, `2`, `w`, `a`, `s`, `d`) or `space`.
Case-insensitive. Converted to VK codes via `letter_to_vk()`.

### Example: default.yaml (current duowei sequence)

```yaml
name: 默认连招
description: 通用攻击循环 — Attack×2 Skill1 Attack Skill2 Attack Skill3 Ultimate QTE1 QTE2
interval: 0.12
steps:
  - press: j    # Attack
  - press: j    # Attack
  - press: u    # Skill 1
  - press: j    # Attack
  - press: i    # Skill 2
  - press: j    # Attack
  - press: o    # Skill 3
  - press: r    # Ultimate
  - press: "1"  # QTE 1
  - press: "2"  # QTE 2
```

### Example: shikoudi.yaml (诗寇蒂 from AetherGazer-ahk)

```yaml
name: 诗寇蒂
description: Skill2 → Attack → Skill3 → Ultimate → QTE1 → Attack → QTE2
interval: 0.12
steps:
  - press: i    # Skill 2
  - press: j    # Attack
  - press: o    # Skill 3
  - press: r    # Ultimate
  - press: "1"  # QTE 1
  - press: j    # Attack
  - press: "2"  # QTE 2
```

## Components

### 1. CombatScript (`combat/script.py`)

```python
@dataclass(frozen=True)
class CombatStep:
    """Single action in a combat script."""
    action: Literal["press", "hold", "wait"]
    key: str | None        # Key name (None for wait)
    vk_code: int | None    # Resolved VK code (None for wait)
    duration: float        # Hold duration (for hold) or sleep (for wait)
    interval: float        # Post-action wait

@dataclass(frozen=True)
class CombatScript:
    """Loaded and validated combat script."""
    name: str
    description: str
    steps: tuple[CombatStep, ...]

def load_script(name: str) -> CombatScript:
    """Load a named script from config/combat_scripts/{name}.yaml."""

def load_script_file(path: Path) -> CombatScript:
    """Load a script from an arbitrary YAML file path."""
```

**Validation** (at load time):
- `steps` must be non-empty
- Each step must have exactly one of `press`, `hold`, or `wait`
- `hold` steps must have `duration > 0`
- Key names must resolve via `letter_to_vk()`
- `interval` defaults to the top-level `interval` (default 0.12)

### 2. CombatRunner (`combat/runner.py`)

Two levels of API:

```python
async def execute_cycle(ctx: OpContext, script: CombatScript) -> None:
    """Execute one complete cycle of the script (all steps once).

    Stateless function — caller manages looping and battle detection.
    """
    for step in script.steps:
        if step.action == "press":
            ctx.device.press_key(step.vk_code)
        elif step.action == "hold":
            ctx.device.hold_key(step.vk_code, step.duration)
        # wait steps and post-action interval
        await asyncio.sleep(step.interval if step.action != "wait" else step.duration)


class CombatRunner:
    """Loops execute_cycle while active flag is True.

    The active flag is controlled externally (by AutoBattleService
    or by task code directly). Runner checks it between EACH step
    for responsive stop.
    """

    def __init__(self, script: CombatScript):
        self._script = script
        self.active: bool = False

    async def run(self, ctx: OpContext) -> None:
        """Loop script steps while self.active is True.

        Exits when self.active becomes False.
        Between each step, yields via asyncio.sleep and checks active.
        """
```

**Step execution:**
- `press`: `ctx.device.press_key(vk)` → `asyncio.sleep(interval)`
- `hold`: `ctx.device.hold_key(vk, duration)` → `asyncio.sleep(interval)`
- `wait`: `asyncio.sleep(duration)`

### 3. AutoBattleService (`combat/service.py`)

```python
class AutoBattleService:
    """Toggle-based auto-battle: monitor battle state + run combat script.

    Two usage patterns:

    Pattern A — Toggle (user-driven, runs until stop()):
        service = AutoBattleService(script)
        task = asyncio.create_task(service.start(ctx))
        ...  # user clicks stop
        service.stop()
        await task

    Pattern B — Run-once (task-driven, auto-stops when battle ends):
        service = AutoBattleService(script)
        await service.run_until_battle_ends(ctx)
    """

    def __init__(self, script: CombatScript, check_interval: float = 2.0):
        self._script = script
        self._check_interval = check_interval
        self._runner = CombatRunner(script)
        self._enabled = False

    async def start(self, ctx: OpContext) -> None:
        """Start monitor + combat loops. Blocks until stop() called."""
        self._enabled = True
        await asyncio.gather(
            self._monitor_loop(ctx),
            self._combat_loop(ctx),
        )

    def stop(self) -> None:
        """Signal both loops to exit."""
        self._enabled = False
        self._runner.active = False

    async def run_until_battle_ends(self, ctx: OpContext) -> None:
        """Start, wait for battle to begin and end, then auto-stop.

        For task-driven usage (e.g. duowei): enter battle screen,
        call this, it fights until InBattleCheck goes False, returns.
        """
        self._enabled = True
        monitor = asyncio.create_task(self._monitor_loop(ctx))
        combat = asyncio.create_task(self._combat_loop(ctx))
        try:
            # Wait for battle to start
            while self._enabled and not self._runner.active:
                await asyncio.sleep(0.5)
            # Wait for battle to end
            while self._enabled and self._runner.active:
                await asyncio.sleep(0.5)
        finally:
            self.stop()
            await asyncio.gather(monitor, combat, return_exceptions=True)

    @property
    def in_battle(self) -> bool:
        return self._runner.active

    async def _monitor_loop(self, ctx: OpContext) -> None:
        """Periodically check InBattleCheck, update runner.active."""
        check = InBattleCheck()
        while self._enabled:
            result = await check.evaluate(ctx)
            self._runner.active = result.passed
            await asyncio.sleep(self._check_interval)

    async def _combat_loop(self, ctx: OpContext) -> None:
        """Run CombatRunner, exits when not enabled."""
        while self._enabled:
            if self._runner.active:
                await execute_cycle(ctx, self._script)
            else:
                await asyncio.sleep(0.5)
```

## duowei_tasks.py Refactor

### Before (~40 lines)
```python
async def _fight_battle(self, ctx: TaskContext) -> str:
    for check in range(self._BATTLE_MAX_CHECKS):
        for _ in range(self._BATTLE_CHECK_INTERVAL):
            for vk in self._attack_keys:
                ctx.device.press_key(vk)
                time.sleep(0.12)
            time.sleep(0.2)
        img = ctx.screenshot()
        ocr = ocr_once(img)
        # ... OCR-based detection (~20 lines)
```

### After (~5 lines)
```python
async def _fight_battle(self, ctx: TaskContext) -> str:
    script = load_script("default")
    service = AutoBattleService(script, check_interval=2.0)
    await service.run_until_battle_ends(ctx)
    return "won"
```

`run_until_battle_ends()` waits for InBattleCheck to go True (battle starts), fights, then returns when InBattleCheck goes False (battle ends). No OCR needed.

Note: duowei's existing OCR-based battle-end detection (`击退`, `珍宝`, `失败`) is replaced by InBattleCheck which is faster and already tested. The existing OCR checks for `won`/`died`/`timeout` distinctions are lost, but duowei doesn't branch on them meaningfully — it always proceeds to `_handle_reward()`.

## File Inventory

| File | Action | Description |
|------|--------|-------------|
| `src/.../combat/__init__.py` | Create | Package init, re-exports |
| `src/.../combat/script.py` | Create | CombatScript + CombatStep + load_script() |
| `src/.../combat/runner.py` | Create | execute_cycle() + CombatRunner class |
| `src/.../combat/service.py` | Create | AutoBattleService (monitor + runner) |
| `config/combat_scripts/default.yaml` | Create | Current duowei sequence |
| `config/combat_scripts/shikoudi.yaml` | Create | 诗寇蒂 from AetherGazer-ahk |
| `src/.../tasks/duowei_tasks.py` | Modify | Replace _fight_battle + remove _build_attack_keys |

## Testing

- **Unit**: Load scripts, validate bad YAML raises errors, step execution order
- **Integration**: Load default.yaml → CombatRunner runs → keys pressed in order
- **Live**: Toggle on in actual battle → verify keys are pressed → battle ends → stops

## Out of Scope

- Character-specific script auto-selection (no character detection yet)
- Conditional logic in scripts (cooldown-aware, HP-based decisions)
- Frontend UI for script editing (future)
- Multiple simultaneous scripts
