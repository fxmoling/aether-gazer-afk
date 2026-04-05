# Wave 4: Orchestrator & Cleanup (Layer 8 + Migration)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement task-by-task.

**Goal:** Build the top-level orchestrator/pipeline (Layer 8) that loads a user YAML plan, executes enabled processes sequentially with timing/logging, and handles infrastructure-level recovery. Then clean up scripts/, remove superseded code, create the main entry point, and finalize migration from old directory structure.

**Architecture:** Layer 8 sits at the top. It imports Process from Layer 7, tasks from Layer 6, runtime services from Layer 3, and core types from Layer 1. The pipeline loads a YAML plan file, filters enabled processes, and delegates execution to the executor. Recovery handles only infrastructure failures (device disconnect, window lost, game crash). Game-level failures (battle failed, stamina empty) are handled within processes themselves.

**Tech Stack:** Python 3.11, maafw, pyyaml, loguru, asyncio

**Dependency assumption:** Waves 1-3 have created the foundational layers. This plan references types and modules from:
- `src/anime_game_afk/core/device.py` (Layer 1 — DeviceAdapter)
- `src/anime_game_afk/core/types.py` (Layer 1 — Point, Rect, Resolution)
- `src/anime_game_afk/core/errors.py` (Layer 1 — DeviceError, InfrastructureError)
- `src/anime_game_afk/runtime/logger.py` (Layer 3 — get_logger)
- `src/anime_game_afk/runtime/config.py` (Layer 3 — ConfigStore)
- `src/anime_game_afk/runtime/state.py` (Layer 3 — StateStore)
- `src/anime_game_afk/runtime/clock.py` (Layer 3 — Timer)
- `src/anime_game_afk/runtime/errors.py` (Layer 3 — RecoveryStrategy)
- `src/anime_game_afk/games/aether_gazer/processes/base.py` (Layer 7 — Process, ProcessResult, ProcessContext)

---

## Task 1: Orchestrator types and plan loader

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/orchestrator/__init__.py`
- Create: `src/anime_game_afk/games/aether_gazer/orchestrator/types.py`
- Create: `src/anime_game_afk/games/aether_gazer/orchestrator/README.md`
- Test: `tests/games/aether_gazer/orchestrator/test_types.py`

**Purpose:** Define orchestrator data types — ProcessDef (one entry in a plan), PlanConfig (the full plan), and PipelineResult (execution summary). Implement YAML plan loading and validation.

- [ ] Step 1: Create `orchestrator/__init__.py` with public exports
- [ ] Step 2: Create `orchestrator/types.py` with ProcessDef, PlanConfig, PipelineResult, and load_plan()
- [ ] Step 3: Write tests for types construction, load_plan from dict, load_plan from YAML file
- [ ] Step 4: Write `orchestrator/README.md` documenting the directory purpose and each file
- [ ] Step 5: Run tests, commit

**orchestrator/__init__.py content:**
```python
"""Layer 8: Orchestrator / Pipeline.

Executes a user-configured selection of processes.
Loads YAML plans, runs processes sequentially, handles infrastructure recovery.

Dependency rule: imports from Layers 0-7 only.
"""

from anime_game_afk.games.aether_gazer.orchestrator.types import (
    PipelineResult,
    PlanConfig,
    ProcessDef,
    load_plan,
)

__all__ = [
    "PlanConfig",
    "PipelineResult",
    "ProcessDef",
    "load_plan",
]
```

**orchestrator/types.py content:**
```python
"""Orchestrator data types and plan loading."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from anime_game_afk.runtime.logger import get_logger

logger = get_logger("orchestrator.types")


@dataclass
class ProcessDef:
    """One process entry in a user plan.

    Attributes:
        name: Process identifier matching a registered process class.
        enabled: Whether this process should run. Defaults to True.
        config: Process-specific configuration passed to ProcessContext.
    """
    name: str
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanConfig:
    """Complete user plan loaded from YAML.

    Attributes:
        game: Game identifier (e.g. "aether_gazer").
        processes: Ordered list of process definitions.
    """
    game: str
    processes: list[ProcessDef] = field(default_factory=list)

    @property
    def enabled_processes(self) -> list[ProcessDef]:
        """Return only processes with enabled=True, preserving order."""
        return [p for p in self.processes if p.enabled]


@dataclass
class PipelineResult:
    """Summary of a full pipeline execution.

    Attributes:
        total: Number of processes attempted.
        succeeded: Number that completed successfully.
        failed: Number that failed.
        skipped: Number skipped (disabled in plan).
        aborted: True if pipeline stopped early due to unrecoverable error.
        details: Per-process result summaries.
        elapsed_s: Total wall-clock time in seconds.
    """
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    aborted: bool = False
    details: list[dict[str, Any]] = field(default_factory=list)
    elapsed_s: float = 0.0

    @property
    def success_rate(self) -> float:
        """Fraction of attempted processes that succeeded."""
        if self.total == 0:
            return 0.0
        return self.succeeded / self.total


def _parse_process_def(raw: dict[str, Any]) -> ProcessDef:
    """Parse a single process definition from a YAML dict.

    Args:
        raw: Dict with keys 'name' (required), 'enabled' (optional),
             'config' (optional).

    Returns:
        A validated ProcessDef.

    Raises:
        ValueError: If 'name' key is missing.
    """
    if "name" not in raw:
        raise ValueError(f"Process definition missing 'name': {raw}")

    return ProcessDef(
        name=raw["name"],
        enabled=raw.get("enabled", True),
        config=raw.get("config", {}),
    )


def load_plan(source: str | Path | dict[str, Any]) -> PlanConfig:
    """Load a pipeline plan from a YAML file path or a pre-parsed dict.

    Args:
        source: Either a file path (str/Path) to a YAML file,
                or a dict already parsed from YAML.

    Returns:
        A validated PlanConfig.

    Raises:
        FileNotFoundError: If source is a path and file does not exist.
        ValueError: If plan structure is invalid.
    """
    if isinstance(source, dict):
        data = source
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Plan file not found: {path}")
        logger.info("Loading plan from {path}", path=str(path))
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Plan must be a YAML mapping, got {type(data).__name__}")

    game = data.get("game")
    if not game:
        raise ValueError("Plan missing required 'game' field")

    raw_processes = data.get("processes", [])
    if not isinstance(raw_processes, list):
        raise ValueError(f"'processes' must be a list, got {type(raw_processes).__name__}")

    processes = [_parse_process_def(p) for p in raw_processes]
    logger.info(
        "Plan loaded: game={game}, {total} processes ({enabled} enabled)",
        game=game,
        total=len(processes),
        enabled=sum(1 for p in processes if p.enabled),
    )

    return PlanConfig(game=game, processes=processes)
```

**tests/games/aether_gazer/orchestrator/test_types.py content:**
```python
"""Tests for orchestrator types and plan loading."""
import tempfile
from pathlib import Path

import pytest
import yaml

from anime_game_afk.games.aether_gazer.orchestrator.types import (
    PipelineResult,
    PlanConfig,
    ProcessDef,
    load_plan,
)


class TestProcessDef:
    def test_defaults(self) -> None:
        pd = ProcessDef(name="daily_routine")
        assert pd.name == "daily_routine"
        assert pd.enabled is True
        assert pd.config == {}

    def test_with_config(self) -> None:
        pd = ProcessDef(name="farm", enabled=False, config={"max_runs": 6})
        assert pd.enabled is False
        assert pd.config["max_runs"] == 6


class TestPlanConfig:
    def test_enabled_processes_filters(self) -> None:
        plan = PlanConfig(
            game="aether_gazer",
            processes=[
                ProcessDef(name="a", enabled=True),
                ProcessDef(name="b", enabled=False),
                ProcessDef(name="c", enabled=True),
            ],
        )
        enabled = plan.enabled_processes
        assert len(enabled) == 2
        assert [p.name for p in enabled] == ["a", "c"]

    def test_empty_processes(self) -> None:
        plan = PlanConfig(game="aether_gazer")
        assert plan.enabled_processes == []


class TestPipelineResult:
    def test_success_rate(self) -> None:
        result = PipelineResult(total=4, succeeded=3, failed=1)
        assert result.success_rate == 0.75

    def test_success_rate_zero(self) -> None:
        result = PipelineResult()
        assert result.success_rate == 0.0


class TestLoadPlan:
    def test_load_from_dict(self) -> None:
        data = {
            "game": "aether_gazer",
            "processes": [
                {"name": "daily_routine", "enabled": True},
                {"name": "push_main_story", "config": {"max_stages": 20}},
            ],
        }
        plan = load_plan(data)
        assert plan.game == "aether_gazer"
        assert len(plan.processes) == 2
        assert plan.processes[1].config["max_stages"] == 20

    def test_load_from_yaml_file(self, tmp_path: Path) -> None:
        plan_data = {
            "game": "aether_gazer",
            "processes": [
                {"name": "daily_routine", "enabled": True},
            ],
        }
        plan_file = tmp_path / "test_plan.yaml"
        plan_file.write_text(yaml.dump(plan_data), encoding="utf-8")

        plan = load_plan(plan_file)
        assert plan.game == "aether_gazer"
        assert len(plan.processes) == 1

    def test_missing_game_raises(self) -> None:
        with pytest.raises(ValueError, match="missing required 'game'"):
            load_plan({"processes": []})

    def test_missing_name_raises(self) -> None:
        with pytest.raises(ValueError, match="missing 'name'"):
            load_plan({"game": "x", "processes": [{"enabled": True}]})

    def test_file_not_found_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_plan("/nonexistent/plan.yaml")

    def test_disabled_default_true(self) -> None:
        plan = load_plan({
            "game": "aether_gazer",
            "processes": [{"name": "test"}],
        })
        assert plan.processes[0].enabled is True
```

**orchestrator/README.md content:**
```markdown
# Orchestrator (Layer 8)

Top-level pipeline that executes a user-configured selection of game processes.

## Files

| File | Purpose |
|---|---|
| `types.py` | Data types: ProcessDef, PlanConfig, PipelineResult, load_plan() |
| `executor.py` | Run individual processes with logging, timing, error handling |
| `recovery.py` | Cross-process infrastructure recovery strategies |
| `pipeline.py` | Main Pipeline class: load plan → build process list → execute |
| `plans/default.yaml` | Default plan template for new users |

## Architecture

- **Pipeline** loads a YAML plan, filters enabled processes, delegates to Executor
- **Executor** runs each process with timing, logs results, catches errors
- **Recovery** handles ONLY infrastructure failures: device_disconnected, window_lost,
  screenshot_timeout, game_crash, session_expired
- Game-level failures (battle failed, stamina empty) are handled within processes (Layer 7)

## Dependency Rule

Layer 8 imports from Layers 0-7. No other layer imports from Layer 8.
```

---

## Task 2: Infrastructure recovery strategies

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/orchestrator/recovery.py`
- Test: `tests/games/aether_gazer/orchestrator/test_recovery.py`

**Purpose:** Cross-process recovery for infrastructure failures that no single process can handle. Each strategy attempts to restore the automation environment so the pipeline can continue.

- [ ] Step 1: Create `recovery.py` with InfraFailure enum and RecoveryManager class
- [ ] Step 2: Implement five recovery strategies as methods on RecoveryManager
- [ ] Step 3: Write tests with mocked device adapter (no real MaaFw needed)
- [ ] Step 4: Run tests, commit

**orchestrator/recovery.py content:**
```python
"""Cross-process infrastructure recovery.

Handles ONLY infrastructure-level failures that no single process can handle:
- device_disconnected: MaaFw controller lost connection
- window_lost: Game window closed or minimized
- screenshot_timeout: Screenshot capture fails repeatedly
- game_crash: Game process exited unexpectedly
- session_expired: Login session timed out (game kicked to title screen)

Game-level failures (battle failed, stamina empty, wrong page) are handled
within processes (Layer 7) and tasks (Layer 6).
"""
from __future__ import annotations

import asyncio
from enum import Enum
from typing import Protocol

from anime_game_afk.runtime.logger import get_logger

logger = get_logger("orchestrator.recovery")


class InfraFailure(Enum):
    """Infrastructure failure types that recovery can handle."""
    DEVICE_DISCONNECTED = "device_disconnected"
    WINDOW_LOST = "window_lost"
    SCREENSHOT_TIMEOUT = "screenshot_timeout"
    GAME_CRASH = "game_crash"
    SESSION_EXPIRED = "session_expired"


class DeviceHandle(Protocol):
    """Minimal device interface needed by recovery.

    Matches DeviceAdapter but only requires the methods recovery uses.
    Allows easy mocking in tests.
    """
    @property
    def connected(self) -> bool: ...
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def screenshot(self) -> object: ...
    def click(self, x: int, y: int) -> None: ...
    def press_key(self, vk_code: int) -> None: ...


class RecoveryManager:
    """Attempt to recover from infrastructure failures.

    Usage:
        recovery = RecoveryManager(device=device_adapter)
        recovered = await recovery.handle(InfraFailure.WINDOW_LOST)
        if not recovered:
            # pipeline should abort
    """

    # Maximum retries per recovery attempt before giving up
    MAX_RETRIES: int = 3
    # Delay between retry attempts in seconds
    RETRY_DELAY_S: float = 5.0
    # Delay after game crash before reconnect attempt
    CRASH_WAIT_S: float = 15.0

    def __init__(self, device: DeviceHandle) -> None:
        self._device = device
        self._strategies: dict[InfraFailure, object] = {
            InfraFailure.DEVICE_DISCONNECTED: self._recover_device_disconnected,
            InfraFailure.WINDOW_LOST: self._recover_window_lost,
            InfraFailure.SCREENSHOT_TIMEOUT: self._recover_screenshot_timeout,
            InfraFailure.GAME_CRASH: self._recover_game_crash,
            InfraFailure.SESSION_EXPIRED: self._recover_session_expired,
        }

    async def handle(self, failure: InfraFailure) -> bool:
        """Attempt to recover from the given infrastructure failure.

        Args:
            failure: The type of infrastructure failure that occurred.

        Returns:
            True if recovery succeeded and pipeline can continue.
            False if recovery failed and pipeline should abort.
        """
        strategy = self._strategies.get(failure)
        if strategy is None:
            logger.error("No recovery strategy for {failure}", failure=failure.value)
            return False

        logger.warning(
            "Infrastructure failure detected: {failure}. Attempting recovery...",
            failure=failure.value,
        )

        for attempt in range(1, self.MAX_RETRIES + 1):
            logger.info(
                "Recovery attempt {attempt}/{max} for {failure}",
                attempt=attempt,
                max=self.MAX_RETRIES,
                failure=failure.value,
            )
            try:
                success = await strategy()
                if success:
                    logger.info(
                        "Recovery succeeded for {failure} on attempt {attempt}",
                        failure=failure.value,
                        attempt=attempt,
                    )
                    return True
            except Exception as e:
                logger.error(
                    "Recovery attempt {attempt} raised exception: {err}",
                    attempt=attempt,
                    err=str(e),
                )

            if attempt < self.MAX_RETRIES:
                logger.info(
                    "Waiting {delay}s before next attempt...",
                    delay=self.RETRY_DELAY_S,
                )
                await asyncio.sleep(self.RETRY_DELAY_S)

        logger.error(
            "Recovery FAILED for {failure} after {max} attempts",
            failure=failure.value,
            max=self.MAX_RETRIES,
        )
        return False

    async def _recover_device_disconnected(self) -> bool:
        """Reconnect MaaFw controller to the game window.

        Strategy: disconnect cleanly, wait briefly, reconnect.
        """
        try:
            self._device.disconnect()
        except Exception:
            pass  # Already disconnected, ignore

        await asyncio.sleep(2.0)

        try:
            self._device.connect()
            return self._device.connected
        except Exception as e:
            logger.error("Reconnect failed: {err}", err=str(e))
            return False

    async def _recover_window_lost(self) -> bool:
        """Recover from game window lost (closed, minimized, moved offscreen).

        Strategy: disconnect, wait for window to reappear, reconnect.
        If the game window was merely minimized, MaaFw reconnect will find it.
        """
        try:
            self._device.disconnect()
        except Exception:
            pass

        await asyncio.sleep(3.0)

        try:
            self._device.connect()
            if not self._device.connected:
                return False
            # Verify we can actually capture a screenshot
            self._device.screenshot()
            return True
        except Exception as e:
            logger.error("Window recovery failed: {err}", err=str(e))
            return False

    async def _recover_screenshot_timeout(self) -> bool:
        """Recover from repeated screenshot capture failures.

        Strategy: try taking a screenshot directly. If that fails,
        full reconnect cycle.
        """
        try:
            self._device.screenshot()
            return True
        except Exception:
            pass

        # Full reconnect
        try:
            self._device.disconnect()
        except Exception:
            pass

        await asyncio.sleep(2.0)

        try:
            self._device.connect()
            self._device.screenshot()
            return True
        except Exception as e:
            logger.error("Screenshot recovery failed: {err}", err=str(e))
            return False

    async def _recover_game_crash(self) -> bool:
        """Recover from game process crash / unexpected exit.

        Strategy: wait for game to potentially auto-restart or for the
        user to manually restart it, then reconnect. This is the most
        severe failure — we wait longer before attempting reconnect.
        """
        logger.warning(
            "Game crash detected. Waiting {wait}s for restart...",
            wait=self.CRASH_WAIT_S,
        )
        await asyncio.sleep(self.CRASH_WAIT_S)

        try:
            self._device.disconnect()
        except Exception:
            pass

        try:
            self._device.connect()
            if not self._device.connected:
                return False
            # Verify screenshot works after reconnect
            self._device.screenshot()
            return True
        except Exception as e:
            logger.error("Game crash recovery failed: {err}", err=str(e))
            return False

    async def _recover_session_expired(self) -> bool:
        """Recover from login session expiry (kicked to title screen).

        Strategy: reconnect to device, then simulate clicking through
        the title screen to re-enter the game. The title screen typically
        has a "tap to start" prompt followed by server select / login.

        VK_RETURN (0x0D) is used to confirm prompts.
        """
        # Ensure device is connected
        if not self._device.connected:
            try:
                self._device.connect()
            except Exception as e:
                logger.error("Cannot reconnect for session recovery: {err}", err=str(e))
                return False

        # Click center of screen to dismiss "tap to start"
        # Design resolution: 1600x900
        self._device.click(800, 450)
        await asyncio.sleep(3.0)

        # Press Enter to confirm any login prompts
        self._device.press_key(0x0D)  # VK_RETURN
        await asyncio.sleep(5.0)

        # Press Enter again for server select / announcements
        self._device.press_key(0x0D)
        await asyncio.sleep(3.0)

        # Verify we can screenshot (proves we're connected and in-game)
        try:
            self._device.screenshot()
            return True
        except Exception as e:
            logger.error("Session recovery failed: {err}", err=str(e))
            return False
```

**tests/games/aether_gazer/orchestrator/test_recovery.py content:**
```python
"""Tests for infrastructure recovery strategies."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from anime_game_afk.games.aether_gazer.orchestrator.recovery import (
    InfraFailure,
    RecoveryManager,
)


class FakeDevice:
    """Mock device for recovery tests."""

    def __init__(self) -> None:
        self._connected = True
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.screenshot_calls = 0
        self.click_calls: list[tuple[int, int]] = []
        self.key_calls: list[int] = []
        # Control behavior
        self.connect_succeeds = True
        self.screenshot_succeeds = True

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        self.connect_calls += 1
        if not self.connect_succeeds:
            raise ConnectionError("Mock connect failed")
        self._connected = True

    def disconnect(self) -> None:
        self.disconnect_calls += 1
        self._connected = False

    def screenshot(self) -> object:
        self.screenshot_calls += 1
        if not self.screenshot_succeeds:
            raise RuntimeError("Mock screenshot failed")
        return object()

    def click(self, x: int, y: int) -> None:
        self.click_calls.append((x, y))

    def press_key(self, vk_code: int) -> None:
        self.key_calls.append(vk_code)


@pytest.fixture
def device() -> FakeDevice:
    return FakeDevice()


@pytest.fixture
def recovery(device: FakeDevice) -> RecoveryManager:
    mgr = RecoveryManager(device=device)
    # Speed up tests by reducing delays
    mgr.RETRY_DELAY_S = 0.01
    mgr.CRASH_WAIT_S = 0.01
    return mgr


class TestRecoveryDeviceDisconnected:
    @pytest.mark.asyncio
    async def test_reconnect_success(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        result = await recovery.handle(InfraFailure.DEVICE_DISCONNECTED)
        assert result is True
        assert device.connect_calls >= 1

    @pytest.mark.asyncio
    async def test_reconnect_failure(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        device.connect_succeeds = False
        result = await recovery.handle(InfraFailure.DEVICE_DISCONNECTED)
        assert result is False


class TestRecoveryWindowLost:
    @pytest.mark.asyncio
    async def test_window_recovery_success(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        result = await recovery.handle(InfraFailure.WINDOW_LOST)
        assert result is True
        assert device.screenshot_calls >= 1

    @pytest.mark.asyncio
    async def test_window_recovery_screenshot_fails(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        device.screenshot_succeeds = False
        result = await recovery.handle(InfraFailure.WINDOW_LOST)
        assert result is False


class TestRecoveryScreenshotTimeout:
    @pytest.mark.asyncio
    async def test_screenshot_works_immediately(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        result = await recovery.handle(InfraFailure.SCREENSHOT_TIMEOUT)
        assert result is True

    @pytest.mark.asyncio
    async def test_screenshot_needs_reconnect(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        call_count = 0
        original_screenshot = device.screenshot

        def flaky_screenshot() -> object:
            nonlocal call_count
            call_count += 1
            # First call fails, subsequent calls succeed
            if call_count == 1:
                raise RuntimeError("timeout")
            return original_screenshot()

        device.screenshot = flaky_screenshot
        result = await recovery.handle(InfraFailure.SCREENSHOT_TIMEOUT)
        assert result is True


class TestRecoveryGameCrash:
    @pytest.mark.asyncio
    async def test_crash_recovery_success(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        result = await recovery.handle(InfraFailure.GAME_CRASH)
        assert result is True
        assert device.connect_calls >= 1

    @pytest.mark.asyncio
    async def test_crash_recovery_game_not_restarted(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        device.connect_succeeds = False
        result = await recovery.handle(InfraFailure.GAME_CRASH)
        assert result is False


class TestRecoverySessionExpired:
    @pytest.mark.asyncio
    async def test_session_recovery_success(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        result = await recovery.handle(InfraFailure.SESSION_EXPIRED)
        assert result is True
        # Should click center screen + press Enter twice
        assert len(device.click_calls) >= 1
        assert len(device.key_calls) >= 2

    @pytest.mark.asyncio
    async def test_session_recovery_device_dead(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        device._connected = False
        device.connect_succeeds = False
        result = await recovery.handle(InfraFailure.SESSION_EXPIRED)
        assert result is False


class TestRecoveryRetries:
    @pytest.mark.asyncio
    async def test_retries_up_to_max(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        device.connect_succeeds = False
        result = await recovery.handle(InfraFailure.DEVICE_DISCONNECTED)
        assert result is False
        # Should have tried MAX_RETRIES times
        assert device.connect_calls == recovery.MAX_RETRIES
```

---

## Task 3: Process executor with timing and logging

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/orchestrator/executor.py`
- Test: `tests/games/aether_gazer/orchestrator/test_executor.py`

**Purpose:** Run individual processes sequentially with per-process logging, timing, and structured error handling. Reports results back to the pipeline for aggregation.

- [ ] Step 1: Create `executor.py` with ProcessExecutor class
- [ ] Step 2: Implement execute_one() and execute_all() methods
- [ ] Step 3: Write tests with mock processes
- [ ] Step 4: Run tests, commit

**orchestrator/executor.py content:**
```python
"""Process executor with timing, logging, and error handling.

Runs processes one at a time. Each process gets its own timing context
and structured log output. Errors are caught, classified, and reported
back to the pipeline for recovery decisions.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from anime_game_afk.core.errors import InfrastructureError
from anime_game_afk.games.aether_gazer.orchestrator.recovery import (
    InfraFailure,
    RecoveryManager,
)
from anime_game_afk.games.aether_gazer.orchestrator.types import ProcessDef
from anime_game_afk.runtime.logger import get_logger

logger = get_logger("orchestrator.executor")


# Map exception types/messages to InfraFailure categories
_INFRA_ERROR_MAP: dict[str, InfraFailure] = {
    "device_disconnected": InfraFailure.DEVICE_DISCONNECTED,
    "window_lost": InfraFailure.WINDOW_LOST,
    "screenshot_timeout": InfraFailure.SCREENSHOT_TIMEOUT,
    "game_crash": InfraFailure.GAME_CRASH,
    "session_expired": InfraFailure.SESSION_EXPIRED,
}


@dataclass
class ExecutionRecord:
    """Result of executing a single process.

    Attributes:
        process_name: Name of the process that ran.
        status: One of "success", "failed", "error", "recovered".
        elapsed_s: Wall-clock time in seconds.
        message: Human-readable result summary.
        data: Process-specific output data.
        infra_failure: If an infrastructure failure occurred, its type.
    """
    process_name: str
    status: str
    elapsed_s: float = 0.0
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    infra_failure: InfraFailure | None = None


def classify_infra_error(error: InfrastructureError) -> InfraFailure | None:
    """Classify an InfrastructureError into an InfraFailure category.

    Args:
        error: The caught InfrastructureError.

    Returns:
        Matching InfraFailure or None if unclassifiable.
    """
    error_msg = str(error).lower()
    for keyword, failure in _INFRA_ERROR_MAP.items():
        if keyword in error_msg:
            return failure
    return None


class ProcessExecutor:
    """Execute processes with timing, logging, and error classification.

    This class does NOT handle recovery directly. It catches errors,
    classifies them, and returns structured records. The Pipeline
    decides whether to attempt recovery.
    """

    def __init__(self, recovery: RecoveryManager) -> None:
        self._recovery = recovery

    async def execute_one(
        self,
        process: Any,
        proc_def: ProcessDef,
        ctx: Any,
    ) -> ExecutionRecord:
        """Execute a single process with timing and error handling.

        Args:
            process: A Process instance with an async execute(ctx) method.
            proc_def: The ProcessDef from the user plan (for metadata).
            ctx: ProcessContext to pass to process.execute().

        Returns:
            ExecutionRecord with status, timing, and any error info.
        """
        logger.info(
            "Starting process: {name}",
            name=proc_def.name,
        )
        start = time.monotonic()

        try:
            result = await process.execute(ctx)
            elapsed = time.monotonic() - start

            record = ExecutionRecord(
                process_name=proc_def.name,
                status=result.status,
                elapsed_s=elapsed,
                message=result.message if hasattr(result, "message") else "",
                data=result.data if hasattr(result, "data") else {},
            )
            logger.info(
                "Process {name} completed: status={status} in {elapsed:.1f}s",
                name=proc_def.name,
                status=record.status,
                elapsed=elapsed,
            )
            return record

        except InfrastructureError as e:
            elapsed = time.monotonic() - start
            failure = classify_infra_error(e)
            logger.error(
                "Process {name} hit infrastructure error after {elapsed:.1f}s: {err}",
                name=proc_def.name,
                elapsed=elapsed,
                err=str(e),
            )
            return ExecutionRecord(
                process_name=proc_def.name,
                status="error",
                elapsed_s=elapsed,
                message=f"Infrastructure error: {e}",
                infra_failure=failure,
            )

        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error(
                "Process {name} raised unexpected error after {elapsed:.1f}s: {err}",
                name=proc_def.name,
                elapsed=elapsed,
                err=str(e),
            )
            return ExecutionRecord(
                process_name=proc_def.name,
                status="error",
                elapsed_s=elapsed,
                message=f"Unexpected error: {e}",
            )

    async def execute_all(
        self,
        process_pairs: list[tuple[Any, ProcessDef, Any]],
    ) -> list[ExecutionRecord]:
        """Execute a list of processes sequentially.

        Attempts recovery on infrastructure failures. If recovery succeeds,
        retries the failed process once. If recovery fails, stops execution.

        Args:
            process_pairs: List of (process_instance, proc_def, ctx) tuples.

        Returns:
            List of ExecutionRecords, one per attempted process.
        """
        records: list[ExecutionRecord] = []

        for process, proc_def, ctx in process_pairs:
            record = await self.execute_one(process, proc_def, ctx)
            records.append(record)

            # If infrastructure error, attempt recovery
            if record.infra_failure is not None:
                recovered = await self._recovery.handle(record.infra_failure)
                if recovered:
                    logger.info(
                        "Recovery succeeded. Retrying process {name}...",
                        name=proc_def.name,
                    )
                    retry_record = await self.execute_one(process, proc_def, ctx)
                    retry_record.status = (
                        "recovered" if retry_record.status == "success"
                        else retry_record.status
                    )
                    records.append(retry_record)
                    # If retry also failed with infra error, abort
                    if retry_record.infra_failure is not None:
                        logger.error("Retry also failed with infra error. Aborting.")
                        break
                else:
                    logger.error(
                        "Recovery failed for {failure}. Aborting pipeline.",
                        failure=record.infra_failure.value,
                    )
                    break

        return records
```

**tests/games/aether_gazer/orchestrator/test_executor.py content:**
```python
"""Tests for process executor."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock

import pytest

from anime_game_afk.core.errors import InfrastructureError
from anime_game_afk.games.aether_gazer.orchestrator.executor import (
    ExecutionRecord,
    ProcessExecutor,
    classify_infra_error,
)
from anime_game_afk.games.aether_gazer.orchestrator.recovery import (
    InfraFailure,
    RecoveryManager,
)
from anime_game_afk.games.aether_gazer.orchestrator.types import ProcessDef


@dataclass
class FakeProcessResult:
    status: str = "success"
    message: str = ""
    data: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.data is None:
            self.data = {}


class FakeProcess:
    """Mock process for testing."""

    def __init__(self, result: FakeProcessResult | None = None, error: Exception | None = None) -> None:
        self._result = result or FakeProcessResult()
        self._error = error
        self.execute_count = 0

    async def execute(self, ctx: Any) -> FakeProcessResult:
        self.execute_count += 1
        if self._error is not None:
            raise self._error
        return self._result


class FakeRecovery:
    """Mock recovery manager."""

    def __init__(self, succeeds: bool = True) -> None:
        self._succeeds = succeeds
        self.handle_calls: list[InfraFailure] = []

    async def handle(self, failure: InfraFailure) -> bool:
        self.handle_calls.append(failure)
        return self._succeeds


@pytest.fixture
def recovery() -> FakeRecovery:
    return FakeRecovery()


@pytest.fixture
def executor(recovery: FakeRecovery) -> ProcessExecutor:
    return ProcessExecutor(recovery=recovery)


class TestClassifyInfraError:
    def test_device_disconnected(self) -> None:
        err = InfrastructureError("device_disconnected: controller lost")
        assert classify_infra_error(err) == InfraFailure.DEVICE_DISCONNECTED

    def test_window_lost(self) -> None:
        err = InfrastructureError("window_lost: HWND invalid")
        assert classify_infra_error(err) == InfraFailure.WINDOW_LOST

    def test_unknown_error(self) -> None:
        err = InfrastructureError("something weird happened")
        assert classify_infra_error(err) is None


class TestExecuteOne:
    @pytest.mark.asyncio
    async def test_successful_process(self, executor: ProcessExecutor) -> None:
        process = FakeProcess(FakeProcessResult(status="success", data={"stages": 5}))
        proc_def = ProcessDef(name="test_process")

        record = await executor.execute_one(process, proc_def, ctx=None)

        assert record.status == "success"
        assert record.process_name == "test_process"
        assert record.elapsed_s >= 0
        assert record.data == {"stages": 5}

    @pytest.mark.asyncio
    async def test_failed_process(self, executor: ProcessExecutor) -> None:
        process = FakeProcess(FakeProcessResult(status="failed", message="no stamina"))
        proc_def = ProcessDef(name="farm")

        record = await executor.execute_one(process, proc_def, ctx=None)

        assert record.status == "failed"
        assert record.infra_failure is None

    @pytest.mark.asyncio
    async def test_infra_error_classified(self, executor: ProcessExecutor) -> None:
        process = FakeProcess(
            error=InfrastructureError("device_disconnected: lost connection")
        )
        proc_def = ProcessDef(name="daily")

        record = await executor.execute_one(process, proc_def, ctx=None)

        assert record.status == "error"
        assert record.infra_failure == InfraFailure.DEVICE_DISCONNECTED

    @pytest.mark.asyncio
    async def test_unexpected_error(self, executor: ProcessExecutor) -> None:
        process = FakeProcess(error=RuntimeError("something broke"))
        proc_def = ProcessDef(name="push")

        record = await executor.execute_one(process, proc_def, ctx=None)

        assert record.status == "error"
        assert record.infra_failure is None
        assert "something broke" in record.message


class TestExecuteAll:
    @pytest.mark.asyncio
    async def test_all_succeed(self, executor: ProcessExecutor) -> None:
        pairs = [
            (FakeProcess(), ProcessDef(name="a"), None),
            (FakeProcess(), ProcessDef(name="b"), None),
            (FakeProcess(), ProcessDef(name="c"), None),
        ]
        records = await executor.execute_all(pairs)

        assert len(records) == 3
        assert all(r.status == "success" for r in records)

    @pytest.mark.asyncio
    async def test_infra_error_triggers_recovery(
        self, recovery: FakeRecovery, executor: ProcessExecutor
    ) -> None:
        # First process raises infra error, recovery succeeds, retry succeeds
        fail_once = FakeProcess(
            error=InfrastructureError("device_disconnected: lost")
        )
        # After recovery, the retry will also raise (same process instance)
        # So we need a process that fails once then succeeds
        call_count = 0

        async def flaky_execute(ctx: Any) -> FakeProcessResult:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise InfrastructureError("device_disconnected: lost")
            return FakeProcessResult(status="success")

        flaky = FakeProcess()
        flaky.execute = flaky_execute

        pairs = [
            (flaky, ProcessDef(name="flaky_proc"), None),
            (FakeProcess(), ProcessDef(name="b"), None),
        ]
        records = await executor.execute_all(pairs)

        assert len(recovery.handle_calls) == 1
        assert recovery.handle_calls[0] == InfraFailure.DEVICE_DISCONNECTED

    @pytest.mark.asyncio
    async def test_unrecoverable_error_aborts(self) -> None:
        recovery = FakeRecovery(succeeds=False)
        executor = ProcessExecutor(recovery=recovery)

        fail_proc = FakeProcess(
            error=InfrastructureError("window_lost: gone")
        )
        pairs = [
            (fail_proc, ProcessDef(name="a"), None),
            (FakeProcess(), ProcessDef(name="b"), None),  # should not run
        ]
        records = await executor.execute_all(pairs)

        # Only the failed process should have a record (b never runs)
        process_names = [r.process_name for r in records]
        assert "a" in process_names
        assert "b" not in process_names
```

---

## Task 4: Pipeline — main orchestrator class

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/orchestrator/pipeline.py`
- Test: `tests/games/aether_gazer/orchestrator/test_pipeline.py`

**Purpose:** The top-level Pipeline class. Loads a plan, resolves process names to process instances, builds contexts, and delegates execution to the ProcessExecutor. Aggregates results into a PipelineResult.

- [ ] Step 1: Create `pipeline.py` with Pipeline class and process registry
- [ ] Step 2: Implement run() method with plan loading, process resolution, and execution
- [ ] Step 3: Write tests with mock process registry
- [ ] Step 4: Run tests, commit

**orchestrator/pipeline.py content:**
```python
"""Main pipeline: load plan, resolve processes, execute.

The Pipeline is the single entry point for running automation.
External code (scripts/run.py) creates a Pipeline and calls run().
"""
from __future__ import annotations

import time
from typing import Any

from anime_game_afk.games.aether_gazer.orchestrator.executor import (
    ExecutionRecord,
    ProcessExecutor,
)
from anime_game_afk.games.aether_gazer.orchestrator.recovery import RecoveryManager
from anime_game_afk.games.aether_gazer.orchestrator.types import (
    PipelineResult,
    PlanConfig,
    ProcessDef,
    load_plan,
)
from anime_game_afk.runtime.logger import get_logger

logger = get_logger("orchestrator.pipeline")


class ProcessRegistry:
    """Maps process names to process factory functions.

    Processes register themselves here. The pipeline looks up
    process names from the user plan and instantiates them.
    """

    def __init__(self) -> None:
        self._factories: dict[str, Any] = {}

    def register(self, name: str, factory: Any) -> None:
        """Register a process factory by name.

        Args:
            name: Process name as it appears in the YAML plan.
            factory: Callable that returns a Process instance.
        """
        self._factories[name] = factory
        logger.debug("Registered process: {name}", name=name)

    def create(self, name: str) -> Any:
        """Create a process instance by name.

        Args:
            name: Process name from the YAML plan.

        Returns:
            A Process instance.

        Raises:
            KeyError: If the process name is not registered.
        """
        if name not in self._factories:
            available = ", ".join(sorted(self._factories.keys()))
            raise KeyError(
                f"Unknown process '{name}'. Available: [{available}]"
            )
        return self._factories[name]()

    def available(self) -> list[str]:
        """Return sorted list of registered process names."""
        return sorted(self._factories.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._factories


class Pipeline:
    """Top-level orchestrator. Loads a plan and executes processes.

    Usage:
        registry = ProcessRegistry()
        registry.register("daily_routine", DailyRoutine)
        registry.register("push_main_story", PushMainStory)

        pipeline = Pipeline(
            registry=registry,
            device=device_adapter,
            context_factory=build_process_context,
        )
        result = await pipeline.run("plans/my_plan.yaml")
    """

    def __init__(
        self,
        registry: ProcessRegistry,
        device: Any,
        context_factory: Any,
    ) -> None:
        """Initialize the pipeline.

        Args:
            registry: ProcessRegistry with registered process factories.
            device: DeviceAdapter instance for device interaction.
            context_factory: Callable(proc_def) -> ProcessContext.
                             Builds a context for each process from its config.
        """
        self._registry = registry
        self._device = device
        self._context_factory = context_factory
        self._recovery = RecoveryManager(device=device)
        self._executor = ProcessExecutor(recovery=self._recovery)

    async def run(self, plan_source: Any) -> PipelineResult:
        """Load a plan and execute all enabled processes.

        Args:
            plan_source: Path to YAML file, or a dict / PlanConfig.

        Returns:
            PipelineResult with execution summary.
        """
        # Load plan
        if isinstance(plan_source, PlanConfig):
            plan = plan_source
        else:
            plan = load_plan(plan_source)

        enabled = plan.enabled_processes
        total = len(plan.processes)
        skipped = total - len(enabled)

        logger.info(
            "Pipeline starting: {enabled}/{total} processes enabled",
            enabled=len(enabled),
            total=total,
        )

        # Validate all process names before starting
        unknown = [p.name for p in enabled if p.name not in self._registry]
        if unknown:
            logger.error(
                "Unknown processes in plan: {unknown}. Available: {available}",
                unknown=unknown,
                available=self._registry.available(),
            )
            return PipelineResult(
                total=len(enabled),
                failed=len(enabled),
                skipped=skipped,
                aborted=True,
                details=[{
                    "error": f"Unknown processes: {unknown}",
                }],
            )

        # Build (process, proc_def, ctx) tuples
        process_pairs: list[tuple[Any, ProcessDef, Any]] = []
        for proc_def in enabled:
            process = self._registry.create(proc_def.name)
            ctx = self._context_factory(proc_def)
            process_pairs.append((process, proc_def, ctx))

        # Execute
        start = time.monotonic()
        records = await self._executor.execute_all(process_pairs)
        elapsed = time.monotonic() - start

        # Aggregate results
        result = self._aggregate(records, skipped, elapsed)

        logger.info(
            "Pipeline complete: {succeeded}/{total} succeeded, "
            "{failed} failed, {skipped} skipped in {elapsed:.1f}s",
            succeeded=result.succeeded,
            total=result.total,
            failed=result.failed,
            skipped=result.skipped,
            elapsed=result.elapsed_s,
        )

        return result

    def _aggregate(
        self,
        records: list[ExecutionRecord],
        skipped: int,
        elapsed: float,
    ) -> PipelineResult:
        """Aggregate execution records into a PipelineResult.

        Args:
            records: List of per-process execution records.
            skipped: Number of processes skipped (disabled in plan).
            elapsed: Total wall-clock time in seconds.

        Returns:
            Aggregated PipelineResult.
        """
        succeeded = sum(1 for r in records if r.status in ("success", "recovered"))
        failed = sum(1 for r in records if r.status in ("failed", "error"))
        aborted = any(r.infra_failure is not None and r.status == "error" for r in records)

        # Deduplicate: if a process was retried after recovery,
        # count only the final attempt
        seen_names: set[str] = set()
        unique_records = []
        for record in reversed(records):
            if record.process_name not in seen_names:
                seen_names.add(record.process_name)
                unique_records.append(record)
        unique_records.reverse()

        details = [
            {
                "name": r.process_name,
                "status": r.status,
                "elapsed_s": round(r.elapsed_s, 2),
                "message": r.message,
            }
            for r in records  # All records including retries
        ]

        return PipelineResult(
            total=len(unique_records),
            succeeded=sum(1 for r in unique_records if r.status in ("success", "recovered")),
            failed=sum(1 for r in unique_records if r.status in ("failed", "error")),
            skipped=skipped,
            aborted=aborted,
            details=details,
            elapsed_s=round(elapsed, 2),
        )
```

**tests/games/aether_gazer/orchestrator/test_pipeline.py content:**
```python
"""Tests for the main Pipeline class."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from anime_game_afk.games.aether_gazer.orchestrator.pipeline import (
    Pipeline,
    ProcessRegistry,
)
from anime_game_afk.games.aether_gazer.orchestrator.types import (
    PlanConfig,
    ProcessDef,
)


@dataclass
class MockResult:
    status: str = "success"
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class MockProcess:
    """Process that always succeeds."""
    def __init__(self) -> None:
        self.executed = False

    async def execute(self, ctx: Any) -> MockResult:
        self.executed = True
        return MockResult(status="success")


class FailingProcess:
    """Process that always fails."""
    async def execute(self, ctx: Any) -> MockResult:
        return MockResult(status="failed", message="intentional failure")


class MockDevice:
    """Minimal device mock for Pipeline tests."""
    @property
    def connected(self) -> bool:
        return True

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def screenshot(self) -> object:
        return object()

    def click(self, x: int, y: int) -> None:
        pass

    def press_key(self, vk_code: int) -> None:
        pass


@pytest.fixture
def registry() -> ProcessRegistry:
    reg = ProcessRegistry()
    reg.register("daily_routine", MockProcess)
    reg.register("push_main_story", MockProcess)
    reg.register("farm_resources", MockProcess)
    return reg


@pytest.fixture
def pipeline(registry: ProcessRegistry) -> Pipeline:
    device = MockDevice()
    return Pipeline(
        registry=registry,
        device=device,
        context_factory=lambda proc_def: {"config": proc_def.config},
    )


class TestProcessRegistry:
    def test_register_and_create(self) -> None:
        reg = ProcessRegistry()
        reg.register("test", MockProcess)
        proc = reg.create("test")
        assert isinstance(proc, MockProcess)

    def test_unknown_process_raises(self) -> None:
        reg = ProcessRegistry()
        with pytest.raises(KeyError, match="Unknown process"):
            reg.create("nonexistent")

    def test_available_sorted(self) -> None:
        reg = ProcessRegistry()
        reg.register("z_process", MockProcess)
        reg.register("a_process", MockProcess)
        assert reg.available() == ["a_process", "z_process"]

    def test_contains(self) -> None:
        reg = ProcessRegistry()
        reg.register("test", MockProcess)
        assert "test" in reg
        assert "other" not in reg


class TestPipeline:
    @pytest.mark.asyncio
    async def test_run_all_enabled(self, pipeline: Pipeline) -> None:
        plan = PlanConfig(
            game="aether_gazer",
            processes=[
                ProcessDef(name="daily_routine", enabled=True),
                ProcessDef(name="push_main_story", enabled=True),
            ],
        )
        result = await pipeline.run(plan)

        assert result.succeeded == 2
        assert result.failed == 0
        assert result.total == 2

    @pytest.mark.asyncio
    async def test_skipped_processes_counted(self, pipeline: Pipeline) -> None:
        plan = PlanConfig(
            game="aether_gazer",
            processes=[
                ProcessDef(name="daily_routine", enabled=True),
                ProcessDef(name="push_main_story", enabled=False),
                ProcessDef(name="farm_resources", enabled=False),
            ],
        )
        result = await pipeline.run(plan)

        assert result.succeeded == 1
        assert result.skipped == 2
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_unknown_process_aborts(self, pipeline: Pipeline) -> None:
        plan = PlanConfig(
            game="aether_gazer",
            processes=[
                ProcessDef(name="nonexistent_process", enabled=True),
            ],
        )
        result = await pipeline.run(plan)

        assert result.aborted is True
        assert result.failed > 0

    @pytest.mark.asyncio
    async def test_failed_process_reported(self) -> None:
        reg = ProcessRegistry()
        reg.register("fail_proc", FailingProcess)
        device = MockDevice()
        pipeline = Pipeline(
            registry=reg,
            device=device,
            context_factory=lambda pd: None,
        )

        plan = PlanConfig(
            game="aether_gazer",
            processes=[ProcessDef(name="fail_proc", enabled=True)],
        )
        result = await pipeline.run(plan)

        assert result.failed == 1
        assert result.succeeded == 0

    @pytest.mark.asyncio
    async def test_run_from_dict(self, pipeline: Pipeline) -> None:
        plan_dict = {
            "game": "aether_gazer",
            "processes": [
                {"name": "daily_routine", "enabled": True},
            ],
        }
        result = await pipeline.run(plan_dict)
        assert result.succeeded == 1

    @pytest.mark.asyncio
    async def test_elapsed_time_recorded(self, pipeline: Pipeline) -> None:
        plan = PlanConfig(
            game="aether_gazer",
            processes=[ProcessDef(name="daily_routine", enabled=True)],
        )
        result = await pipeline.run(plan)
        assert result.elapsed_s >= 0
```

---

## Task 5: Default plan template

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/orchestrator/plans/default.yaml`
- Test: `tests/games/aether_gazer/orchestrator/test_default_plan.py`

**Purpose:** Provide a default plan template that new users can copy and customize. Also serves as a documentation example.

- [ ] Step 1: Create the `plans/` directory
- [ ] Step 2: Write `default.yaml` with all known processes and sensible defaults
- [ ] Step 3: Write a test that loads `default.yaml` and validates it parses correctly
- [ ] Step 4: Commit

**orchestrator/plans/default.yaml content:**
```yaml
# Default automation plan for AetherGazer (深空之眼)
#
# Copy this file and customize it for your daily run.
# Set enabled: false to skip a process.
# Each process has an optional 'config' section for fine-tuning.
#
# Usage:
#   python scripts/run.py --plan path/to/your_plan.yaml

game: aether_gazer

processes:
  # Complete daily tasks: sign-in, daily missions, collect rewards
  - name: daily_routine
    enabled: true

  # Push main story from current progress
  - name: push_main_story
    enabled: true
    config:
      # "current" = continue from last completed chapter
      target_chapter: current
      # Maximum number of stages to attempt per run
      max_stages: 20

  # Clear 梦境再构 (Dream Realm)
  - name: dream_realm
    enabled: false

  # Spend stamina on resource farming stages
  - name: farm_resources
    enabled: true
    config:
      # Stage names to farm (Chinese names as they appear in-game)
      stages:
        - "模拟作战"
        - "极限萃取"
      # Maximum total runs across all stages
      max_runs: 6

  # Clear weekly boss stages
  - name: weekly_bosses
    enabled: false
```

**tests/games/aether_gazer/orchestrator/test_default_plan.py content:**
```python
"""Test that the default plan template is valid and loadable."""
from pathlib import Path

from anime_game_afk.games.aether_gazer.orchestrator.types import load_plan


def test_default_plan_loads() -> None:
    """Verify default.yaml is parseable and structurally valid."""
    plan_path = (
        Path(__file__).resolve().parents[4]
        / "src"
        / "anime_game_afk"
        / "games"
        / "aether_gazer"
        / "orchestrator"
        / "plans"
        / "default.yaml"
    )
    assert plan_path.exists(), f"Default plan not found at {plan_path}"

    plan = load_plan(plan_path)
    assert plan.game == "aether_gazer"
    assert len(plan.processes) >= 3

    # Verify structure: all processes have names
    for proc in plan.processes:
        assert proc.name, "Process must have a name"
        assert isinstance(proc.enabled, bool)
        assert isinstance(proc.config, dict)


def test_default_plan_has_daily_routine() -> None:
    """Daily routine should be enabled by default."""
    plan_path = (
        Path(__file__).resolve().parents[4]
        / "src"
        / "anime_game_afk"
        / "games"
        / "aether_gazer"
        / "orchestrator"
        / "plans"
        / "default.yaml"
    )
    plan = load_plan(plan_path)
    daily = next((p for p in plan.processes if p.name == "daily_routine"), None)
    assert daily is not None
    assert daily.enabled is True


def test_default_plan_farm_config() -> None:
    """Farm resources should have stages and max_runs in config."""
    plan_path = (
        Path(__file__).resolve().parents[4]
        / "src"
        / "anime_game_afk"
        / "games"
        / "aether_gazer"
        / "orchestrator"
        / "plans"
        / "default.yaml"
    )
    plan = load_plan(plan_path)
    farm = next((p for p in plan.processes if p.name == "farm_resources"), None)
    assert farm is not None
    assert "stages" in farm.config
    assert "max_runs" in farm.config
    assert isinstance(farm.config["stages"], list)
```

---

## Task 6: Main entry point — scripts/run.py

**Files:**
- Create: `scripts/run.py`
- Modify: `src/anime_game_afk/games/aether_gazer/orchestrator/__init__.py` — add Pipeline, ProcessRegistry exports

**Purpose:** Create the main entry point that users actually run. Uses argparse to accept a plan file, initializes the device, registers all known processes, creates the pipeline, and executes.

- [ ] Step 1: Create `scripts/run.py` with argparse, device setup, process registration
- [ ] Step 2: Implement main() with async pipeline execution
- [ ] Step 3: Update orchestrator `__init__.py` to export Pipeline and ProcessRegistry
- [ ] Step 4: Test manually: `python scripts/run.py --help` should print usage
- [ ] Step 5: Commit

**scripts/run.py content:**
```python
"""Main entry point for AetherGazer automation.

Usage:
    python scripts/run.py
    python scripts/run.py --plan path/to/my_plan.yaml
    python scripts/run.py --plan plans/default.yaml --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

# Ensure src/ is on the import path
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root / "src"))

from anime_game_afk.core.device import DeviceAdapter
from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
from anime_game_afk.games.aether_gazer.orchestrator.pipeline import (
    Pipeline,
    ProcessRegistry,
)
from anime_game_afk.games.aether_gazer.orchestrator.types import ProcessDef
from anime_game_afk.runtime.logger import get_logger

# Import all process classes for registration
# These are created in Wave 3 (Layer 7)
from anime_game_afk.games.aether_gazer.processes.daily_routine import DailyRoutine
from anime_game_afk.games.aether_gazer.processes.push_main_story import PushMainStory
from anime_game_afk.games.aether_gazer.processes.farm_resources import FarmResources

logger = get_logger("run")

# Default plan path relative to project root
DEFAULT_PLAN = (
    _project_root
    / "src"
    / "anime_game_afk"
    / "games"
    / "aether_gazer"
    / "orchestrator"
    / "plans"
    / "default.yaml"
)


def build_registry() -> ProcessRegistry:
    """Register all available processes.

    Each process class is mapped to the name used in YAML plans.
    Add new processes here as they are implemented.
    """
    registry = ProcessRegistry()
    registry.register("daily_routine", DailyRoutine)
    registry.register("push_main_story", PushMainStory)
    registry.register("farm_resources", FarmResources)
    # Future processes:
    # registry.register("dream_realm", DreamRealm)
    # registry.register("weekly_bosses", WeeklyBosses)
    return registry


def build_context_factory(device: DeviceAdapter):
    """Create a factory function that builds ProcessContext for each process.

    Args:
        device: Connected DeviceAdapter instance.

    Returns:
        Callable(ProcessDef) -> ProcessContext
    """
    from anime_game_afk.games.aether_gazer.processes.base import ProcessContext

    def factory(proc_def: ProcessDef) -> ProcessContext:
        return ProcessContext(
            device=device,
            config=proc_def.config,
            logger=get_logger(f"process.{proc_def.name}"),
        )

    return factory


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="AetherGazer automation pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/run.py                           # Run default plan\n"
            "  python scripts/run.py --plan my_plan.yaml       # Run custom plan\n"
            "  python scripts/run.py --list                    # List available processes\n"
        ),
    )
    parser.add_argument(
        "--plan",
        type=str,
        default=str(DEFAULT_PLAN),
        help="Path to YAML plan file (default: plans/default.yaml)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available processes and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse plan and show what would run, without executing",
    )
    return parser.parse_args()


async def async_main(args: argparse.Namespace) -> int:
    """Async entry point.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code: 0 for success, 1 for failure.
    """
    registry = build_registry()

    # List mode: show available processes and exit
    if args.list:
        print("Available processes:")
        for name in registry.available():
            print(f"  - {name}")
        return 0

    # Dry-run mode: parse plan and show execution order
    if args.dry_run:
        from anime_game_afk.games.aether_gazer.orchestrator.types import load_plan

        plan = load_plan(args.plan)
        print(f"Plan: {args.plan}")
        print(f"Game: {plan.game}")
        print(f"Processes ({len(plan.enabled_processes)} enabled):")
        for proc in plan.processes:
            status = "ENABLED" if proc.enabled else "disabled"
            config_str = f" config={proc.config}" if proc.config else ""
            print(f"  [{status}] {proc.name}{config_str}")
        return 0

    # Connect to game
    logger.info("Connecting to AetherGazer...")
    device = DeviceAdapter(config=AETHER_GAZER_CONFIG)
    device.connect()

    if not device.connected:
        logger.error("Failed to connect to game window. Is AetherGazer running?")
        return 1

    logger.info("Connected. Resolution: {res}", res=device.resolution)

    try:
        # Build pipeline and run
        pipeline = Pipeline(
            registry=registry,
            device=device,
            context_factory=build_context_factory(device),
        )

        result = await pipeline.run(args.plan)

        # Print summary
        print("\n" + "=" * 60)
        print("Pipeline Summary")
        print("=" * 60)
        print(f"  Total:     {result.total}")
        print(f"  Succeeded: {result.succeeded}")
        print(f"  Failed:    {result.failed}")
        print(f"  Skipped:   {result.skipped}")
        print(f"  Time:      {result.elapsed_s:.1f}s")
        print(f"  Aborted:   {result.aborted}")
        print("=" * 60)

        if result.details:
            print("\nDetails:")
            for d in result.details:
                print(f"  {d.get('name', '?')}: {d.get('status', '?')} ({d.get('elapsed_s', 0):.1f}s)")

        return 0 if not result.aborted and result.failed == 0 else 1

    finally:
        device.disconnect()
        logger.info("Disconnected from game.")


def main() -> None:
    """Synchronous entry point."""
    args = parse_args()
    exit_code = asyncio.run(async_main(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
```

**Updated orchestrator/__init__.py:**
```python
"""Layer 8: Orchestrator / Pipeline.

Executes a user-configured selection of processes.
Loads YAML plans, runs processes sequentially, handles infrastructure recovery.

Dependency rule: imports from Layers 0-7 only.
"""

from anime_game_afk.games.aether_gazer.orchestrator.pipeline import (
    Pipeline,
    ProcessRegistry,
)
from anime_game_afk.games.aether_gazer.orchestrator.types import (
    PipelineResult,
    PlanConfig,
    ProcessDef,
    load_plan,
)

__all__ = [
    "Pipeline",
    "PipelineResult",
    "PlanConfig",
    "ProcessDef",
    "ProcessRegistry",
    "load_plan",
]
```

---

## Task 7: Scripts cleanup and reorganization

**Files:**
- Create: `scripts/debug/` directory
- Move: `scripts/explore.py` → `scripts/debug/explore.py`
- Move: `scripts/explore_all_pages.py` → `scripts/debug/explore_all_pages.py`
- Move: `scripts/explore_deep.py` → `scripts/debug/explore_deep.py`
- Move: `scripts/explore_systematic.py` → `scripts/debug/explore_systematic.py`
- Move: `scripts/crop_templates.py` → `scripts/debug/crop_templates.py`
- Move: `scripts/extract_templates.py` → `scripts/debug/extract_templates.py`
- Move: `scripts/extract_templates_v2.py` → `scripts/debug/extract_templates_v2.py`
- Move: `scripts/battle_spam.py` → `scripts/debug/battle_spam.py`
- Move: `scripts/run_daily.py` → `scripts/debug/run_daily.py` (superseded by run.py)
- Delete: `scripts/ch6_clear.py` (superseded by new architecture)
- Delete: `scripts/ch6_clear_v2.py` (superseded by new architecture)
- Move: `scripts/ch6_battle.py` → `scripts/debug/ch6_battle.py` (reference only)
- Keep: `scripts/snap.py` (debug screenshot tool, stays at top level)
- Keep: `scripts/run.py` (main entry point, created in Task 6)
- Create: `scripts/README.md`
- Create: `scripts/debug/README.md`

**Purpose:** Clean scripts/ down to two top-level files (run.py, snap.py) plus a debug/ directory for historical reference scripts. Delete superseded scripts that have been fully replaced by the layered architecture.

- [ ] Step 1: Create `scripts/debug/` directory
- [ ] Step 2: Move exploration scripts to `scripts/debug/` using `git mv`
- [ ] Step 3: Move template extraction scripts to `scripts/debug/`
- [ ] Step 4: Move battle_spam.py, run_daily.py, ch6_battle.py to `scripts/debug/`
- [ ] Step 5: Delete ch6_clear.py and ch6_clear_v2.py using `git rm`
- [ ] Step 6: Write `scripts/README.md` and `scripts/debug/README.md`
- [ ] Step 7: Verify `scripts/snap.py` still runs: `python scripts/snap.py --help`
- [ ] Step 8: Commit

**scripts/README.md content:**
```markdown
# Scripts

Entry points and debug tools. All real logic lives in `src/`.

## Files

| File | Purpose |
|---|---|
| `run.py` | Main entry point: load YAML plan → run automation pipeline |
| `snap.py` | Debug tool: screenshot, click, crop for coordinate exploration |

## Usage

```bash
# Run the automation pipeline with default plan
python scripts/run.py

# Run with a custom plan
python scripts/run.py --plan path/to/my_plan.yaml

# List available processes
python scripts/run.py --list

# Dry-run: show what would execute without running
python scripts/run.py --dry-run

# Debug: take a screenshot and explore coordinates
python scripts/snap.py
```

## debug/

Historical exploration and development scripts. Kept for reference only.
These scripts may have broken imports and are NOT maintained.
```

**scripts/debug/README.md content:**
```markdown
# Debug Scripts

Historical scripts from the exploration/development phase.
Kept for reference only — these are NOT maintained and may have broken imports.

| File | Original purpose |
|---|---|
| `explore.py` | Initial page exploration |
| `explore_all_pages.py` | Systematic page discovery |
| `explore_deep.py` | Deep navigation tree exploration |
| `explore_systematic.py` | Systematic UI element mapping |
| `crop_templates.py` | Crop template images from screenshots |
| `extract_templates.py` | Extract and save UI templates |
| `extract_templates_v2.py` | Improved template extraction |
| `battle_spam.py` | Raw key-spam battle testing |
| `run_daily.py` | Old daily task runner (superseded by run.py) |
| `ch6_battle.py` | Chapter 6 battle state machine (reference for combat_tasks.py) |
```

---

## Task 8: Legacy code removal and import updates

**Files:**
- Delete: `src/anime_game_afk/games/aether_gazer/pages/` (migrated to knowledge/ + ops/perception/)
- Delete: `src/anime_game_afk/games/aether_gazer/nav/` (migrated to ops/navigate/)
- Delete: `src/anime_game_afk/games/aether_gazer/tasks/` (migrated to tasks/ + processes/)
- Delete: `src/anime_game_afk/task/` (empty stub, never used)
- Create: `src/anime_game_afk/games/aether_gazer/pages/__init__.py` (deprecation wrapper)
- Create: `src/anime_game_afk/games/aether_gazer/nav/__init__.py` (deprecation wrapper)
- Create: `src/anime_game_afk/games/aether_gazer/tasks/__init__.py` (deprecation wrapper)
- Modify: `src/anime_game_afk/games/aether_gazer/README.md` — update directory listing
- Modify: `src/anime_game_afk/README.md` — update top-level structure overview
- Modify: `docs/` — update architecture documentation

**Purpose:** Remove old directory structure that has been replaced by the layered architecture. Use deprecation wrappers for a grace period so any remaining references get clear error messages instead of silent failures. Update all documentation to reflect the new structure.

- [ ] Step 1: Delete `src/anime_game_afk/task/` entirely (empty stub)
- [ ] Step 2: Clear old files from `pages/`, keep only `__init__.py` with deprecation wrapper
- [ ] Step 3: Clear old files from `nav/`, keep only `__init__.py` with deprecation wrapper
- [ ] Step 4: Clear old files from `tasks/` (old), keep only `__init__.py` with deprecation wrapper
- [ ] Step 5: Write deprecation wrappers for pages/, nav/, tasks/ (old)
- [ ] Step 6: Update `games/aether_gazer/README.md` with new directory structure
- [ ] Step 7: Update `src/anime_game_afk/README.md` with full architecture overview
- [ ] Step 8: Verify no broken imports: `python -c "import anime_game_afk"`
- [ ] Step 9: Commit

**Deprecation wrapper — pages/__init__.py:**
```python
"""DEPRECATED: This module has been migrated.

Page definitions → knowledge/pages.py
Page identification → ops/perception/identify_page.py
Template identification → ops/perception/identify_page.py

This wrapper exists temporarily so old imports produce clear errors.
Remove after all references have been updated.
"""
import warnings


def __getattr__(name: str):
    """Raise clear deprecation error for any attribute access."""
    warnings.warn(
        f"anime_game_afk.games.aether_gazer.pages is DEPRECATED. "
        f"Attribute '{name}' has been migrated:\n"
        f"  Page definitions → knowledge/pages.py\n"
        f"  Page identification → ops/perception/identify_page.py\n"
        f"  Template matching → ops/perception/identify_page.py\n"
        f"Update your imports accordingly.",
        DeprecationWarning,
        stacklevel=2,
    )
    raise ImportError(
        f"Module 'pages' is deprecated. '{name}' has moved. "
        f"See deprecation warning for new locations."
    )
```

**Deprecation wrapper — nav/__init__.py:**
```python
"""DEPRECATED: This module has been migrated.

Navigator → ops/navigate/goto_page.py
Navigation graph → knowledge/navigation.py

This wrapper exists temporarily so old imports produce clear errors.
Remove after all references have been updated.
"""
import warnings


def __getattr__(name: str):
    """Raise clear deprecation error for any attribute access."""
    warnings.warn(
        f"anime_game_afk.games.aether_gazer.nav is DEPRECATED. "
        f"Attribute '{name}' has been migrated:\n"
        f"  Navigator → ops/navigate/goto_page.py\n"
        f"  Navigation graph → knowledge/navigation.py\n"
        f"Update your imports accordingly.",
        DeprecationWarning,
        stacklevel=2,
    )
    raise ImportError(
        f"Module 'nav' is deprecated. '{name}' has moved. "
        f"See deprecation warning for new locations."
    )
```

**Deprecation wrapper — tasks/__init__.py (old tasks):**
```python
"""DEPRECATED: This module has been migrated.

BaseTask / TaskContext → processes/base.py (Layer 7) or tasks/base.py (Layer 6)
SinglePointTask → ops/ (Layer 5, one file per op)
CompleteTask → tasks/ (Layer 6, composable tasks)
TaskSequence → orchestrator/pipeline.py (Layer 8)
atomic.py → ops/ (Layer 5, split into subdirectories)
daily.py → processes/daily_routine.py (Layer 7)

This wrapper exists temporarily so old imports produce clear errors.
Remove after all references have been updated.
"""
import warnings


def __getattr__(name: str):
    """Raise clear deprecation error for any attribute access."""
    _migration_map = {
        "BaseTask": "processes/base.py or tasks/base.py",
        "TaskContext": "processes/base.py (ProcessContext)",
        "SinglePointTask": "ops/ (one file per atomic operation)",
        "CompleteTask": "tasks/ (composable task modules)",
        "TaskSequence": "orchestrator/pipeline.py (Pipeline)",
        "TaskStatus": "processes/base.py or tasks/base.py",
    }
    new_location = _migration_map.get(name, "see architecture docs")
    warnings.warn(
        f"anime_game_afk.games.aether_gazer.tasks is DEPRECATED. "
        f"'{name}' has moved to: {new_location}\n"
        f"Update your imports accordingly.",
        DeprecationWarning,
        stacklevel=2,
    )
    raise ImportError(
        f"Module 'tasks' (old) is deprecated. '{name}' has moved to: {new_location}"
    )
```

**games/aether_gazer/README.md content:**
```markdown
# AetherGazer (深空之眼) Game Module

Game-specific automation for AetherGazer, built on the layered architecture.

## Directory Structure

```
aether_gazer/
├── knowledge/          # Layer 4: Pure data (pages, nav graph, keys, constants)
├── ops/                # Layer 5: Atomic operations (perception, navigate, interact, combat)
├── tasks/              # Layer 6: Composable multi-step tasks
├── processes/          # Layer 7: Complete user-visible features
├── orchestrator/       # Layer 8: Pipeline execution and recovery
├── config.py           # Game configuration (window title, MaaFw settings)
├── adapter.py          # Game-specific adapter utilities
└── __init__.py
```

## Deprecated Directories (to be removed)

The following directories contain deprecation wrappers that redirect to new locations:

- `pages/` → migrated to `knowledge/pages.py` + `ops/perception/`
- `nav/` → migrated to `knowledge/navigation.py` + `ops/navigate/`
- `tasks/` (old) → migrated to `tasks/` (new Layer 6) + `processes/` (Layer 7)

## Layer Dependencies

```
Layer 8: orchestrator/ → imports from processes/, tasks/, ops/, knowledge/, runtime/, core/
Layer 7: processes/    → imports from tasks/, ops/, knowledge/, runtime/, core/
Layer 6: tasks/        → imports from ops/, knowledge/, runtime/, core/
Layer 5: ops/          → imports from knowledge/, vision/, runtime/, core/
Layer 4: knowledge/    → imports nothing (pure data)
```
```

**src/anime_game_afk/README.md content:**
```markdown
# anime_game_afk — Source Root

Layered game automation framework built on MaaFramework.

## Architecture

```
src/anime_game_afk/
├── core/              # Layer 1: Device adapter (MaaFw wrapper)
├── vision/            # Layer 2: Game-agnostic computer vision
├── runtime/           # Layer 3: Logging, config, state, events, errors
├── config/            # Application configuration models
└── games/
    └── aether_gazer/  # Game-specific layers (4-8)
        ├── knowledge/     # Layer 4: Pure data models
        ├── ops/           # Layer 5: Atomic operations
        ├── tasks/         # Layer 6: Composable tasks
        ├── processes/     # Layer 7: Complete features
        └── orchestrator/  # Layer 8: Pipeline execution
```

## Dependency Rule

Layer N may only import from Layers 0..(N-1).
Game-specific code (Layers 4-8) never imports from another game.
Shared infrastructure (Layers 1-3) is game-agnostic.

## Entry Point

Users run automation via `scripts/run.py`, which loads a YAML plan
and executes the Layer 8 pipeline.
```

---

## Post-Wave Verification Checklist

After all 8 tasks are complete, run these verification steps:

- [ ] All tests pass: `pytest tests/ -v`
- [ ] Type check passes: `python -m mypy src/anime_game_afk/games/aether_gazer/orchestrator/ --ignore-missing-imports`
- [ ] Default plan loads: `python -c "from anime_game_afk.games.aether_gazer.orchestrator.types import load_plan; print(load_plan('src/anime_game_afk/games/aether_gazer/orchestrator/plans/default.yaml'))"`
- [ ] scripts/run.py help works: `python scripts/run.py --help`
- [ ] scripts/run.py dry-run works: `python scripts/run.py --dry-run`
- [ ] scripts/snap.py still works: `python scripts/snap.py --help`
- [ ] Deprecation wrappers fire correctly: `python -c "import warnings; warnings.simplefilter('always'); from anime_game_afk.games.aether_gazer import pages"` should show deprecation warning
- [ ] scripts/ directory contains only: `run.py`, `snap.py`, `debug/`
- [ ] No broken imports from removed modules
- [ ] All README.md files updated to reflect new structure
- [ ] `.claude/memory/` updated with Wave 4 completion notes
