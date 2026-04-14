# Code Review Lessons (2026-04-05)

Lessons from Wave 1 code review. **Must check for these in all future code.**

## Critical Patterns to Avoid

### 1. Layer Isolation Violations
**Problem**: `core/device.py` imported `GameConfig` from `config/models.py` — outside the layer system.
**Rule**: Layer N only imports from Layers 0..(N-1). Never import from outside the layer hierarchy.
**Fix**: Created `DeviceConfig` in `core/types.py` so device.py stays within Layer 1.

### 2. Shadowing Python Builtins
**Problem**: `class ConnectionError(DeviceError)` shadowed `builtins.ConnectionError`.
**Rule**: Never name a class the same as a Python builtin. Use prefixed names.
**Fix**: Renamed to `DeviceConnectionError`, kept backward-compat alias temporarily.

### 3. Fake "Hold" via Press+Sleep
**Problem**: `hold_key()` did press→release→sleep. Key was already released before the sleep.
**Rule**: When simulating a held key without key-down/key-up API, use rapid repeated presses.
**Fix**: Changed to a press loop (every 100ms) for the duration.

## Important Patterns to Avoid

### 4. Event Handler Exception Propagation
**Problem**: `EventBus.emit()` — one handler exception killed all subsequent handlers.
**Rule**: Always wrap handler calls in try/except in event buses and callback loops.
**Fix**: Added try/except with loguru logging per handler.

### 5. Non-Atomic File Writes
**Problem**: `StateStore._save()` opened file with `"w"` (truncates first), then wrote. Crash mid-write = data loss.
**Rule**: Always use atomic writes for persistent state: write to `.tmp`, then `os.replace()`.
**Fix**: Write to `.json.tmp`, then `os.replace()` to atomically swap.

### 6. Corrupt File Crashes on Load
**Problem**: `StateStore._load()` — `json.load()` on corrupt file raises `JSONDecodeError`, crashing the app on startup.
**Rule**: Always handle corrupt/malformed files gracefully. Back up, log warning, start fresh.
**Fix**: Catch `JSONDecodeError`, back up corrupt file to `.json.corrupt`, start with empty dict.

### 7. Mutable Global Sentinels
**Problem**: `_NO_MATCH = MatchResult(...)` was a shared mutable object. Caller mutation corrupts it globally.
**Rule**: Never return shared mutable sentinels. Use factory functions or frozen dataclasses.
**Fix**: Replaced `_NO_MATCH` with `_no_match()` factory that returns a fresh instance each time.

### 8. Test Mocks Must Match Real Import Paths
**Problem**: After Op/Check refactoring, tests still patched old import paths like `tasks.startup_tasks.is_on_page` — but tasks no longer import those functions directly. They use Check/Op classes which import the functions internally.
**Rule**: When refactoring imports, always update test mock paths to match where the function is actually looked up at runtime.
**Fix** (2026-04-07): Updated all 4 task test files (22 failures → 0):
- `test_startup_tasks.py`: Patch `checks.page.is_on_page`, `checks.page.ocr_once`, `checks.ocr.ocr_once` (the Check modules' imports)
- `test_combat_tasks.py`: Patch `machine._detect.evaluate` (CheckResult) instead of `.run` (OpResult)
- `test_mail_tasks.py`: Patch `SmartReturnToHubOp.run` instead of `mail_tasks.smart_return_to_hub`
- `test_shop_tasks.py`: Patch `checks.ocr.ocr_find` instead of `shop_tasks.ocr_find`

## Checklist for Future Code Reviews

- [ ] Layer isolation: does each file only import from lower layers?
- [ ] No builtin shadowing: class names don't collide with builtins?
- [ ] Event/callback loops: exceptions caught per handler?
- [ ] File writes: atomic (write .tmp then os.replace)?
- [ ] File reads: corrupt/missing handled gracefully?
- [ ] Mutable globals: no shared mutable sentinels returned to callers?
- [ ] Simulated key holds: using rapid presses, not press+sleep?
- [ ] Test mocks: patch paths match where the function is actually imported?
