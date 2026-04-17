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
import time
import traceback
from typing import Any


# ---------------------------------------------------------------------------
# JSON-line helpers
# ---------------------------------------------------------------------------

def _emit(obj: dict[str, Any]) -> None:
    """Write a single JSON object as one line to stdout and flush."""
    print(json.dumps(obj, ensure_ascii=False), flush=True)


# ---------------------------------------------------------------------------
# Async main loop
# ---------------------------------------------------------------------------

async def _run(pipeline_id: str, enabled_ids: set[str]) -> int:
    """Execute the requested pipeline tasks and stream status to stdout.

    Returns:
        Exit code — 0 for success, 1 for fatal error.
    """
    # Late imports so the module can be parsed even if deps aren't installed.
    from anime_game_afk.core.device import DeviceAdapter
    from anime_game_afk.core.errors import WindowNotFoundError
    from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
    from anime_game_afk.games.aether_gazer.processes.base import ProcessContext
    from anime_game_afk.games.aether_gazer.processes.daily_routine import (
        _DAILY_TASKS,
    )
    from anime_game_afk.games.aether_gazer.tasks.navigation_tasks import (
        ReturnToHub,
    )
    from anime_game_afk.runtime.logger import get_logger

    t0 = time.monotonic()
    completed = 0
    failed = 0

    # ---- Connect device ---------------------------------------------------
    try:
        device = DeviceAdapter(config=AETHER_GAZER_CONFIG.to_device_config())
        device.connect()
    except WindowNotFoundError as exc:
        return 1
    except Exception as exc:
        _emit({"type": "error", "msg": f"Connection failed: {exc}"})
        return 1

    res = device.actual_resolution
    _emit({
        "type": "connected",
        "resolution": f"{res.width}x{res.height}",
    })

    # ---- Build context ----------------------------------------------------
    ctx = ProcessContext(
        device=device,
        logger=get_logger(f"worker.{pipeline_id}"),
    )
    hub = ReturnToHub()

    # Initial return-to-hub
    try:
        await hub.execute(ctx)
    except Exception:
        pass  # best-effort; tasks will fail if hub unreachable

    # ---- Execute tasks in _DAILY_TASKS order ------------------------------
    if pipeline_id != "daily_routine":
        _emit({"type": "error", "msg": f"Unknown pipeline: {pipeline_id}"})
        return 1

    for task_id, task_cls in _DAILY_TASKS:
        if task_id not in enabled_ids:
            continue

        # Signal "running"
        _emit({"type": "task_status", "id": task_id, "status": "running"})

        try:
            task_obj = task_cls()

            # Check can_run gate
            if hasattr(task_obj, "can_run") and not await task_obj.can_run(ctx):
                _emit({
                    "type": "task_status",
                    "id": task_id,
                    "status": "skipped",
                    "message": "can_run returned False",
                })
                # Still return to hub after skip
                try:
                    await hub.execute(ctx)
                except Exception:
                    pass
                continue

            # Execute the task
            result = await task_obj.execute(ctx)

            if result.status == "success":
                completed += 1
                _emit({
                    "type": "task_status",
                    "id": task_id,
                    "status": "success",
                    "message": result.message or "ok",
                })
            elif result.status == "skipped":
                _emit({
                    "type": "task_status",
                    "id": task_id,
                    "status": "skipped",
                    "message": result.message or "skipped",
                })
            else:
                failed += 1
                _emit({
                    "type": "task_status",
                    "id": task_id,
                    "status": "failed",
                    "message": result.message or "unknown error",
                })

        except Exception as exc:
            failed += 1
            _emit({
                "type": "task_status",
                "id": task_id,
                "status": "failed",
                "message": str(exc),
            })

        # Return to hub between tasks
        try:
            await hub.execute(ctx)
        except Exception:
            pass

    # ---- Done -------------------------------------------------------------
    elapsed = round(time.monotonic() - t0, 1)
    _emit({
        "type": "done",
        "completed": completed,
        "failed": failed,
        "elapsed_s": elapsed,
    })
    return 0


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
        # Uncaught exception — traceback to stderr, JSON error to stdout
        traceback.print_exc(file=sys.stderr)
        _emit({"type": "error", "msg": f"Fatal: {exc}"})
        sys.exit(1)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
