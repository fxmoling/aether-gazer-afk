"""Subprocess worker entry point for pipeline execution.

Runs as a child process so the parent GUI can ``process.kill()`` it for
reliable stop.  Communicates with the parent via a JSON-line protocol on
stdout; all log output goes to stderr only.

Usage::

    python -m anime_game_afk.ui.worker --pipeline daily_routine \\
        --tasks mail,intel_shards,stamina_packs
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import traceback
from typing import Any


# ---------------------------------------------------------------------------
# JSON-line helpers
# ---------------------------------------------------------------------------

def _emit(obj: dict[str, Any]) -> None:
    """Write a single JSON object as one line to stdout and flush."""
    print(json.dumps(obj, ensure_ascii=False), flush=True)


# ---------------------------------------------------------------------------
# JsonLineListener — translates PipelineListener events to JSON lines
# ---------------------------------------------------------------------------

class JsonLineListener:
    """Implements PipelineListener by emitting JSON lines to stdout."""

    def on_task_status(
        self, task_id: str, status: str, message: str = "",
    ) -> None:
        _emit({"type": "task_status", "id": task_id, "status": status,
               "message": message})

    def on_process_status(
        self, name: str, status: str, message: str = "",
    ) -> None:
        _emit({"type": "process_status", "name": name, "status": status,
               "message": message})

    def on_connected(self, resolution: str) -> None:
        _emit({"type": "connected", "resolution": resolution})

    def on_done(
        self, completed: int, failed: int, elapsed_s: float,
    ) -> None:
        _emit({"type": "done", "completed": completed, "failed": failed,
               "elapsed_s": elapsed_s})


# ---------------------------------------------------------------------------
# Async main loop
# ---------------------------------------------------------------------------

async def _run(pipeline_id: str, enabled_ids: set[str]) -> int:
    """Execute the requested pipeline and stream status to stdout.

    Returns:
        Exit code — 0 for success, 1 for fatal error.
    """
    # Late imports so the module can be parsed even if deps aren't installed.
    from anime_game_afk.core.device import DeviceAdapter
    from anime_game_afk.core.errors import WindowNotFoundError
    from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
    from anime_game_afk.games.aether_gazer.orchestrator.pipeline import Pipeline
    from anime_game_afk.games.aether_gazer.orchestrator.types import (
        PlanConfig,
        ProcessDef,
    )
    from anime_game_afk.games.aether_gazer.processes.base import ProcessContext
    from anime_game_afk.games.aether_gazer.registry import build_registry
    from anime_game_afk.runtime.logger import get_logger

    listener = JsonLineListener()

    # ---- Connect device ---------------------------------------------------
    try:
        device = DeviceAdapter(config=AETHER_GAZER_CONFIG.to_device_config())
        device.connect()
    except WindowNotFoundError:
        _emit({"type": "error", "msg": "Game window not found"})
        return 1
    except Exception as exc:
        _emit({"type": "error", "msg": f"Connection failed: {exc}"})
        return 1

    res = device.actual_resolution
    listener.on_connected(f"{res.width}x{res.height}")

    # ---- Build pipeline ---------------------------------------------------
    registry = build_registry()

    def context_factory(proc_def: ProcessDef) -> ProcessContext:
        return ProcessContext(
            device=device,
            config=proc_def.config,
            listener=listener,
            logger=get_logger(f"worker.{proc_def.name}"),
        )

    pipeline = Pipeline(
        registry=registry,
        device=device,
        context_factory=context_factory,
    )

    # ---- Build plan from CLI args -----------------------------------------
    plan = PlanConfig(
        game="aether_gazer",
        processes=[ProcessDef(
            name=pipeline_id,
            config={"enabled_tasks": sorted(enabled_ids)},
        )],
    )

    # ---- Execute ----------------------------------------------------------
    try:
        result = await pipeline.run(plan)
    except Exception as exc:
        _emit({"type": "error", "msg": f"Pipeline error: {exc}"})
        device.disconnect()
        return 1

    listener.on_done(result.succeeded, result.failed, result.elapsed_s)
    device.disconnect()
    return 0 if not result.aborted and result.failed == 0 else 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Parse CLI arguments, configure logging, and run the async loop."""
    # Line-buffered stdout for real-time JSON streaming
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]

    # Redirect loguru to stderr only (stdout is the JSON protocol channel)
    from loguru import logger

    logger.remove()
    logger.add(
        sys.stderr,
        format="{time:HH:mm:ss} | {level:<7} | {message}",
        level="DEBUG",
    )

    parser = argparse.ArgumentParser(
        description="Subprocess worker for pipeline execution",
    )
    parser.add_argument(
        "--pipeline",
        required=True,
        help="Pipeline ID to execute (e.g. daily_routine)",
    )
    parser.add_argument(
        "--tasks",
        required=True,
        help="Comma-separated list of enabled task IDs",
    )
    args = parser.parse_args()

    enabled_ids = {t.strip() for t in args.tasks.split(",") if t.strip()}

    try:
        exit_code = asyncio.run(_run(args.pipeline, enabled_ids))
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        _emit({"type": "error", "msg": f"Fatal: {exc}"})
        sys.exit(1)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
