# 代码架构与模块说明 (2026-04-05, updated 2026-04-05 — 9-layer redesign)

## Architecture Redesign Status

**Design spec**: `docs/superpowers/specs/2026-04-05-architecture-redesign-design.md` ✅ approved
**Implementation plans**: `docs/superpowers/plans/2026-04-05-wave{1,2,3,4}*.md` ✅ all 4 waves written
**Execution**: ✅ ALL 4 WAVES COMPLETE — 482 tests passing

## Op/Check/Task 三层重构 (2026-04-07 session 7)

**Design spec**: `docs/superpowers/specs/2026-04-07-op-check-task-refactor-design.md` ✅ approved
**Execution**: ✅ COMPLETE — 532 tests passing (482 → 532, +50 new)

### 核心变更
三种类型，三种职责，硬性边界：
- **Op** — 改变世界（点击、按键、滑动、导航）
- **Check** — 观察世界（截图 + OCR/模板匹配，返回结构化结果 CheckResult）
- **Task** — 编排 Op + Check（禁止直接碰 ctx.device.* 和 vision.*）

### 五条硬规则
1. Task 禁止 `ctx.device.*` — 所有设备交互必须通过 Op
2. Task 禁止直接调视觉函数 — 所有观察必须通过 Check
3. 原始 Op 不调其他 Op — 复合 Op 只用原始 Op + Check
4. Check 不改变状态 — 只截图 + 识别
5. Op 和 Check 都是 class 式 (`__init__` 传参，利于未来序列化)

### 新增文件
- `checks/` 包: base.py, ocr.py, page.py, state.py, vision.py (11 个 Check 类)
- `ops/primitives.py`: 6 个原始 Op (ClickOp, PressKeyOp, HoldKeyOp, SwipeOp, SleepOp, ScreenshotOp)
- `ops/navigate/smart_return.py`: SmartReturnToHubOp (从 helpers 提升)
- `ops/interact/rapid_click.py`: RapidClickOp (从 helpers 提升)

### 重构文件
- 8 个复合 Op: 内部改用原始 Op + Check，不再直接调 ctx.device.*
- 10 个 Task: 全部改用 Op + Check，零 ctx.device.* 调用
- 4 个测试文件更新 mock 路径
- `tests/test_architecture.py`: 自动扫描 tasks/*.py 验证硬规则

### 层级依赖
```
Layer 4:  knowledge/     ← 纯数据
Layer 5A: checks/        ← imports: knowledge, vision (L2)
Layer 5B: ops/           ← imports: knowledge, vision (L2), checks (L5A)
Layer 6:  tasks/         ← imports: ops (L5B), checks (L5A), 禁止 device/vision
Layer 7:  processes/     ← imports: tasks (L6)
```

## Game Launch & User Config (2026-04-06 session 5)

### Persistent User Config (config/user_config.py + config/user_config.yaml)
- YAML-based persistent config for per-game launch settings
- `UserConfig.load()` factory — auto-creates from template if missing
- Per-game accessors: `game_exe_path`, `launcher_path`, `launch_method`, `launch_timeout`, `window_title`, `search_keywords`, `desktop_shortcut_names`
- Global settings: `auto_detect_games`, `search_drives`, `log_level`
- Save/load round-trip with `yaml.dump/safe_load`
- 21 unit tests in `tests/config/test_user_config.py`

### Game Finder (core/game_finder.py)
- Auto-detect game installations using 3 strategies (priority order):
  1. Running process — `wmic process where name=X get ExecutablePath`
  2. Desktop shortcuts — PowerShell WScript.Shell COM to read .lnk targets
  3. Filesystem search — BFS scan of drives for keyword-matching directories
- `GameFinder.find_game_exe(exe_name, keywords, shortcut_names, search_drives)`
- `find_aether_gazer()` convenience: finds both game exe and launcher
- AetherGazer found at: `E:\shenkongzhiyan\AetherGazerLauncher\AetherGazer\AetherGazer.exe`
- Launcher at: `E:\shenkongzhiyan\AetherGazerLauncher\AetherGazerLauncher.exe`
- 13 unit tests in `tests/core/test_game_finder.py`

### Game Launcher (core/game_launcher.py)
- Process lifecycle: `is_running()`, `get_pid()`, `launch()`, `wait_for_process()`, `wait_for_window()`
- `ensure_running()` — single call: checks if running, launches if not, waits for window
- Uses `tasklist` for process detection, `subprocess.Popen` for launching (DETACHED_PROCESS)
- Window detection via MaaFramework `Toolkit.find_desktop_windows()`
- No psutil dependency — pure subprocess + Win32 API
- 13 unit tests in `tests/core/test_game_launcher.py`

### Startup Tasks (tasks/startup_tasks.py)
- **SkipStartupPopups**: Multi-strategy popup dismissal loop
  - Checks: hub detection (template + OCR) → loading → login → idle → popup keywords → aggressive dismiss
  - OCR keywords: _LOADING_KEYWORDS (9), _DISMISS_KEYWORDS (9), _LOGIN_KEYWORDS (4), _EVENT_POPUP_KEYWORDS (6)
  - "前往" (go to event) → ESC instead of click (safety)
  - Aggressive mode: ESC/Enter/Space + 6 known close button positions
  - max_attempts configurable (default 60)
- **LaunchAndReachHub**: Wraps SkipStartupPopups as a Task with metadata
- **ensure_game_running()**: Phase 1 function — call before DeviceAdapter.connect()
- 13 unit tests in `tests/games/aether_gazer/tasks/test_startup_tasks.py`

### Pipeline Integration
- `scripts/run.py` updated with `--launch`, `--no-launch`, `--detect-game` flags
- Phase 1 (pre-connection): resolve game exe + ensure running
- Phase 2 (post-connection): skip popups via LaunchAndReachHub
- Auto-detect saves to `config/user_config.yaml` for future runs
- `default.yaml` updated with launch documentation

## Post-Wave Changes (2026-04-05 session 2)

### RunLog infrastructure (runtime/run_log.py)
- Per-run timestamped log directory: `logs/20260405_143022/`
- Screenshots saved as `001_label.jpg` thumbnails (800x450) under `screenshots/`
- Loguru file sink per run (`run.log`)
- Retention: max 15 run directories, oldest auto-deleted
- `snap(device, label)` — capture from device, save, return original
- `save_image(img, label)` — save existing image
- 7 unit tests in `tests/runtime/test_run_log.py`

### Task metadata upgrade (tasks/base.py)
- Task protocol now requires `description: str` attribute
- Optional metadata: `category`, `requires_pages`, `requires_ocr`, `safe`
- `task_info(task)` helper extracts metadata dict for logging/registry
- All 8 task classes updated with full metadata

### BuyIntelShards (tasks/shop_tasks.py) — NEW
- Extracted from verified `scripts/test_buy_intel_v2.py`
- Strategy: always buy first (leftmost) intel item, repeat until sold out
- Navigation: hub → shop → trade → daily purchase (with OCR verify "修正者情报")
- Buy loop: OCR "情报" in popup before every purchase (safety)
- Metadata: category=daily_shop, requires_ocr=True, safe=False
- Full RunLog integration (screenshots at every step)

### ClaimFreeStamina rewritten (tasks/shop_tasks.py)
- Old version used fabricated coordinates (800,400) — replaced entirely
- New navigation: hub → shop → supply → daily supply
- OCR checks: "免费" (available) vs "冷却" (cooldown = already claimed)
- Confirm button located via OCR, not hardcoded coords

### DailyRoutine updated (processes/daily_routine.py)
- Now runs 7 tasks via _DAILY_TASKS list (data-driven loop)
- Task order: mail → intel shards → stamina packs → mimi station → missions → guild → amusement
- Each task wrapped in try/except, returns to hub between tasks
- Tracks completed/failed lists in result data

### STAMINA_PANEL page + hub Stamina element (session 3)
- Added `STAMINA_PANEL` page to knowledge/pages.py (23 pages total)
  - Tabs: 冷却剂(451,155), 移转之辉(783,153), 每日补给(1113,154)
- Added "Stamina" element to MAIN_HUB at (850,35) → opens stamina_panel
- Hub now has 12 elements

### JointDefenseSweep (tasks/activity_tasks.py) — NEW (session 3)
- Complex multi-step task: hub → activity page → 联防协议 → 震动 → sweep
- Navigation: H button OCR → offset 50px below → activity list scroll
- Mixed identification methods:
  - Template match: verify hub page
  - OCR: "前往作战" (hub active), "联防协议", "前往挑战", "信息集纳", "震动", "扫荡"
  - Fixed coord: >> max multiplier button (1470,716) — graphical, OCR unreadable
- Sweep consumes 30 吨吨值 per run (safe=False)
- _safe_return_to_hub: ESC×3 + fallback ReturnToHubOp
- Verified full flow end-to-end (2026-04-05): 183 吨吨值→153, drops obtained

### 4 new daily tasks (session 4, 2026-04-06)

**Shared helpers (tasks/helpers.py)**:
- `smart_return_to_hub(ctx)`: back(35,35) → ESC → Enter (if unchanged) cycle, max 10 attempts + fallback
- `rapid_click(ctx, x, y, times, interval)`: fixed-position multi-click for popup dismissal

**MimiStationCollect (tasks/observation_tasks.py)**:
- Flow: G → 弥弥观测站(110,820) → 一键领取(1205,809) ×5 → x10/x8(OCR) ×5 → hub
- Verified: rewards collected, characters re-dispatched (19:59:57 countdown started)

**DailyWeeklyMissionClaim (tasks/observation_tasks.py)**:
- Flow: G → 一键领取(1480,860) ×5 → 周常任务(80,195) → 一键领取(1480,860) ×5 → hub
- All fixed coords, no OCR needed

**GuildSupplyClaim (tasks/guild_tasks.py)**:
- Flow: 公会(1025,850) → 矩阵补给(OCR) → 领取(OCR) → hub
- Verified: "获得物品 ×50" popup dismissed with Enter

**AmusementStreetDaily (tasks/amusement_tasks.py)**:
- Flow: 游园街(1257,850) → 面板(1240,860) → 自动放置(1084,826) → 一键投喂(1368,826)
       → 领取收益(OCR) → 可委托/派遣完成(OCR) → Enter → 一键派遣(OCR) → ESC×2 → hub
- Mixed: fixed coords for panel buttons, OCR for dynamic elements
- Verified: 3676/10000→0/10000 income collected, 3 tasks dispatched (19:59:58)

### ClaimDailyStaminaPacks (tasks/shop_tasks.py) — NEW (session 3)
- Navigation: hub → click stamina display (top bar NNN/NNN pattern) → 每日补给 tab
- Two packs per day: 每日上午 (11:00+, 30 stamina) + 每日下午 (18:00+, 30 stamina)
- OCR finds "领取" buttons, filters out "已领取" (already claimed)
- Verified coordinates (2026-04-05):
  - Stamina display: OCR `NNN/NNN` at ~(851,43), click LEFT edge to avoid "+"
  - Tabs: 冷却剂(451,155), 移转之辉(783,153), 每日补给(1113,154)
  - Pack items: ~(893,571) and ~(1207,569), claim buttons ~(891,485) and ~(1208,485)
- Successfully tested: stamina went from 174/240 → 204/240 (30 pts claimed)
- DailyRoutine now uses this instead of ClaimFreeStamina

## Architecture Summary (post-migration)

```
src/anime_game_afk/
├── core/              # L1: types.py, device.py, errors.py (session.py deprecated)
├── vision/            # L2: matcher.py, geometry.py, color.py, ocr.py (RapidOCR), types.py
├── runtime/           # L3: logger.py, config.py, state.py, clock.py, events.py, errors.py, run_log.py
├── ui/                # L9: app.py, api.py, bridge.py, task_manager.py, web/ (pywebview GUI)
└── games/aether_gazer/
    ├── knowledge/     # L4: constants.py, keys.py, resources.py, pages.py (22 pages), navigation.py (42 edges BFS)
    ├── ops/           # L5: base.py + perception/ + navigate/ + interact/ + combat/
    ├── tasks/         # L6: base.py (Task protocol w/ metadata) + combat/navigation/shop/mail/stamina/story_tasks.py
    ├── processes/     # L7: base.py + push_main_story.py + daily_routine.py
    └── orchestrator/  # L8: types.py + pipeline.py + executor.py + recovery.py + plans/
```

## Target 10-Layer Architecture

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
───────────────────────────── application layer ───
Layer 9  ui/                   pywebview GUI (app.py, api.py, bridge.py, task_manager.py, web/)
```

**Dependency rule**: Layer N imports only from Layers 0..(N-1). Game layers (4-8) per-game isolated.
UI (L9) imports from L8 (orchestrator), L7 (processes), L6 (tasks), L3 (runtime), L1 (core). Nothing imports from ui/.

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

## UI Layer (Layer 9) — 2026-04-06

### Design
- **Spec**: `docs/superpowers/specs/2026-04-06-ui-design.md`
- **Framework**: pywebview + vanilla HTML/CSS/JS (no React/Vue)
- **Dependency**: `pywebview>=5.0` (~5MB, uses system WebView2)
- **Theme**: Dark mode only

### Files
| File | Purpose |
|---|---|
| `ui/__init__.py` | Package marker |
| `ui/app.py` | Entry point: creates pywebview window |
| `ui/api.py` | Api class: 9 methods exposed to JS via js_api |
| `ui/bridge.py` | LogForwarder: loguru sink → evaluate_js push |
| `ui/task_manager.py` | TaskManager: pipeline/task state + bg execution |
| `ui/web/index.html` | HTML: sidebar nav, tasks page, logs page |
| `ui/web/style.css` | Dark theme CSS |
| `ui/web/app.js` | Frontend logic: page switch, API calls, DOM updates |

### Architecture
- Pipeline-driven: user selects pipeline (daily_routine/push_main_story), toggles tasks
- Communication: pywebview `js_api` (JS→Python) + `evaluate_js` (Python→JS push)
- No HTTP server, no WebSocket — all through pywebview bridge
- Worker thread runs `asyncio.run(pipeline)`, main thread runs pywebview event loop
- Config persistence: `config/ui_state.json` (atomic write)
- **Zero changes to existing L1-L8 code**

### Launch
```bash
python -m anime_game_afk.ui.app         # normal
python -m anime_game_afk.ui.app --debug  # with devtools
```

## Created

- **Date**: 2026-04-05
- **Updated**: 2026-04-05 — Wave 1 complete (112 tests). Wave 2 Tasks 1-3 (knowledge layer) complete. Wave 2 Tasks 4-8 (ops layer) complete. Total: **284/284** tests pass.

## E2E Performance Benchmarks (2026-04-06)

### DailyRoutine 10-task full run (20:48:57 → 20:53:41 = ~4m44s)

| # | Task | Duration | Status | Notes |
|---|------|----------|--------|-------|
| 1 | mail | 12s | ✅ | H→全部领取→Enter→hub |
| 2 | intel_shards | 36s | ✅ (0购) | 商店导航较慢，OCR多次 |
| 3 | stamina_packs | 30s | ✅ (2领) | 体力面板→日常补给→领取×2 |
| 4 | free_stamina | 41s | ✅ (跳过) | 免费体力已领，OCR检测耗时 |
| 5 | mimi_station | 33s | ✅ | G→弥弥观测站→一键领取→缩短 |
| 6 | guild_supply | 8s | ✅ (跳过) | OCR找不到矩阵补给 |
| 7 | amusement | 30s | ✅ | 游园街→收益→派遣 |
| 8 | joint_defense | 54s | ✅ | 联防协议→震动→扫荡(已优化OCR) |
| 9 | missions | 14s | ✅ | G→一键领取×5→周常→一键领取×5 |
| 10 | tactics | 17s | ✅ | T→任务→一键领取×3 |

**瓶颈分析**:
- OCR 单次调用 ~2s (scale=0.7)，每个 ocr_once ~2s
- shop_tasks/free_stamina 未优化（仍用旧 ocr_find），占总时间大
- smart_return_to_hub 每轮~4s (template + 1x ocr_once)
- sleep 已按用户反馈缩减（activity_tasks 已优化，其余待优化）

### OCR 优化基础设施 (2026-04-06)

- `ocr_once(img, region=None, scale=0.7)` → `OcrResult` (batch API)
- `OcrResult.find(kw)` / `.has(kw)` / `.has_all(*kws)` — 无额外 OCR 调用
- 旧 3x `ocr_find` (~6.4s) → 1x `ocr_once` (~1.9s) = **3.4x提速**
- scale=0.7 最稳定（0.5 会漏 "前往作战"，1.0 太慢）
- 已优化: helpers.py, return_to_hub.py, wake_hub_ui.py, activity_tasks.py
- 待优化: shop_tasks.py, amusement_tasks.py, observation_tasks.py, guild_tasks.py

### Startup 任务集成 (2026-04-06 session 6)

- `SkipStartupPopups` (tasks/startup_tasks.py) 重写：
  - 修复死循环 bug（"确认/确定" 在非按钮文字中误匹配）
  - 登录屏检测："深空之眼" / "进入游戏" / "点击任意" → click center
  - 事件弹窗：检测 "活动/公告/限时" → click (1540,50) 关闭
  - stuck 检测：3 次未变化 → aggressive dismiss
  - 已在 hub 时 attempt 0 立即返回 success（自动跳过）
- `_DAILY_TASKS` 新增 `("startup", SkipStartupPopups)` 作为第 0 个任务
- `run_daily_routine.py` 完整流程：launch → connect → startup → 10 tasks
- `GameLauncher._find_window()` 修复：精确匹配 + Unity 类过滤

### Hub 检测统一 (2026-04-06 session 6)

- `is_at_hub(img)` / `is_at_hub_with_ocr(img, ocr)` 集中在 helpers.py
- 4 关键词：`("前往作战", "探测", "修正者", "仓库")`
- 所有文件引用统一函数，不再分散判断
- `return_to_hub.py` 用 `_HUB_OCR` 常量（避免跨层导入）

### 窗口匹配修复 (2026-04-06 session 6)

- `device.find_window()` 两级匹配：精确标题 → 子串+UnityWndClass
- 删除了危险的纯子串 pass 3（会误匹配 "AetherGazer AFK" 工具窗口）
- `GameLauncher._find_window()` 同步修复

### UI 层 (2026-04-06 session 5, pywebview GUI)

```
src/anime_game_afk/ui/
├── app.py           # pywebview 入口，创建窗口
├── api.py           # JS→Python API（connect, start, stop, get_status...）
├── bridge.py        # LogForwarder: loguru → JS push
├── task_manager.py  # pipeline 发现、任务执行、状态推送
└── web/
    ├── index.html   # 单页 SPA
    ├── style.css    # 暗色主题
    └── app.js       # 前端逻辑，DOM 操作
```

**已知问题（待下次 session 修复）**:
1. **Stop 按钮不可靠**：当前用 `asyncio.Task.cancel()` 只能在 await 点中断，MaaFramework C++ 调用中无法中断
   - **决定方案**：改为子进程执行，stop = `process.kill()` 100% 立即停止
2. **前端手动 DOM 操作**：当前纯 Vanilla JS，维护成本高
   - **决定方案**：引入 Preact + HTM（~3KB，React API，无构建步骤）
3. **OCR 剩余 task 未优化**：shop_tasks, amusement_tasks, observation_tasks, guild_tasks 仍用旧 `ocr_find`

### 下次 Session 计划

**优先级 1 — 子进程 worker**:
```
主进程 (UI + pywebview)
  └── subprocess.Popen → worker 进程 (asyncio + 任务执行)
       ├── stdout/pipe 推送日志和状态
       └── stop → process.kill() / process.terminate()
```
- 修改 task_manager.py：`_run_pipeline` 改为 spawn subprocess
- worker 入口脚本：接收 pipeline_id + enabled_tasks → 执行 → stdout JSON 日志
- kill 后 MaaFramework 的 BlockInput/资源由 OS 回收

**优先级 2 — 前端重构 (Preact + HTM)**:
- CDN 引入 Preact + HTM（零构建步骤）
- 组件化：ConnectionBar, TaskList, TaskItem, LogViewer
- 响应式状态替代手动 DOM 操作

**优先级 3 — OCR 性能优化剩余 tasks**:
- shop_tasks.py（19 OCR calls, 36.3s sleep）
- amusement_tasks.py（9 OCR calls, 18s sleep）
- observation_tasks.py, guild_tasks.py

## PyInstaller 打包 (2026-04-07)

### 打包方案
- **工具**: PyInstaller 6.19.0, onedir 模式
- **入口**: `launcher.py` (frozen-friendly, 路径自适应)
- **构建脚本**: `build.py` (一键打包, 自动生成 .spec)

### 关键文件
| 文件 | 用途 |
|------|------|
| `build.py` | 构建脚本 (`python build.py --clean --zip`) |
| `launcher.py` | 打包后入口点 (替代 scripts/run.py) |
| `anime-game-afk.spec` | PyInstaller 配置 (自动生成, 不提交) |

### 产物结构
```
dist/anime-game-afk/
├── anime-game-afk.exe   # 主程序 (~6MB)
├── config/              # 用户配置 (可编辑)
├── plans/               # 执行计划 (可自定义)
├── logs/                # 运行日志
└── _internal/           # Python 运行时 + 依赖 (~520MB)
    ├── maa/bin/         # MaaFw 16个 DLL
    ├── MaaAgentBinary/  # adb agent 工具
    ├── assets/          # 游戏资源图片
    └── ...              # Python packages
```

### 依赖处理
- MaaFw DLL: 从 site-packages/maa/bin/ 收集到 _internal/maa/bin/
- MaaAgentBinary: 完整复制 (minicap/minitouch/maatouch)
- MAAFW_BINARY_PATH 环境变量: launcher.py 自动设置
- os.add_dll_directory(): Windows DLL 搜索路径
- 排除: pytest, mypy, ruff, torch, matplotlib 等开发/无关依赖

### 验证
- `--list`: ✅ 进程列表正常
- `--dry-run`: ✅ 计划解析正常
- `--help`: ✅ 参数帮助正常
- ZIP 包: 353.2 MB

### E2E 完整流程验证 (2026-04-06 23:21)

- 10/10 + startup 全部成功
- 总时间 318.6s (~5m19s) 含启动+登录+全部任务
- 窗口匹配正确（精确匹配 'AetherGazer' + UnityWndClass）
- Startup: 登录屏 → click center → 加载 → Hub（5 attempts, ~21s）
