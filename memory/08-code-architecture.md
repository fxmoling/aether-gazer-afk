# 代码架构与模块说明 (2026-04-05, updated 2026-04-05 — 9-layer redesign)

## Architecture Redesign Status

**Design spec**: `docs/superpowers/specs/2026-04-05-architecture-redesign-design.md` ✅ approved
**Implementation plans**: `docs/superpowers/plans/2026-04-05-wave{1,2,3,4}*.md` ✅ all 4 waves written
**Execution**: Wave 1 ✅ complete (231 tests), Wave 2 ✅ complete (284 tests), Wave 3 next

## Target 9-Layer Architecture

```
Layer 0  MaaFramework          (external C++ engine)
Layer 1  core/                 Device adapter (device.py, types.py, errors.py)
Layer 2  vision/               Game-agnostic CV tools (matcher.py, ocr.py, color.py, geometry.py)
Layer 3  runtime/              Logging, config, state, clock, events, errors
───────────────────────────── generic above / game-specific below ───
Layer 4  games/aether_gazer/knowledge/   Pure data models (pages, nav graph, keys, constants)
Layer 5  games/aether_gazer/ops/         Atomic ops (perception/, navigate/, interact/, combat/)
Layer 6  games/aether_gazer/tasks/       Composable multi-step tasks (combat_tasks, shop_tasks...)
Layer 7  games/aether_gazer/processes/   User-visible features (daily_routine, push_main_story...)
Layer 8  games/aether_gazer/orchestrator/ Pipeline + YAML plan execution
```

**Dependency rule**: Layer N imports only from Layers 0..(N-1). Game layers (4-8) per-game isolated.

## Current Structure (pre-migration)

```
src/anime_game_afk/
├── core/
│   ├── session.py        # GameSession → will become device.py (Layer 1)
│   └── errors.py         # exceptions
├── config/
│   └── models.py         # GameConfig, TaskResult
├── games/aether_gazer/
│   ├── pages/            # → migrate to knowledge/ (Layer 4) + ops/perception/ (Layer 5)
│   │   ├── definitions.py       # 15 PageDefs + coords + VK codes
│   │   ├── template_identifier.py  # Template matching page ID
│   │   └── identifier.py        # V1 pixel (deprecated)
│   ├── nav/              # → migrate to ops/navigate/ (Layer 5)
│   │   └── navigator.py
│   └── tasks/            # → split into ops/ (L5) + tasks/ (L6) + processes/ (L7)
│       ├── base.py, atomic.py, daily.py

assets/aether_gazer/
├── templates/              # Page signature templates (20 PNG, 15 pages)
│   ├── index.json
│   └── text/               # Text templates for state detection (9 PNG)
```

## Implementation Wave Plan

| Wave | File | Tasks | Scope |
|------|------|-------|-------|
| 1 | `wave1-foundation.md` | 11 | L1-3: Device, Vision, Runtime |
| 2 | `wave2-game-knowledge-ops.md` | 9 | L4-5: Knowledge, Atomic Ops |
| 3 | `wave3-tasks-processes.md` | 8 | L6-7: Tasks, Processes |
| 4 | `wave4-orchestrator-cleanup.md` | 8 | L8: Pipeline + cleanup |

Execute bottom-up: Wave 1 first, then 2, 3, 4.

## Key Migration Mapping

| Current file | Target layer | New location |
|---|---|---|
| core/session.py | L1 | core/device.py |
| pages/definitions.py | L4 | knowledge/pages.py + keys.py |
| pages/template_identifier.py | L5 | ops/perception/identify_page.py |
| nav/navigator.py | L5 | ops/navigate/ (split into 4 files) |
| tasks/atomic.py | L5 | ops/ (split across subdirs) |
| tasks/daily.py | L6+L7 | tasks/ + processes/daily_routine.py |
| scripts/ch6_battle.py | L5+L6+L7 | ops/combat/ + tasks/combat_tasks.py + processes/push_main_story.py |

## Wave 1 Progress

| Task | Status | Files |
|------|--------|-------|
| Task 1: Core types + errors | ✅ DONE | `core/types.py` (new), `core/errors.py` (updated), `tests/core/test_types.py` (17 tests) |
| Task 2: Device adapter | ✅ DONE | `core/device.py` (new), `core/session.py` (deprecation wrapper), `tests/core/test_device.py` (27 tests) |
| Task 3: Vision types | ✅ DONE | `vision/types.py` (MatchResult, TextResult), `tests/vision/test_types.py` (16 tests) |
| Task 4: Vision matcher | ✅ DONE | `vision/matcher.py` (match_template, match_best, match_all + NMS), `tests/vision/test_matcher.py` (21 tests) |
| Task 5: Vision geometry/color | ✅ DONE | `vision/geometry.py` (crop, resize, find_contours), `vision/color.py` (find_color_regions, color_ratio), `tests/vision/test_geometry.py` (13 tests), `tests/vision/test_color.py` (12 tests) |
| Task 6: Vision OCR stub | ✅ DONE | `vision/ocr.py` (recognize_text — template-matching backend), `tests/vision/test_ocr.py` (10 tests) |
| Task 7: Runtime logger | ✅ DONE | `runtime/logger.py` (Logger, get_logger, with_context), `tests/runtime/test_logger.py` (20 tests) |
| Task 8: Runtime config | ✅ DONE | `runtime/config.py` (ConfigStore — from_yaml/from_dict, get/set/has dot-path), `tests/runtime/test_config.py` (29 tests) |
| Task 9: Runtime state+clock | ✅ DONE | `runtime/state.py` (StateStore — JSON persistence), `runtime/clock.py` (Cooldown, Timer), `tests/runtime/test_state.py` (19 tests), `tests/runtime/test_clock.py` (18 tests) |
| Task 10: Runtime events+errors | ✅ DONE | `runtime/events.py` (EventBus + 5 constants), `runtime/errors.py` (RecoveryStrategy, RetryStrategy, FallbackStrategy), `tests/runtime/test_events.py` (12 tests), `tests/runtime/test_errors.py` (13 tests) |

### Task 1 details (2026-04-05)
- `core/types.py`: `Point`, `Rect`, `Resolution` frozen dataclasses. `Rect.contains()`, `.x2`, `.y2` properties.
- `core/errors.py`: English docstrings; `DeviceError(AutomationError)` added as base for `WindowNotFoundError`, `ConnectionError`, `ScreenshotError`.
- All 17 unit tests pass.
- Commit: `feat(core): add shared types and clean up error hierarchy`

### Task 2 details (2026-04-05)
- `core/device.py`: `DeviceAdapter` class — connect/disconnect, screenshot (design-res + raw), click, swipe, press_key, hold_key. Auto-scales design→actual coords. No Resource/Tasker (device I/O only).
- `core/session.py`: Added `import warnings` + `warnings.warn(DeprecationWarning)` in `__init__`. Module docstring updated with deprecation notice pointing to `DeviceAdapter`.
- `tests/core/test_device.py`: 27 unit tests, fully mocked (no real MaaFw). Covers: construction, find_window, connect/disconnect state, coordinate scaling (1:1 and 2×), screenshot resize, ScreenshotError, press_key delegation, hold_key sleep, _ensure_connected guard (6 methods).
- Full core suite: 44/44 passed.
- Commit: `feat(core): add DeviceAdapter and deprecate GameSession`

### Task 7 details (2026-04-05)
- `runtime/logger.py`: `Logger` class + `get_logger(name)` factory. Context dict carried immutably; `with_context(**kv)` returns a new child logger. `_log()` uses `loguru.opt(depth=2)` so file/line points to caller.
- `runtime/__init__.py`: re-exports `Logger`, `get_logger`, `ConfigStore`.
- `tests/runtime/test_logger.py`: 20 tests — emission (info/debug/warning/error), level labels, name prefix, `{}` format args, bad-placeholder safety, `with_context` merge/override/immutability, context in output, `context` property copy.
- All 20 pass.

### Task 8 details (2026-04-05)
- `runtime/config.py`: `ConfigStore` — `from_yaml(path)`, `from_dict(data)`, `get(key, default)`, `set(key, value)`, `has(key)`, `raw` property. All key access uses dot-separated paths with sentinel for `None`-value safety.
- `tests/runtime/test_config.py`: 29 tests — flat/nested get, default, `None` value, partial subtree, path-through-scalar, set with intermediates, overwrite, `has` with `None`, YAML (simple, nested, Path, str, empty, missing).
- All 29 pass. Combined runtime suite: **49/49 passed**.
- Commit: `feat(runtime): add Logger and ConfigStore (Tasks 7+8)`

## Wave 2 Progress (Layer 4 + Layer 5)

| Task | Status | Files |
|------|--------|-------|
| Task 1: constants, keys, resources | ✅ DONE | `knowledge/constants.py`, `keys.py`, `resources.py`, `tests/knowledge/test_keys.py` |
| Task 2: pages.py (15 pages) | ✅ DONE | `knowledge/pages.py`, `tests/knowledge/test_pages.py` (9 tests) |
| Task 3: navigation.py | ✅ DONE | `knowledge/navigation.py`, `tests/knowledge/test_navigation.py` (10 tests) |
| Task 4: ops/base.py | ✅ DONE | `ops/__init__.py`, `ops/base.py`, `ops/README.md`, `tests/ops/test_base.py` (6 tests) |
| Task 5: ops/perception/ | ✅ DONE | `identify_page.py`, `detect_game_state.py`, `README.md`, 5 tests |
| Task 6: ops/navigate/ | ✅ DONE | `wake_hub_ui.py`, `go_back.py`, `return_to_hub.py`, `goto_page.py`, `README.md`, 3 tests |
| Task 7: ops/interact/ | ✅ DONE | `click_element.py`, `skip_cutscene.py`, `advance_dialogue.py`, `confirm_popup.py`, `README.md`, 8 tests |
| Task 8: ops/combat/ | ✅ DONE | `attack_cycle.py`, `handle_revive.py`, `walk_forward.py`, `README.md`, 5 tests |

### Wave 2 Key Design Decisions
- **Op protocol**: `async run(ctx: OpContext) -> OpResult` — every op follows this pattern
- **DevicePort / LoggerPort**: runtime_checkable Protocol interfaces — ops only depend on these ports
- **OpContext**: holds device + logger + state dict; ops import knowledge directly (pure data)
- **GameState enum**: 11 states (BATTLE, CUTSCENE, DIALOGUE, REVIVE_PROMPT, LOADING, etc.)
- **identify() / detect_state()**: pure utility functions, callable without Op wrapper
- **ClickElementOp**: blocks unsafe elements (gacha, inventory) unless `force_unsafe=True`
- **ReturnToHubOp**: max 8 attempts, alternates ESC/click-back, calls `identify()` directly (NOT IdentifyPageOp)
- **GotoPageOp**: uses NavGraph routes, max 2 retries, verifies arrival with `is_on_page()`
- **Module-level template caches**: loaded lazily on first call, reused across invocations
- **Black screen detection**: `mean < 15` → LOADING state (non-template heuristic only for fully black screens)
- **Test strategy**: all tests use MockDevice, `asyncio.get_event_loop().run_until_complete()`, `interval=0.0`/`wait_after=0.0` to avoid real delays

### Full test suite after Wave 2 Tasks 4-8: **284/284 passed**

## Created

- **Date**: 2026-04-05
- **Updated**: 2026-04-05 — Wave 1 complete (112 tests). Wave 2 Tasks 1-3 (knowledge layer) complete. Wave 2 Tasks 4-8 (ops layer) complete. Total: **284/284** tests pass.
