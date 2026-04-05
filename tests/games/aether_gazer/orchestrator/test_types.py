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
