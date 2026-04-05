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
