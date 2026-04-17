"""Main entry point for AetherGazer automation.

Usage:
    python scripts/run.py
    python scripts/run.py --plan path/to/my_plan.yaml
    python scripts/run.py --plan plans/default.yaml --dry-run
    python scripts/run.py --list
    python scripts/run.py --launch     # Launch game + reach hub, then exit
    python scripts/run.py --no-launch  # Skip game launch, assume already running
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure src/ is on the import path
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root / "src"))

from anime_game_afk.config.user_config import UserConfig
from anime_game_afk.core.device import DeviceAdapter
from anime_game_afk.core.game_finder import find_aether_gazer
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
from anime_game_afk.games.aether_gazer.tasks.startup_tasks import (
    LaunchAndReachHub,
    ensure_game_running,
)
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
    """Convert the game's GameConfig to a DeviceConfig for DeviceAdapter."""
    return AETHER_GAZER_CONFIG.to_device_config()


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
            "  python scripts/run.py --launch                  # Launch game + reach hub\n"
            "  python scripts/run.py --no-launch               # Skip game launch\n"
            "  python scripts/run.py --detect-game             # Auto-detect game path\n"
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
    parser.add_argument(
        "--launch",
        action="store_true",
        default=False,
        help="Launch game before connecting (auto-detect or use config path)",
    )
    parser.add_argument(
        "--no-launch",
        action="store_true",
        default=False,
        help="Skip game launch, assume already running",
    )
    parser.add_argument(
        "--detect-game",
        action="store_true",
        default=False,
        help="Auto-detect game installation and save to config, then exit",
    )
    return parser.parse_args()


def _resolve_game_exe(user_cfg: UserConfig) -> str | None:
    """Resolve the game exe path from user config or auto-detection.

    If the config has a path and it exists, use it.
    Otherwise, auto-detect and save to config.

    Returns:
        Path to game exe, or None if not found.
    """
    game_id = "aether_gazer"
    exe_path = user_cfg.game_exe_path(game_id)

    # Check if configured path is still valid
    if exe_path and Path(exe_path).exists():
        logger.info("Using configured game path: {path}", path=exe_path)
        return exe_path

    # Auto-detect
    if not user_cfg.auto_detect_games():
        logger.warning("auto_detect_games is disabled and no valid path configured")
        return None

    logger.info("Auto-detecting AetherGazer installation...")
    result = find_aether_gazer(
        search_drives=user_cfg.search_drives(),
    )

    if result["game_exe"]:
        user_cfg.set_game_exe_path(game_id, result["game_exe"])
        if result["launcher"]:
            user_cfg.set_launcher_path(game_id, result["launcher"])
        user_cfg.save()
        logger.info(
            "Auto-detected and saved: game={game}, launcher={launcher}",
            game=result["game_exe"],
            launcher=result.get("launcher", ""),
        )
        return result["game_exe"]

    logger.error(
        "Could not auto-detect AetherGazer. "
        "Please set game_exe_path in config/user_config.yaml"
    )
    return None


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

    # Load user config
    user_cfg = UserConfig.load()

    # Detect-game mode: find game and save to config
    if args.detect_game:
        exe_path = _resolve_game_exe(user_cfg)
        if exe_path:
            print(f"Game exe: {exe_path}")
            launcher = user_cfg.launcher_path("aether_gazer")
            if launcher:
                print(f"Launcher: {launcher}")
            print(f"Config saved to: {user_cfg.path}")
            return 0
        else:
            print("ERROR: Could not find AetherGazer installation.")
            print("Please set game_exe_path manually in config/user_config.yaml")
            return 1

    # Phase 1: Ensure game is running (unless --no-launch)
    if args.launch and not args.no_launch:
        exe_path = _resolve_game_exe(user_cfg)
        if not exe_path:
            logger.error(
                "Cannot launch: game exe not found. "
                "Run with --detect-game first, or set path in config."
            )
            return 1

        timeout = user_cfg.launch_timeout("aether_gazer")
        logger.info("Phase 1: Ensuring game is running...")
        if not ensure_game_running(
            exe_path=exe_path,
            window_title=user_cfg.window_title("aether_gazer") or "AetherGazer",
            timeout=timeout,
        ):
            logger.error("Failed to launch game within {t}s", t=timeout)
            return 1
        logger.info("Phase 1: Game is running")

    # Connect to game
    logger.info("Connecting to AetherGazer...")
    device = DeviceAdapter(config=_make_device_config())
    try:
        device.connect()
    except Exception as exc:
        logger.error("Failed to connect: {exc}", exc=str(exc))
        if not args.no_launch:
            logger.info(
                "Hint: If the game is not running, use --launch to start it."
            )
        return 1

    if not device.connected:
        logger.error("Failed to connect to game window. Is AetherGazer running?")
        return 1

    logger.info("Connected. Resolution: {res}", res=device.actual_resolution)

    try:
        # Phase 2: Skip startup popups if launching
        if args.launch and not args.no_launch:
            logger.info("Phase 2: Skipping startup popups...")
            from anime_game_afk.games.aether_gazer.tasks.base import TaskContext
            ctx = TaskContext(device=device, logger=logger)
            launch_task = LaunchAndReachHub(
                max_popup_attempts=user_cfg.popup_dismiss_max_attempts("aether_gazer"),
            )
            launch_result = await launch_task.execute(ctx)
            if launch_result.status != "success":
                logger.error(
                    "Failed to reach hub: {msg}", msg=launch_result.message
                )
                return 1
            logger.info("Phase 2: Hub reached successfully")

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
