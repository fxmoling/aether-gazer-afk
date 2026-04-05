"""Main entry point for AetherGazer automation.

Usage:
    python scripts/run.py
    python scripts/run.py --plan path/to/my_plan.yaml
    python scripts/run.py --plan plans/default.yaml --dry-run
    python scripts/run.py --list
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure src/ is on the import path
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root / "src"))

from anime_game_afk.core.device import DeviceAdapter
from anime_game_afk.core.types import DeviceConfig
from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
from anime_game_afk.games.aether_gazer.orchestrator.pipeline import (
    Pipeline,
    ProcessRegistry,
)
from anime_game_afk.games.aether_gazer.orchestrator.types import ProcessDef, load_plan
from anime_game_afk.games.aether_gazer.processes.base import ProcessContext
from anime_game_afk.games.aether_gazer.processes.daily_routine import DailyRoutine
from anime_game_afk.games.aether_gazer.processes.push_main_story import PushMainStory
from anime_game_afk.runtime.logger import get_logger

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


def _make_device_config() -> DeviceConfig:
    """Convert the game's GameConfig to a DeviceConfig for DeviceAdapter.

    GameConfig lives in config/ (higher layer) while DeviceAdapter lives in
    core/ and accepts only DeviceConfig to avoid layer violations.
    """
    return DeviceConfig(
        window_title=AETHER_GAZER_CONFIG.window_title,
        screencap_method=AETHER_GAZER_CONFIG.screencap_method,
        mouse_method=AETHER_GAZER_CONFIG.mouse_method,
        keyboard_method=AETHER_GAZER_CONFIG.keyboard_method,
        design_resolution=AETHER_GAZER_CONFIG.design_resolution,
    )


def build_registry() -> ProcessRegistry:
    """Register all available processes.

    Each process class is mapped to the name used in YAML plans.
    Add new processes here as they are implemented.
    """
    registry = ProcessRegistry()
    registry.register("daily_routine", DailyRoutine)
    registry.register("push_main_story", PushMainStory)
    # Future processes:
    # registry.register("farm_resources", FarmResources)
    # registry.register("dream_realm", DreamRealm)
    # registry.register("weekly_bosses", WeeklyBosses)
    return registry


def build_context_factory(device: DeviceAdapter):  # type: ignore[return]
    """Create a factory function that builds ProcessContext for each process.

    Args:
        device: Connected DeviceAdapter instance.

    Returns:
        Callable(ProcessDef) -> ProcessContext
    """
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
            "  python scripts/run.py --dry-run                 # Show plan without running\n"
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
    device = DeviceAdapter(config=_make_device_config())
    device.connect()

    if not device.connected:
        logger.error("Failed to connect to game window. Is AetherGazer running?")
        return 1

    logger.info("Connected. Resolution: {res}", res=device.actual_resolution)

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
                print(
                    f"  {d.get('name', '?')}: {d.get('status', '?')} "
                    f"({d.get('elapsed_s', 0):.1f}s)"
                )

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
