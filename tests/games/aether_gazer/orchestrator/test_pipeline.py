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
        local_pipeline = Pipeline(
            registry=reg,
            device=device,
            context_factory=lambda pd: None,
        )

        plan = PlanConfig(
            game="aether_gazer",
            processes=[ProcessDef(name="fail_proc", enabled=True)],
        )
        result = await local_pipeline.run(plan)

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
