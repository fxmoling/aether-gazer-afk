# Auto-Battle System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract reusable auto-battle module from duowei inline code, with YAML combat scripts and InBattleCheck-based state monitoring.

**Architecture:** Three files in `combat/` package: `script.py` (data model + YAML loader), `runner.py` (execution loop), `service.py` (monitor + combat orchestration). Two YAML scripts in `config/combat_scripts/`. Refactor `duowei_tasks.py` to use the new module.

**Tech Stack:** Python 3.11, asyncio, PyYAML (already in deps), dataclasses

---

### Task 1: YAML Script Files

**Files:**
- Create: `config/combat_scripts/default.yaml`
- Create: `config/combat_scripts/shikoudi.yaml`

- [ ] **Step 1: Create default.yaml**

```yaml
# config/combat_scripts/default.yaml
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

- [ ] **Step 2: Create shikoudi.yaml**

```yaml
# config/combat_scripts/shikoudi.yaml
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

- [ ] **Step 3: Commit**

```bash
git add config/combat_scripts/
git commit -m "feat: add default and shikoudi combat script YAML files"
```

---

### Task 2: CombatScript Data Model + Loader (`script.py`)

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/combat/__init__.py`
- Create: `src/anime_game_afk/games/aether_gazer/combat/script.py`
- Create: `tests/games/aether_gazer/combat/__init__.py`
- Create: `tests/games/aether_gazer/combat/test_script.py`

- [ ] **Step 1: Create combat package `__init__.py`**

```python
# src/anime_game_afk/games/aether_gazer/combat/__init__.py
"""Auto-battle system — YAML combat scripts + execution + monitoring."""

from anime_game_afk.games.aether_gazer.combat.script import (
    CombatScript,
    CombatStep,
    load_script,
    load_script_file,
)

__all__ = ["CombatScript", "CombatStep", "load_script", "load_script_file"]
```

- [ ] **Step 2: Write tests for script loading**

```python
# tests/games/aether_gazer/combat/__init__.py
```

```python
# tests/games/aether_gazer/combat/test_script.py
"""Tests for combat script data model and YAML loading."""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
import yaml

from anime_game_afk.games.aether_gazer.combat.script import (
    CombatScript,
    CombatStep,
    load_script,
    load_script_file,
)


@pytest.fixture
def tmp_yaml(tmp_path: Path):
    """Helper: write YAML content to a temp file and return the path."""
    def _write(content: str) -> Path:
        p = tmp_path / "test_script.yaml"
        p.write_text(dedent(content), encoding="utf-8")
        return p
    return _write


class TestCombatStep:
    def test_press_step(self):
        step = CombatStep(action="press", key="j", vk_code=0x4A, duration=0.0, interval=0.12)
        assert step.action == "press"
        assert step.vk_code == 0x4A
        assert step.interval == 0.12

    def test_hold_step(self):
        step = CombatStep(action="hold", key="u", vk_code=0x55, duration=1.5, interval=0.12)
        assert step.action == "hold"
        assert step.duration == 1.5

    def test_wait_step(self):
        step = CombatStep(action="wait", key=None, vk_code=None, duration=0.5, interval=0.0)
        assert step.action == "wait"
        assert step.duration == 0.5


class TestLoadScriptFile:
    def test_basic_press_script(self, tmp_yaml):
        path = tmp_yaml("""\
            name: test
            interval: 0.1
            steps:
              - press: j
              - press: u
        """)
        script = load_script_file(path)
        assert script.name == "test"
        assert len(script.steps) == 2
        assert script.steps[0].action == "press"
        assert script.steps[0].vk_code == 0x4A  # J
        assert script.steps[0].interval == 0.1
        assert script.steps[1].vk_code == 0x55  # U

    def test_hold_step(self, tmp_yaml):
        path = tmp_yaml("""\
            name: hold_test
            interval: 0.12
            steps:
              - hold: u
                duration: 1.5
              - press: j
        """)
        script = load_script_file(path)
        assert script.steps[0].action == "hold"
        assert script.steps[0].vk_code == 0x55
        assert script.steps[0].duration == 1.5
        assert script.steps[1].action == "press"

    def test_wait_step(self, tmp_yaml):
        path = tmp_yaml("""\
            name: wait_test
            steps:
              - press: j
              - wait: 0.5
              - press: j
        """)
        script = load_script_file(path)
        assert len(script.steps) == 3
        assert script.steps[1].action == "wait"
        assert script.steps[1].duration == 0.5
        assert script.steps[1].key is None
        assert script.steps[1].vk_code is None

    def test_per_step_interval_override(self, tmp_yaml):
        path = tmp_yaml("""\
            name: override_test
            interval: 0.12
            steps:
              - press: j
                interval: 0.5
              - press: u
        """)
        script = load_script_file(path)
        assert script.steps[0].interval == 0.5
        assert script.steps[1].interval == 0.12

    def test_default_interval(self, tmp_yaml):
        path = tmp_yaml("""\
            name: default_interval
            steps:
              - press: j
        """)
        script = load_script_file(path)
        assert script.steps[0].interval == 0.12  # module default

    def test_description_optional(self, tmp_yaml):
        path = tmp_yaml("""\
            name: no_desc
            steps:
              - press: j
        """)
        script = load_script_file(path)
        assert script.description == ""

    def test_numeric_key_as_string(self, tmp_yaml):
        path = tmp_yaml("""\
            name: numeric
            steps:
              - press: "1"
              - press: "2"
        """)
        script = load_script_file(path)
        assert script.steps[0].vk_code == 0x31  # 1
        assert script.steps[1].vk_code == 0x32  # 2

    def test_space_key(self, tmp_yaml):
        path = tmp_yaml("""\
            name: space
            steps:
              - press: space
        """)
        script = load_script_file(path)
        assert script.steps[0].vk_code == 0x20

    def test_empty_steps_raises(self, tmp_yaml):
        path = tmp_yaml("""\
            name: empty
            steps: []
        """)
        with pytest.raises(ValueError, match="steps"):
            load_script_file(path)

    def test_missing_steps_raises(self, tmp_yaml):
        path = tmp_yaml("""\
            name: no_steps
        """)
        with pytest.raises(ValueError, match="steps"):
            load_script_file(path)

    def test_invalid_key_raises(self, tmp_yaml):
        path = tmp_yaml("""\
            name: bad_key
            steps:
              - press: "F12"
        """)
        with pytest.raises(ValueError):
            load_script_file(path)

    def test_hold_without_duration_raises(self, tmp_yaml):
        path = tmp_yaml("""\
            name: bad_hold
            steps:
              - hold: u
        """)
        with pytest.raises(ValueError, match="duration"):
            load_script_file(path)

    def test_ambiguous_step_raises(self, tmp_yaml):
        path = tmp_yaml("""\
            name: ambiguous
            steps:
              - press: j
                hold: u
        """)
        with pytest.raises(ValueError, match="exactly one"):
            load_script_file(path)


class TestLoadScript:
    def test_load_default(self):
        """Load the real default.yaml from config/combat_scripts/."""
        script = load_script("default")
        assert script.name == "默认连招"
        assert len(script.steps) == 10
        # First step is J (attack)
        assert script.steps[0].vk_code == 0x4A

    def test_load_shikoudi(self):
        """Load the real shikoudi.yaml from config/combat_scripts/."""
        script = load_script("shikoudi")
        assert script.name == "诗寇蒂"
        assert len(script.steps) == 7
        # First step is I (skill 2)
        assert script.steps[0].vk_code == 0x49

    def test_load_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            load_script("nonexistent_script_xyz")
```

- [ ] **Step 3: Run tests — verify they fail**

Run: `python -m pytest tests/games/aether_gazer/combat/test_script.py -v --tb=short 2>&1 | head -30`
Expected: ImportError (module doesn't exist yet)

- [ ] **Step 4: Implement `script.py`**

```python
# src/anime_game_afk/games/aether_gazer/combat/script.py
"""Combat script data model and YAML loader.

A CombatScript is a sequence of CombatSteps loaded from a YAML file.
Three step types: press (tap key), hold (sustain key), wait (sleep).

Pure data — no device access, no side effects.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from anime_game_afk.games.aether_gazer.knowledge.keys import letter_to_vk

_DEFAULT_INTERVAL = 0.12
_STEP_ACTIONS = frozenset({"press", "hold", "wait"})

# Resolve config directory relative to project root.
# config/combat_scripts/ lives at the repo root, not inside src/.
_CONFIG_DIR = Path(__file__).resolve().parents[5] / "config" / "combat_scripts"


@dataclass(frozen=True)
class CombatStep:
    """Single action in a combat script."""

    action: Literal["press", "hold", "wait"]
    key: str | None  # Key name (None for wait)
    vk_code: int | None  # Resolved VK code (None for wait)
    duration: float  # Hold duration (hold) or sleep seconds (wait)
    interval: float  # Post-action wait in seconds


@dataclass(frozen=True)
class CombatScript:
    """Loaded and validated combat script."""

    name: str
    description: str
    steps: tuple[CombatStep, ...]


def load_script(name: str) -> CombatScript:
    """Load a named script from ``config/combat_scripts/{name}.yaml``."""
    path = _CONFIG_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Combat script not found: {path}")
    return load_script_file(path)


def load_script_file(path: Path) -> CombatScript:
    """Load and validate a combat script from an arbitrary YAML file."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    name = raw.get("name", path.stem)
    description = raw.get("description", "")
    default_interval = float(raw.get("interval", _DEFAULT_INTERVAL))

    raw_steps = raw.get("steps")
    if not raw_steps:
        raise ValueError(f"Combat script {name!r}: 'steps' must be a non-empty list")

    steps: list[CombatStep] = []
    for i, entry in enumerate(raw_steps):
        step = _parse_step(entry, default_interval, context=f"step {i}")
        steps.append(step)

    return CombatScript(name=name, description=description, steps=tuple(steps))


def _parse_step(entry: dict | float, default_interval: float, context: str) -> CombatStep:
    """Parse a single step entry from the YAML steps list."""
    # wait shorthand: `- wait: 0.5`
    if isinstance(entry, (int, float)):
        return CombatStep(
            action="wait", key=None, vk_code=None,
            duration=float(entry), interval=0.0,
        )

    # Determine which action keys are present
    found = _STEP_ACTIONS & entry.keys()
    if len(found) != 1:
        raise ValueError(
            f"{context}: step must have exactly one of 'press', 'hold', 'wait'; "
            f"found {found or 'none'}"
        )
    action = found.pop()
    interval = float(entry.get("interval", default_interval))

    if action == "wait":
        return CombatStep(
            action="wait", key=None, vk_code=None,
            duration=float(entry["wait"]), interval=0.0,
        )

    key_name = str(entry[action])
    vk_code = letter_to_vk(key_name)  # raises ValueError on bad key
    duration = 0.0
    if action == "hold":
        if "duration" not in entry:
            raise ValueError(f"{context}: 'hold' step requires 'duration'")
        duration = float(entry["duration"])
        if duration <= 0:
            raise ValueError(f"{context}: 'hold' duration must be > 0")

    return CombatStep(
        action=action, key=key_name, vk_code=vk_code,
        duration=duration, interval=interval,
    )
```

- [ ] **Step 5: Run tests — verify they pass**

Run: `python -m pytest tests/games/aether_gazer/combat/test_script.py -v --tb=short`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/anime_game_afk/games/aether_gazer/combat/__init__.py \
        src/anime_game_afk/games/aether_gazer/combat/script.py \
        tests/games/aether_gazer/combat/
git commit -m "feat: CombatScript data model and YAML loader"
```

---

### Task 3: CombatRunner (`runner.py`)

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/combat/runner.py`
- Create: `tests/games/aether_gazer/combat/test_runner.py`

- [ ] **Step 1: Write tests for execute_cycle and CombatRunner**

```python
# tests/games/aether_gazer/combat/test_runner.py
"""Tests for combat runner — execute_cycle and CombatRunner."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import numpy as np
import pytest

from anime_game_afk.games.aether_gazer.combat.runner import (
    CombatRunner,
    execute_cycle,
)
from anime_game_afk.games.aether_gazer.combat.script import CombatScript, CombatStep
from anime_game_afk.games.aether_gazer.ops.base import OpContext


@dataclass
class MockDevice:
    """Records key presses and holds for assertions."""
    pressed: list = field(default_factory=list)
    held: list = field(default_factory=list)

    def screenshot(self) -> np.ndarray:
        return np.zeros((720, 1280, 3), dtype=np.uint8)

    def click(self, fx: float, fy: float) -> None:
        pass

    def press_key(self, vk_code: int) -> None:
        self.pressed.append(vk_code)

    def hold_key(self, vk_code: int, duration_s: float) -> None:
        self.held.append((vk_code, duration_s))


def _make_script(steps: list[CombatStep], name: str = "test") -> CombatScript:
    return CombatScript(name=name, description="", steps=tuple(steps))


def _press(key: str, vk: int, interval: float = 0.12) -> CombatStep:
    return CombatStep(action="press", key=key, vk_code=vk, duration=0.0, interval=interval)


def _hold(key: str, vk: int, duration: float, interval: float = 0.12) -> CombatStep:
    return CombatStep(action="hold", key=key, vk_code=vk, duration=duration, interval=interval)


def _wait(seconds: float) -> CombatStep:
    return CombatStep(action="wait", key=None, vk_code=None, duration=seconds, interval=0.0)


class TestExecuteCycle:
    def test_press_keys_in_order(self):
        dev = MockDevice()
        ctx = OpContext(device=dev)
        script = _make_script([
            _press("j", 0x4A),
            _press("u", 0x55),
            _press("i", 0x49),
        ])
        asyncio.run(execute_cycle(ctx, script))
        assert dev.pressed == [0x4A, 0x55, 0x49]

    def test_hold_key(self):
        dev = MockDevice()
        ctx = OpContext(device=dev)
        script = _make_script([
            _hold("u", 0x55, duration=1.5),
            _press("j", 0x4A),
        ])
        asyncio.run(execute_cycle(ctx, script))
        assert dev.held == [(0x55, 1.5)]
        assert dev.pressed == [0x4A]

    def test_wait_step_no_keys(self):
        dev = MockDevice()
        ctx = OpContext(device=dev)
        script = _make_script([
            _press("j", 0x4A),
            _wait(0.5),
            _press("u", 0x55),
        ])
        asyncio.run(execute_cycle(ctx, script))
        assert dev.pressed == [0x4A, 0x55]
        assert dev.held == []

    def test_empty_script_noop(self):
        dev = MockDevice()
        ctx = OpContext(device=dev)
        script = CombatScript(name="empty", description="", steps=())
        asyncio.run(execute_cycle(ctx, script))
        assert dev.pressed == []


class TestCombatRunner:
    def test_runner_stops_when_active_cleared(self):
        dev = MockDevice()
        ctx = OpContext(device=dev)
        script = _make_script([_press("j", 0x4A)])
        runner = CombatRunner(script)
        runner.active = True

        async def _stop_after_short_delay():
            # Let the runner execute a few cycles then stop
            for _ in range(5):
                await asyncio.sleep(0)
            runner.active = False

        async def _run():
            await asyncio.gather(runner.run(ctx), _stop_after_short_delay())

        asyncio.run(_run())
        # Runner should have pressed some keys then stopped
        assert len(dev.pressed) > 0
        assert all(vk == 0x4A for vk in dev.pressed)

    def test_runner_idles_when_not_active(self):
        dev = MockDevice()
        ctx = OpContext(device=dev)
        script = _make_script([_press("j", 0x4A)])
        runner = CombatRunner(script)
        runner.active = False

        async def _stop_soon():
            for _ in range(5):
                await asyncio.sleep(0)
            runner.stop()

        async def _run():
            await asyncio.gather(runner.run(ctx), _stop_soon())

        asyncio.run(_run())
        assert dev.pressed == []  # Never active, no keys pressed
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `python -m pytest tests/games/aether_gazer/combat/test_runner.py -v --tb=short 2>&1 | head -20`
Expected: ImportError (module doesn't exist yet)

- [ ] **Step 3: Implement `runner.py`**

```python
# src/anime_game_afk/games/aether_gazer/combat/runner.py
"""Combat script execution.

``execute_cycle`` runs one pass of all steps in a script.
``CombatRunner`` loops the cycle while its ``active`` flag is True.
"""
from __future__ import annotations

import asyncio

from loguru import logger

from anime_game_afk.games.aether_gazer.combat.script import CombatScript
from anime_game_afk.games.aether_gazer.knowledge.keys import key_name
from anime_game_afk.games.aether_gazer.ops.base import OpContext


async def execute_cycle(ctx: OpContext, script: CombatScript) -> None:
    """Execute one complete cycle of *script* (all steps once)."""
    for step in script.steps:
        if step.action == "press":
            ctx.device.press_key(step.vk_code)
            await asyncio.sleep(step.interval)
        elif step.action == "hold":
            ctx.device.hold_key(step.vk_code, step.duration)
            await asyncio.sleep(step.interval)
        elif step.action == "wait":
            await asyncio.sleep(step.duration)


class CombatRunner:
    """Loops ``execute_cycle`` while ``active`` is True.

    Set ``active = True`` to start pressing keys.
    Set ``active = False`` to pause (runner idles until active again).
    Call ``stop()`` to exit the run loop entirely.
    """

    def __init__(self, script: CombatScript) -> None:
        self._script = script
        self.active: bool = False
        self._running: bool = False

    def stop(self) -> None:
        """Signal the run loop to exit."""
        self._running = False
        self.active = False

    async def run(self, ctx: OpContext) -> None:
        """Loop script steps while active. Exits on ``stop()``."""
        self._running = True
        logger.info("CombatRunner started: script={!r}", self._script.name)
        try:
            while self._running:
                if self.active:
                    await execute_cycle(ctx, self._script)
                else:
                    await asyncio.sleep(0.5)
        finally:
            logger.info("CombatRunner stopped")
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `python -m pytest tests/games/aether_gazer/combat/test_runner.py -v --tb=short`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/anime_game_afk/games/aether_gazer/combat/runner.py \
        tests/games/aether_gazer/combat/test_runner.py
git commit -m "feat: CombatRunner — execute_cycle and looping runner"
```

---

### Task 4: AutoBattleService (`service.py`)

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/combat/service.py`
- Create: `tests/games/aether_gazer/combat/test_service.py`

- [ ] **Step 1: Write tests for AutoBattleService**

```python
# tests/games/aether_gazer/combat/test_service.py
"""Tests for AutoBattleService — monitor + combat orchestration."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest

from anime_game_afk.games.aether_gazer.combat.script import CombatScript, CombatStep
from anime_game_afk.games.aether_gazer.combat.service import AutoBattleService
from anime_game_afk.games.aether_gazer.ops.base import OpContext


@dataclass
class MockDevice:
    pressed: list = field(default_factory=list)
    held: list = field(default_factory=list)

    def screenshot(self) -> np.ndarray:
        return np.zeros((720, 1280, 3), dtype=np.uint8)

    def click(self, fx: float, fy: float) -> None:
        pass

    def press_key(self, vk_code: int) -> None:
        self.pressed.append(vk_code)

    def hold_key(self, vk_code: int, duration_s: float) -> None:
        self.held.append((vk_code, duration_s))


def _simple_script() -> CombatScript:
    return CombatScript(
        name="test",
        description="",
        steps=(
            CombatStep(action="press", key="j", vk_code=0x4A, duration=0.0, interval=0.12),
        ),
    )


class TestAutoBattleServiceToggle:
    def test_start_and_stop(self):
        """Service starts, fights when in battle, stops on stop()."""
        dev = MockDevice()
        ctx = OpContext(device=dev)
        service = AutoBattleService(_simple_script(), check_interval=0.01)

        call_count = 0

        async def mock_evaluate(self_check, ctx_arg):
            nonlocal call_count
            call_count += 1
            from anime_game_afk.games.aether_gazer.checks.base import CheckResult
            # First 3 calls: in battle. Then: not in battle.
            return CheckResult(passed=(call_count <= 3))

        async def _stop_later():
            for _ in range(20):
                await asyncio.sleep(0)
            service.stop()

        with patch(
            "anime_game_afk.games.aether_gazer.combat.service.InBattleCheck.evaluate",
            mock_evaluate,
        ):
            asyncio.run(asyncio.wait_for(
                asyncio.gather(service.start(ctx), _stop_later()),
                timeout=2.0,
            ))

        assert len(dev.pressed) > 0  # Keys were pressed during battle
        assert not service.in_battle


class TestAutoBattleServiceRunOnce:
    def test_run_until_battle_ends(self):
        """run_until_battle_ends returns after battle starts then stops."""
        dev = MockDevice()
        ctx = OpContext(device=dev)
        service = AutoBattleService(_simple_script(), check_interval=0.01)

        call_count = 0

        async def mock_evaluate(self_check, ctx_arg):
            nonlocal call_count
            call_count += 1
            from anime_game_afk.games.aether_gazer.checks.base import CheckResult
            # Calls 1-2: not in battle (waiting). Calls 3-5: in battle. Then: end.
            return CheckResult(passed=(3 <= call_count <= 5))

        with patch(
            "anime_game_afk.games.aether_gazer.combat.service.InBattleCheck.evaluate",
            mock_evaluate,
        ):
            asyncio.run(asyncio.wait_for(
                service.run_until_battle_ends(ctx),
                timeout=2.0,
            ))

        assert len(dev.pressed) > 0  # Keys were pressed
        assert not service.in_battle  # Battle ended
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `python -m pytest tests/games/aether_gazer/combat/test_service.py -v --tb=short 2>&1 | head -20`
Expected: ImportError (module doesn't exist yet)

- [ ] **Step 3: Implement `service.py`**

```python
# src/anime_game_afk/games/aether_gazer/combat/service.py
"""Auto-battle service — monitor battle state + execute combat script.

Two usage patterns:

Pattern A — Toggle (user-driven)::

    service = AutoBattleService(script)
    task = asyncio.create_task(service.start(ctx))
    ...
    service.stop()
    await task

Pattern B — Run-once (task-driven)::

    service = AutoBattleService(script)
    await service.run_until_battle_ends(ctx)
"""
from __future__ import annotations

import asyncio

from loguru import logger

from anime_game_afk.games.aether_gazer.checks.battle import InBattleCheck
from anime_game_afk.games.aether_gazer.combat.runner import CombatRunner, execute_cycle
from anime_game_afk.games.aether_gazer.combat.script import CombatScript
from anime_game_afk.games.aether_gazer.ops.base import OpContext


class AutoBattleService:
    """Toggle-based auto-battle: monitor battle state + run combat script."""

    def __init__(self, script: CombatScript, check_interval: float = 2.0) -> None:
        self._script = script
        self._check_interval = check_interval
        self._runner = CombatRunner(script)
        self._enabled = False

    # ── Public API ──

    async def start(self, ctx: OpContext) -> None:
        """Start monitor + combat loops. Blocks until ``stop()`` called."""
        self._enabled = True
        logger.info(
            "AutoBattle started: script={!r} check_interval={:.1f}s",
            self._script.name, self._check_interval,
        )
        await asyncio.gather(
            self._monitor_loop(ctx),
            self._combat_loop(ctx),
        )

    def stop(self) -> None:
        """Signal both loops to exit."""
        self._enabled = False
        self._runner.stop()
        logger.info("AutoBattle stopped")

    async def run_until_battle_ends(self, ctx: OpContext) -> None:
        """Start, wait for battle to begin and end, then auto-stop.

        For task-driven usage: call this after entering a battle screen.
        It fights until InBattleCheck goes False, then returns.
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
        """Current battle state."""
        return self._runner.active

    # ── Internal loops ──

    async def _monitor_loop(self, ctx: OpContext) -> None:
        check = InBattleCheck()
        while self._enabled:
            result = await check.evaluate(ctx)
            was_active = self._runner.active
            self._runner.active = result.passed
            if result.passed and not was_active:
                logger.info("AutoBattle: battle detected — fighting")
            elif not result.passed and was_active:
                logger.info("AutoBattle: battle ended — idling")
            await asyncio.sleep(self._check_interval)

    async def _combat_loop(self, ctx: OpContext) -> None:
        while self._enabled:
            if self._runner.active:
                await execute_cycle(ctx, self._script)
            else:
                await asyncio.sleep(0.5)
```

- [ ] **Step 4: Update `__init__.py` to re-export service**

Add to `src/anime_game_afk/games/aether_gazer/combat/__init__.py`:

```python
"""Auto-battle system — YAML combat scripts + execution + monitoring."""

from anime_game_afk.games.aether_gazer.combat.runner import (
    CombatRunner,
    execute_cycle,
)
from anime_game_afk.games.aether_gazer.combat.script import (
    CombatScript,
    CombatStep,
    load_script,
    load_script_file,
)
from anime_game_afk.games.aether_gazer.combat.service import AutoBattleService

__all__ = [
    "AutoBattleService",
    "CombatRunner",
    "CombatScript",
    "CombatStep",
    "execute_cycle",
    "load_script",
    "load_script_file",
]
```

- [ ] **Step 5: Run tests — verify they pass**

Run: `python -m pytest tests/games/aether_gazer/combat/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/anime_game_afk/games/aether_gazer/combat/ \
        tests/games/aether_gazer/combat/test_service.py
git commit -m "feat: AutoBattleService with toggle and run-once patterns"
```

---

### Task 5: Refactor duowei_tasks.py

**Files:**
- Modify: `src/anime_game_afk/games/aether_gazer/tasks/duowei_tasks.py`

- [ ] **Step 1: Replace `_build_attack_keys` and `_fight_battle` with combat module**

In `duowei_tasks.py`:

**Remove** these imports (lines 19-22):
```python
from anime_game_afk.games.aether_gazer.knowledge.keys import (
    VK_ENTER, VK_ESCAPE, VK_J, VK_W, VK_H, VK_S,
    VK_U, VK_I, VK_O, VK_R, VK_1, VK_2,
    letter_to_vk,
)
```

**Replace with:**
```python
from anime_game_afk.games.aether_gazer.knowledge.keys import (
    VK_ENTER, VK_ESCAPE, VK_J, VK_W, VK_H, VK_S,
)
```

**Add** new import:
```python
from anime_game_afk.games.aether_gazer.combat.service import AutoBattleService
from anime_game_afk.games.aether_gazer.combat.script import load_script
```

**Delete** the entire `_build_attack_keys()` function (lines 33-51).

**Delete** the `import time` at line 17 (only used by the old `_fight_battle`; check if used elsewhere first — if `time.sleep` is used in other methods, keep it).

**Remove** from `__init__`:
```python
self._attack_keys = _build_attack_keys(keybinds)
```

**Remove** `keybinds` parameter from `__init__` if it's only used for attack keys.

**Replace** `_fight_battle` method (lines 517-554) with:

```python
    async def _fight_battle(self, ctx: TaskContext) -> str:
        """Execute combat script until battle ends."""
        ctx.logger.info("[duowei] _fight_battle starting")
        await SleepOp(3.0).run(ctx)  # Wait for battle to fully load

        script = load_script("default")
        service = AutoBattleService(script, check_interval=2.0)
        await service.run_until_battle_ends(ctx)

        ctx.logger.info("[duowei] Battle ended")
        return "won"
```

- [ ] **Step 2: Verify existing imports and references are clean**

Check that no other method in `DuoweiCombat` references `self._attack_keys`, `_build_attack_keys`, `VK_U`, `VK_I`, `VK_O`, `VK_R`, `VK_1`, `VK_2`, or `letter_to_vk`. If they do, keep those imports; if not, remove them.

Check if `import time` is still needed for other methods (e.g. `time.sleep` in portal walking). If still needed, keep it.

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/ -v --tb=short 2>&1 | tail -30`
Expected: All tests PASS (no regressions)

- [ ] **Step 4: Commit**

```bash
git add src/anime_game_afk/games/aether_gazer/tasks/duowei_tasks.py
git commit -m "refactor: duowei _fight_battle uses AutoBattleService"
```

---

### Task 6: Full Test Suite + Cleanup

**Files:**
- All test files from previous tasks
- Possibly cleanup stale test files

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 2: Check for stale test references to deleted code**

The old `tests/games/aether_gazer/ops/combat/test_combat.py` may reference deleted code (ops/combat/ was removed in the dead code cleanup). If it imports things that don't exist, fix or remove it.

Run: `python -m pytest tests/games/aether_gazer/ops/combat/ -v --tb=short 2>&1 | head -20`
If it errors, check the file and decide: fix or delete.

- [ ] **Step 3: Verify module imports cleanly**

Run: `python -c "from anime_game_afk.games.aether_gazer.combat import AutoBattleService, load_script; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Final commit if any cleanup was needed**

```bash
git add -A
git commit -m "chore: test suite cleanup after auto-battle module"
```
