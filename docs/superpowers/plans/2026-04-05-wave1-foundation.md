# Wave 1: Foundation (Layers 1-3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement task-by-task.

**Goal:** Establish core infrastructure: device adapter, vision toolkit, runtime services.

**Architecture:** Bottom 3 layers are game-agnostic. Device wraps MaaFw, Vision provides cv2 tools, Runtime provides logging/config/state. Existing `session.py` is refactored into `device.py` with cleaner interface.

**Tech Stack:** Python 3.11, maafw, opencv-python, loguru, numpy

---

## Task 1: Core types and errors

**Files:**
- Create: `src/anime_game_afk/core/types.py`
- Modify: `src/anime_game_afk/core/errors.py`
- Create: `src/anime_game_afk/core/README.md`
- Test: `tests/core/test_types.py`

**Purpose:** Shared type definitions used across all layers. Clean up error hierarchy.

- [ ] Step 1: Create `core/types.py` with Point, Rect, Resolution dataclasses
- [ ] Step 2: Write test for types (construction, equality, unpacking)
- [ ] Step 3: Update `core/errors.py` — English docstrings, add DeviceError base
- [ ] Step 4: Write `core/README.md` documenting directory purpose and each file
- [ ] Step 5: Run tests, commit

**core/types.py content:**
```python
"""Shared type definitions for the automation framework."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Point:
    x: int
    y: int

@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.h

    def contains(self, p: Point) -> bool:
        return self.x <= p.x < self.x2 and self.y <= p.y < self.y2

@dataclass(frozen=True)
class Resolution:
    width: int
    height: int
```

---

## Task 2: Device adapter

**Files:**
- Create: `src/anime_game_afk/core/device.py`
- Modify: `src/anime_game_afk/config/models.py` — rename GameConfig → DeviceConfig
- Test: `tests/core/test_device.py` (unit tests with mocked MaaFw)

**Purpose:** Refactor `session.py` into `device.py`. Strips out resource loading, keeps only device I/O.

- [ ] Step 1: Create `core/device.py` — DeviceAdapter class with connect/disconnect/screenshot/click/press_key/hold_key/swipe
- [ ] Step 2: Write unit tests with a MockController (no real MaaFw needed)
- [ ] Step 3: Update `config/models.py` — English comments, cleaner DeviceConfig
- [ ] Step 4: Verify existing `scripts/snap.py` still works by importing from new location
- [ ] Step 5: Run tests, commit

**Key interface:**
```python
class DeviceAdapter:
    def __init__(self, config: DeviceConfig) -> None: ...
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def screenshot(self) -> np.ndarray: ...       # design resolution
    def screenshot_raw(self) -> np.ndarray: ...    # actual resolution
    def click(self, x: int, y: int) -> None: ...
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 500) -> None: ...
    def press_key(self, vk_code: int) -> None: ...
    def hold_key(self, vk_code: int, duration_s: float) -> None: ...
    @property
    def connected(self) -> bool: ...
    @property
    def resolution(self) -> Resolution: ...
    @property
    def design_resolution(self) -> Resolution: ...
```

**Migration note:** Keep `session.py` temporarily with a deprecation wrapper that delegates to DeviceAdapter, so existing scripts don't break immediately.

---

## Task 3: Vision types

**Files:**
- Create: `src/anime_game_afk/vision/README.md`
- Create: `src/anime_game_afk/vision/__init__.py`
- Create: `src/anime_game_afk/vision/types.py`
- Test: `tests/vision/test_types.py`

**Purpose:** Result types for all vision operations.

- [ ] Step 1: Create `vision/types.py` with MatchResult, TextResult
- [ ] Step 2: Write tests
- [ ] Step 3: Write README.md
- [ ] Step 4: Commit

```python
@dataclass
class MatchResult:
    score: float
    x: int
    y: int
    w: int
    h: int
    matched: bool  # score >= threshold

@dataclass
class TextResult:
    text: str
    confidence: float
    region: Rect
```

---

## Task 4: Vision matcher

**Files:**
- Create: `src/anime_game_afk/vision/matcher.py`
- Test: `tests/vision/test_matcher.py`

**Purpose:** Template matching wrapper around cv2.matchTemplate. Pure functions.

- [ ] Step 1: Create test images (solid color + small pattern) as test fixtures
- [ ] Step 2: Write failing tests for match_template, match_best, match_all
- [ ] Step 3: Implement `matcher.py` — three functions, each <30 lines
- [ ] Step 4: Run tests, verify pass
- [ ] Step 5: Commit

**matcher.py core:**
```python
def match_template(
    image: np.ndarray,
    template: np.ndarray,
    region: Rect | None = None,
    method: int = cv2.TM_CCOEFF_NORMED,
    threshold: float = 0.7,
) -> MatchResult: ...

def match_best(
    image: np.ndarray,
    templates: list[np.ndarray],
    region: Rect | None = None,
    threshold: float = 0.7,
) -> MatchResult: ...

def match_all(
    image: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.7,
    region: Rect | None = None,
) -> list[MatchResult]: ...
```

---

## Task 5: Vision geometry and color

**Files:**
- Create: `src/anime_game_afk/vision/geometry.py`
- Create: `src/anime_game_afk/vision/color.py`
- Test: `tests/vision/test_geometry.py`
- Test: `tests/vision/test_color.py`

**Purpose:** Image crop/resize utilities and HSV color detection.

- [ ] Step 1: Write tests for crop(image, rect) and resize(image, width, height)
- [ ] Step 2: Implement geometry.py (~40 lines)
- [ ] Step 3: Write tests for find_color_regions(image, hsv_low, hsv_high)
- [ ] Step 4: Implement color.py (~50 lines)
- [ ] Step 5: Commit

---

## Task 6: Vision OCR stub

**Files:**
- Create: `src/anime_game_afk/vision/ocr.py`
- Test: `tests/vision/test_ocr.py`

**Purpose:** OCR interface. Initially delegates to template matching for known text. Designed so real OCR can be swapped in later.

- [ ] Step 1: Define interface: `recognize_text(image, region, templates) → list[TextResult]`
- [ ] Step 2: Implement using match_template internally
- [ ] Step 3: Write test with a pre-cropped text template
- [ ] Step 4: Commit

---

## Task 7: Runtime logger

**Files:**
- Create: `src/anime_game_afk/runtime/README.md`
- Create: `src/anime_game_afk/runtime/__init__.py`
- Create: `src/anime_game_afk/runtime/logger.py`
- Test: `tests/runtime/test_logger.py`

**Purpose:** Structured logging wrapping loguru. Adds context tags (game, task, step).

- [ ] Step 1: Write `logger.py` — get_logger(name), with_context(game=, task=, step=)
- [ ] Step 2: Write test: logger outputs to string sink, verify context appears
- [ ] Step 3: Write README.md for runtime/
- [ ] Step 4: Commit

```python
def get_logger(name: str) -> Logger:
    """Get a structured logger with the given name."""
    ...

class Logger:
    def info(self, msg: str, **ctx: Any) -> None: ...
    def debug(self, msg: str, **ctx: Any) -> None: ...
    def warning(self, msg: str, **ctx: Any) -> None: ...
    def error(self, msg: str, **ctx: Any) -> None: ...
    def with_context(self, **ctx: Any) -> Logger: ...
```

---

## Task 8: Runtime config

**Files:**
- Create: `src/anime_game_afk/runtime/config.py`
- Test: `tests/runtime/test_config.py`

**Purpose:** Configuration loading from YAML/dict. Typed access with defaults.

- [ ] Step 1: Write `config.py` — ConfigStore class, load from dict or YAML file
- [ ] Step 2: Write tests: load, get with default, nested access
- [ ] Step 3: Commit

---

## Task 9: Runtime state and clock

**Files:**
- Create: `src/anime_game_afk/runtime/state.py`
- Create: `src/anime_game_afk/runtime/clock.py`
- Test: `tests/runtime/test_state.py`
- Test: `tests/runtime/test_clock.py`

**Purpose:** Persistent JSON state store + time utilities (cooldown, timer).

- [ ] Step 1: Write `state.py` — StateStore with save/load/clear, backed by JSON file
- [ ] Step 2: Write tests: save, load, persistence across instances
- [ ] Step 3: Write `clock.py` — Cooldown(duration), Timer(name) classes
- [ ] Step 4: Write tests: cooldown ready/reset, timer start/stop/elapsed
- [ ] Step 5: Commit

---

## Task 10: Runtime events and errors

**Files:**
- Create: `src/anime_game_afk/runtime/events.py`
- Create: `src/anime_game_afk/runtime/errors.py`
- Test: `tests/runtime/test_events.py`

**Purpose:** Infrastructure event bus (device_disconnected, window_lost, etc.) and recovery strategy framework.

- [ ] Step 1: Write `events.py` — EventBus with emit/on/off, infra events only
- [ ] Step 2: Write tests: register handler, emit event, handler called
- [ ] Step 3: Write `errors.py` — RecoveryStrategy base, RetryStrategy, FallbackStrategy
- [ ] Step 4: Write tests: retry strategy exhaustion, fallback chain
- [ ] Step 5: Commit

---

## Task 11: Integration verification

- [ ] Step 1: Verify all tests pass: `pytest tests/ -v`
- [ ] Step 2: Verify `scripts/snap.py` still works with new device adapter
- [ ] Step 3: Update `src/anime_game_afk/README.md` with new structure overview
- [ ] Step 4: Final commit for Wave 1
