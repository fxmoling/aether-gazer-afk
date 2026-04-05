# Architecture Redesign — Layered Game Automation Framework

**Date**: 2026-04-05
**Status**: Design approved, pending implementation plan
**Scope**: Full codebase restructure from flat scripts to layered architecture

---

## 1. Problem Statement

The project has grown organically through exploration. Scripts in `scripts/` contain logic that belongs in `src/`. The core `src/` directory has minimal structure — a thin MaaFw wrapper, page definitions, and task stubs. Battle automation logic (`ch6_battle.py`, 379 lines) mixes state detection, combat control, navigation, and error recovery in a single file.

We need a layered architecture that:
- Separates generic infrastructure from game-specific logic
- Supports both declarative navigation workflows and real-time combat state machines
- Makes each component independently testable and replaceable
- Scales to multiple games without duplication of infrastructure
- Enforces clean code: small files (~200 lines max), README per directory, English comments

---

## 2. Architecture Overview

Nine layers, strict downward dependency. No layer may import from a higher layer.

```
Layer 0  MaaFramework          C++ engine (external dependency)
Layer 1  Device Adapter        Python wrapper for MaaFw device interaction
Layer 2  Vision Toolkit        Game-agnostic computer vision tools
Layer 3  Runtime Services      Logging, config, state, scheduling, infra-level errors
─────────────────────────────── generic above / game-specific below ───
Layer 4  Game Knowledge        Pure data models (pages, coordinates, nav graph, keys)
Layer 5  Atomic Ops            Smallest executable units (identify, click, navigate, attack)
Layer 6  Composable Tasks      Combinable multi-step sequences (buy items, clear one stage)
Layer 7  Processes             Complete user-visible features (daily routine, push chapter 6)
Layer 8  Orchestrator/Pipeline Task scheduling, plan execution, user configuration
```

**Dependency rule**: Layer N may only import from Layers 0..(N-1). Game layers (4-8) exist per-game under `games/<game_id>/`.

---

## 3. Layer Details

### 3.0 MaaFramework (External)

MaaFramework v5.9.2 C++ core with Python bindings (`maafw` package). Provides:
- Win32/ADB controller for background window interaction
- Screenshot capture
- Click, swipe, key press via PostMessage/SendMessage
- Resource loading

We do not modify this layer.

---

### 3.1 Device Adapter

**Location**: `src/anime_game_afk/core/`
**Responsibility**: Single point of contact with MaaFw. All device interaction goes through here.

```
core/
├── README.md
├── device.py              # DeviceAdapter class
├── types.py               # Shared type definitions (Point, Rect, Resolution)
└── errors.py              # Infrastructure exceptions
```

**DeviceAdapter interface**:

```python
class DeviceAdapter:
    def connect(self, window_title: str, config: DeviceConfig) -> None
    def disconnect(self) -> None

    # Output
    def screenshot(self) -> np.ndarray           # design resolution (e.g. 1600x900)
    def screenshot_raw(self) -> np.ndarray        # actual window resolution

    # Input
    def click(self, x: int, y: int) -> None       # auto-scaled to actual resolution
    def swipe(self, x1, y1, x2, y2, duration_ms: int = 500) -> None
    def press_key(self, vk_code: int) -> None      # single press
    def hold_key(self, vk_code: int, duration_s: float) -> None  # hold for duration

    # Info
    @property
    def resolution(self) -> Resolution             # actual window resolution
    @property
    def design_resolution(self) -> Resolution      # coordinate system used by callers
    @property
    def connected(self) -> bool
```

**Key decisions**:
- All coordinates passed in are in design resolution; scaling happens internally
- `hold_key()` added for WASD exploration movement
- No game logic, no resource loading — pure device I/O
- Renamed from `session.py` to `device.py` for clarity

---

### 3.2 Vision Toolkit

**Location**: `src/anime_game_afk/vision/`
**Responsibility**: Game-agnostic computer vision algorithms. Pure functions: image in, results out.

```
vision/
├── README.md
├── matcher.py             # Template matching (cv2.matchTemplate wrapper)
├── ocr.py                 # OCR interface (template-based now, real OCR later)
├── color.py               # HSV color detection, color region finding
├── geometry.py            # Crop, resize, contour detection
└── types.py               # MatchResult, TextResult, Region, Rect
```

**Design principles**:
- Stateless pure functions. No side effects, no device access, no file I/O.
- Does NOT hold any game resources (templates, models). Callers pass images in.
- Each file stays focused. If `matcher.py` grows (multi-template, feature matching, ONNX), split into a `matching/` package.

**matcher.py core interface**:

```python
def match_template(
    image: np.ndarray,
    template: np.ndarray,
    region: Rect | None = None,
    method: int = cv2.TM_CCOEFF_NORMED,
) -> MatchResult:
    """Match a single template. Returns best match location and score."""

def match_best(
    image: np.ndarray,
    templates: list[np.ndarray],
    region: Rect | None = None,
) -> MatchResult:
    """Try multiple templates, return the best match."""

def match_all(
    image: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.7,
    region: Rect | None = None,
) -> list[MatchResult]:
    """Find all matches above threshold."""
```

**ocr.py**: Initially wraps template matching for known text snippets. Interface designed so a real OCR backend (pytesseract, paddleocr) can be swapped in later without changing callers.

```python
def recognize_text(
    image: np.ndarray,
    region: Rect | None = None,
    templates: dict[str, np.ndarray] | None = None,
) -> list[TextResult]:
    """Recognize text in image region.
    If templates provided, uses template matching.
    If OCR backend available, uses real OCR."""
```

---

### 3.3 Runtime Services

**Location**: `src/anime_game_afk/runtime/`
**Responsibility**: Cross-cutting infrastructure services. Passive — provides tools, does not drive game logic.

```
runtime/
├── README.md
├── logger.py              # Structured logging (wraps loguru or structlog)
├── config.py              # Configuration loading and access
├── state.py               # Persistent state store (survives restarts)
├── clock.py               # Time utilities, cooldown tracking, timers
├── scheduler.py           # Cron-like task scheduling (Phase 2, stub for now)
├── events.py              # Infrastructure-level event bus
└── errors.py              # Recovery framework for infra-level failures
```

**Scope boundaries**:
- `events.py` handles ONLY infrastructure events: `device_disconnected`, `window_lost`, `screenshot_timeout`, `unhandled_exception`, `session_expired`. NOT game events like `battle_started` or `character_died`.
- `errors.py` provides `RecoveryStrategy` base class and common strategies (retry with backoff, fallback chain). Game-specific recovery (revive prompt, mission failed) lives in game layer.
- `logger.py` wraps an established library (loguru recommended). Adds structured context: current game, current task, step number.
- `state.py` persists to JSON. Tracks cross-session state: last completed task, retry counts, timestamps.

**Leverage open-source**: Each module should wrap a proven library rather than reinvent:

| Module | Recommended library | Why |
|---|---|---|
| logger.py | loguru | Structured logging, simple API, file rotation |
| config.py | pydantic + YAML | Typed config with validation |
| state.py | built-in json | Simple key-value persistence |
| clock.py | built-in time | Thin wrappers, no external dep needed |

---

### 3.4 Game Knowledge (Model Layer)

**Location**: `src/anime_game_afk/games/aether_gazer/knowledge/`
**Responsibility**: Pure data. Zero logic, zero imports of cv2/device/vision. The code equivalent of `docs/pages/aether_gazer/*.md`.

```
games/aether_gazer/knowledge/
├── README.md
├── pages.py               # PageDef: id, name, elements with coordinates, safe flags
├── navigation.py          # NavGraph: page→page edges, each edge has action sequence
├── keys.py                # KeyBindings: battle keys, UI shortcuts, VK codes
├── resources.py           # ResourcePaths: template dirs, text template dirs
└── constants.py           # GameConstants: design_resolution, stamina_cap, revive_cost
```

**pages.py example**:

```python
@dataclass(frozen=True)
class PageElement:
    name: str
    x: int
    y: int
    safe: bool = True

@dataclass(frozen=True)
class PageDef:
    id: str
    name: str
    elements: dict[str, PageElement]

PAGES = {
    "main_hub": PageDef(
        id="main_hub",
        name="Main Hub",
        elements={
            "shop": PageElement("shop", 940, 855),
            "inventory": PageElement("inventory", 1141, 853),
            "battle": PageElement("battle", 1465, 850),
            ...
        },
    ),
    ...
}
```

**Key principle**: This layer is hand-maintained. When we discover new coordinates or pages through exploration, we update these files. All other layers read from here.

**Per-game isolation**: Each game has its own `knowledge/` directory. Aether Gazer knowledge is never mixed with or imported by another game.

---

### 3.5 Atomic Operations

**Location**: `src/anime_game_afk/games/aether_gazer/ops/`
**Responsibility**: Smallest executable units. Each op does ONE thing. Takes a context, returns a result.

```
games/aether_gazer/ops/
├── README.md
├── base.py                    # Op protocol, OpResult type, OpContext
│
├── perception/                # "See" — read game state
│   ├── README.md
│   ├── identify_page.py       # → PageId | None
│   ├── detect_game_state.py   # → GameState enum (battle, dialogue, loading, etc.)
│   ├── read_stamina.py        # → int (current stamina)
│   └── check_stage_status.py  # → StageStatus (completed, locked, available)
│
├── navigate/                  # "Go" — move between pages/locations
│   ├── README.md
│   ├── go_back.py             # → press triangle back or circle back
│   ├── return_to_hub.py       # → from anywhere to hub
│   ├── goto_page.py           # → navigate page graph to target
│   └── wake_hub_ui.py         # → recover from hub idle mode
│
├── interact/                  # "Act" — click, press, confirm
│   ├── README.md
│   ├── click_element.py       # → click a named element on current page
│   ├── skip_cutscene.py       # → ESC → wait for confirm → Enter
│   ├── advance_dialogue.py    # → Space to push in-battle dialogue
│   ├── confirm_popup.py       # → detect popup type, respond accordingly
│   └── refill_stamina.py      # → stamina refill flow
│
└── combat/                    # "Fight" — battle-specific actions
    ├── README.md
    ├── attack_cycle.py        # → one round of J/U/I/O/R/1/2 keys
    ├── handle_revive.py       # → detect revive prompt → Enter
    ├── handle_exploration.py  # → WASD movement toward objectives
    └── walk_forward.py        # → hold W for N seconds
```

**Op protocol**:

```python
@dataclass
class OpResult:
    success: bool
    data: Any = None            # op-specific return value
    error: str | None = None

class Op(Protocol):
    async def run(self, ctx: OpContext) -> OpResult: ...
```

**OpContext** provides access to: device, vision tools, game knowledge, logger, state store. Passed down from higher layers.

**Design rules**:
- Each file contains exactly one op (or a small family of closely related ops)
- An op should complete in <10 seconds typically
- Ops do not call other ops. If composition is needed, that belongs in Layer 6.
- Ops handle their own immediate errors (e.g. click didn't register → retry within the op). They do NOT handle cross-op recovery.

---

### 3.6 Composable Tasks

**Location**: `src/anime_game_afk/games/aether_gazer/tasks/`
**Responsibility**: Multi-step sequences built from atomic ops. Can be combined by higher layers. Support conditional logic and loops.

```
games/aether_gazer/tasks/
├── README.md
├── base.py                    # Task protocol, TaskResult, TaskContext
│
├── navigation_tasks.py        # enter_main_story(), go_to_resource_tab(), etc.
├── shop_tasks.py              # buy_daily_items(), claim_free_stamina()
├── mail_tasks.py              # collect_all_mail()
├── combat_tasks.py            # clear_single_stage(), combat_state_machine()
├── story_tasks.py             # navigate_to_chapter(), select_latest_stage()
└── stamina_tasks.py           # check_and_refill_stamina()
```

**Task protocol**:

```python
@dataclass
class TaskResult:
    status: Literal["success", "failed", "skipped"]
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)

class Task(Protocol):
    name: str

    async def execute(self, ctx: TaskContext) -> TaskResult:
        """Run the task. Compose atomic ops with control flow."""
        ...

    async def can_run(self, ctx: TaskContext) -> bool:
        """Check preconditions (e.g. enough stamina, correct page)."""
        ...
```

**combat_state_machine example** (replaces ch6_battle.py):

```python
class CombatStateMachine:
    """Handles in-battle state transitions.
    Composed of atomic ops: attack_cycle, skip_cutscene,
    advance_dialogue, handle_revive, handle_exploration."""

    async def execute(self, ctx: TaskContext) -> TaskResult:
        while not self.battle_complete:
            state = await ops.detect_game_state(ctx)

            if state == GameState.BATTLE:
                await ops.attack_cycle(ctx)
            elif state == GameState.CUTSCENE:
                await ops.skip_cutscene(ctx)
            elif state == GameState.DIALOGUE:
                await ops.advance_dialogue(ctx)
            elif state == GameState.REVIVE_PROMPT:
                await ops.handle_revive(ctx)
            elif state == GameState.LOADING:
                await ctx.clock.wait(1.0)
            elif state == GameState.STAGE_MAP:
                self.battle_complete = True
            else:
                await self.unknown_handler(ctx, state)

        return TaskResult(status="success")
```

**Key principle**: Tasks are the building blocks that Processes use. A task like `clear_single_stage()` handles the full flow for one stage (prep → continuous prompt → team select → combat state machine → result). Processes combine these tasks.

---

### 3.7 Processes (Complete Features)

**Location**: `src/anime_game_afk/games/aether_gazer/processes/`
**Responsibility**: User-visible complete features. Each is a "final class" — not composable by other processes. Internally composed of Layer 6 tasks.

```
games/aether_gazer/processes/
├── README.md
├── base.py                    # Process protocol
├── daily_routine.py           # "Complete daily tasks and claim rewards"
├── push_main_story.py         # "Push main story chapter N"
├── farm_resources.py          # "Spend stamina on resource stages"
├── dream_realm.py             # "Clear 梦境再构"
└── weekly_bosses.py           # "Clear weekly boss stages"
```

**Process example**:

```python
class PushMainStory(Process):
    name = "push_main_story"
    description = "Push main story from current progress"

    async def execute(self, ctx: ProcessContext) -> ProcessResult:
        await tasks.return_to_hub(ctx)
        await tasks.enter_main_story(ctx)

        chapter = ctx.config.get("target_chapter", "current")
        await tasks.navigate_to_chapter(ctx, chapter)

        stages_cleared = 0
        while stages_cleared < ctx.config.get("max_stages", 50):
            stage = await tasks.find_latest_stage(ctx)
            if stage is None:
                break  # chapter complete

            if not await tasks.check_and_refill_stamina(ctx, required=stage.cost):
                break  # out of stamina and refills

            result = await tasks.clear_single_stage(ctx, stage)
            if result.status == "failed":
                ctx.logger.warning("Stage failed, stopping push")
                break

            stages_cleared += 1

        await tasks.return_to_hub(ctx)
        return ProcessResult(
            status="success",
            data={"stages_cleared": stages_cleared},
        )
```

**Key principle**: Each process is what shows up in the user's checkbox list. "Push main story ✓" is one process. The user does not see or configure individual tasks or ops.

---

### 3.8 Orchestrator / Pipeline

**Location**: `src/anime_game_afk/games/aether_gazer/orchestrator/`
**Responsibility**: Execute a user-configured selection of processes. Handle cross-process concerns.

```
games/aether_gazer/orchestrator/
├── README.md
├── pipeline.py                # Load user config → build process list → execute
├── executor.py                # Run processes sequentially with logging/timing
├── recovery.py                # Cross-process recovery (relogin, reconnect)
└── plans/                     # User-facing plan definitions
    └── default.yaml           # Default plan template
```

**User configuration** (YAML):

```yaml
# user_plan.yaml
game: aether_gazer
processes:
  - name: daily_routine
    enabled: true

  - name: push_main_story
    enabled: true
    config:
      target_chapter: current
      max_stages: 20

  - name: dream_realm
    enabled: false

  - name: farm_resources
    enabled: true
    config:
      stages: ["模拟作战", "极限萃取"]
      max_runs: 6
```

**Pipeline execution**:

```python
class Pipeline:
    async def run(self, plan_path: str):
        plan = load_plan(plan_path)
        enabled = [p for p in plan.processes if p.enabled]

        self.logger.info("Starting pipeline: %d processes", len(enabled))
        for proc_def in enabled:
            process = self.load_process(proc_def.name)
            ctx = self.build_context(proc_def.config)

            try:
                result = await process.execute(ctx)
                self.logger.info("Process %s: %s", proc_def.name, result.status)
            except InfrastructureError as e:
                recovered = await self.recovery.handle(e, ctx)
                if not recovered:
                    self.logger.error("Unrecoverable error, stopping pipeline")
                    break

        self.logger.info("Pipeline complete")
```

**recovery.py scope**: Only infrastructure-level failures that no single process can handle — device disconnect, window lost, game crash, login session expired. Game-level failures (battle failed, stamina empty) are handled within processes.

---

## 4. Directory Structure Summary

```
src/anime_game_afk/
├── README.md                          # Project overview
├── core/                              # Layer 1: Device Adapter
│   ├── README.md
│   ├── device.py
│   ├── types.py
│   └── errors.py
├── vision/                            # Layer 2: Vision Toolkit
│   ├── README.md
│   ├── matcher.py
│   ├── ocr.py
│   ├── color.py
│   ├── geometry.py
│   └── types.py
├── runtime/                           # Layer 3: Runtime Services
│   ├── README.md
│   ├── logger.py
│   ├── config.py
│   ├── state.py
│   ├── clock.py
│   ├── scheduler.py
│   ├── events.py
│   └── errors.py
└── games/
    └── aether_gazer/
        ├── README.md                  # Game overview
        ├── knowledge/                 # Layer 4: Game Knowledge
        │   ├── README.md
        │   ├── pages.py
        │   ├── navigation.py
        │   ├── keys.py
        │   ├── resources.py
        │   └── constants.py
        ├── ops/                       # Layer 5: Atomic Operations
        │   ├── README.md
        │   ├── base.py
        │   ├── perception/
        │   ├── navigate/
        │   ├── interact/
        │   └── combat/
        ├── tasks/                     # Layer 6: Composable Tasks
        │   ├── README.md
        │   ├── base.py
        │   ├── navigation_tasks.py
        │   ├── shop_tasks.py
        │   ├── combat_tasks.py
        │   └── ...
        ├── processes/                 # Layer 7: Complete Features
        │   ├── README.md
        │   ├── base.py
        │   ├── daily_routine.py
        │   ├── push_main_story.py
        │   └── ...
        └── orchestrator/              # Layer 8: Pipeline
            ├── README.md
            ├── pipeline.py
            ├── executor.py
            ├── recovery.py
            └── plans/
```

---

## 5. Coding Standards

| Rule | Detail |
|---|---|
| File length | ~200 lines max. Split when approaching limit. |
| Comments | English only. Docstrings in English. |
| README.md | Required in every directory. Documents purpose, files, interfaces, usage. |
| Dependencies | Layer N imports only from Layers 0..(N-1). No circular imports. |
| Game isolation | Game A never imports from Game B. Shared code lives in Layers 1-3. |
| Type hints | All public functions fully typed. Use Protocol for interfaces. |
| Async | Tasks, ops, processes use async/await for non-blocking execution. |
| Testing | Each layer independently testable. Vision: pass test images. Ops: mock device. |
| No pixel brightness | Use template matching or OCR for state detection. Never np.mean() for decisions. |

---

## 6. Migration Path

Current code maps to new structure:

| Current file | New location | Notes |
|---|---|---|
| `core/session.py` | `core/device.py` | Rename, strip resource loading |
| `pages/definitions.py` | `knowledge/pages.py` | Pure data, remove logic |
| `pages/template_identifier.py` | `ops/perception/identify_page.py` | Uses vision/matcher |
| `nav/navigator.py` | `ops/navigate/goto_page.py` | Decompose into atomic ops |
| `tasks/atomic.py` | `ops/` (split across subdirs) | One file per op |
| `tasks/daily.py` | `tasks/` + `processes/daily_routine.py` | Split composable from final |
| `scripts/ch6_battle.py` | `ops/combat/` + `tasks/combat_tasks.py` + `processes/push_main_story.py` | Decompose into 3 layers |
| `scripts/snap.py` | `scripts/snap.py` (keep) | Debug tool, stays in scripts/ |
| `scripts/ch6_clear*.py` | Delete | Superseded by architecture |
| `scripts/explore*.py` | Delete or move to `scripts/debug/` | One-time exploration tools |

---

## 7. What Stays in scripts/

`scripts/` becomes a thin directory for entry points and debug tools only:

```
scripts/
├── run.py                 # Main entry: load plan → run pipeline
├── snap.py                # Debug: screenshot + click + crop tool
└── debug/                 # One-time exploration/testing scripts
```

All real logic lives in `src/`.
