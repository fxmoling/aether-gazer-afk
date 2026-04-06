"""Task manager: bridges the UI to the Pipeline/Process system.

Manages pipeline discovery, task selection state, and execution on a
background thread. Pushes per-task status updates to the frontend.
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

# Imports from existing layers (L8, L6, L3, L1) — UI only adds, never modifies
from anime_game_afk.core.device import DeviceAdapter
from anime_game_afk.core.types import DeviceConfig
from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
from anime_game_afk.games.aether_gazer.orchestrator.pipeline import (
    Pipeline,
    ProcessRegistry,
)
from anime_game_afk.games.aether_gazer.orchestrator.types import (
    PlanConfig,
    ProcessDef,
)
from anime_game_afk.games.aether_gazer.processes.base import ProcessContext
from anime_game_afk.games.aether_gazer.processes.daily_routine import (
    DailyRoutine,
    _DAILY_TASKS,
)
from anime_game_afk.games.aether_gazer.processes.push_main_story import PushMainStory
from anime_game_afk.runtime.logger import get_logger


@dataclass
class TaskState:
    """UI state for a single task within a pipeline."""

    id: str
    name: str
    description: str
    enabled: bool = True
    safe: bool = True
    status: str = "pending"  # pending | running | success | failed | skipped


@dataclass
class PipelineDef:
    """UI representation of a pipeline (process) and its tasks."""

    id: str
    name: str
    description: str
    tasks: list[TaskState] = field(default_factory=list)


# Config file path (relative to project root or cwd)
_CONFIG_PATH = Path("config/ui_state.json")


class TaskManager:
    """Bridges the UI Api to the existing Pipeline/Process system."""

    def __init__(self) -> None:
        self._pipelines: list[PipelineDef] = []
        self._device: DeviceAdapter | None = None
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._window: Any = None  # pywebview window
        self._running = False
        self._start_time: float = 0.0
        self._completed_count = 0
        self._total_count = 0
        self._logger = get_logger("ui.task_manager")

        self._load_pipelines()
        self._load_config()

    def bind_window(self, window: Any) -> None:
        """Bind pywebview window for evaluate_js push."""
        self._window = window

    # ------------------------------------------------------------------
    # Pipeline / task discovery
    # ------------------------------------------------------------------

    def _load_pipelines(self) -> None:
        """Discover available pipelines from the process registry."""
        # daily_routine — build tasks from _DAILY_TASKS
        daily_tasks = []
        for task_id, task_cls in _DAILY_TASKS:
            task_obj = task_cls()
            daily_tasks.append(
                TaskState(
                    id=task_id,
                    name=getattr(task_obj, "description", task_id),
                    description=getattr(task_obj, "description", ""),
                    safe=getattr(task_obj, "safe", True),
                )
            )

        self._pipelines.append(
            PipelineDef(
                id="daily_routine",
                name="日常任务",
                description="完成每日任务：邮件、商店、体力、公会等",
                tasks=daily_tasks,
            )
        )

        # push_main_story — single process, no sub-task toggles for MVP
        self._pipelines.append(
            PipelineDef(
                id="push_main_story",
                name="主线推进",
                description="自动推进主线剧情关卡",
                tasks=[
                    TaskState(
                        id="push_main_story",
                        name="推进主线",
                        description="Clear main story stages sequentially",
                        safe=False,
                    )
                ],
            )
        )

    # ------------------------------------------------------------------
    # Config persistence
    # ------------------------------------------------------------------

    def _load_config(self) -> None:
        """Load task enabled/disabled state from config file."""
        if not _CONFIG_PATH.exists():
            return
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        pipelines_cfg = data.get("pipelines", {})
        for pipeline in self._pipelines:
            pcfg = pipelines_cfg.get(pipeline.id, {})
            tasks_cfg = pcfg.get("tasks", {})
            for task in pipeline.tasks:
                if task.id in tasks_cfg:
                    task.enabled = bool(tasks_cfg[task.id])

    def _save_config(self) -> None:
        """Save task enabled/disabled state to config file (atomic write)."""
        data: dict[str, Any] = {"pipelines": {}}
        for pipeline in self._pipelines:
            data["pipelines"][pipeline.id] = {
                "tasks": {t.id: t.enabled for t in pipeline.tasks}
            }

        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = _CONFIG_PATH.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, _CONFIG_PATH)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_pipelines(self) -> list[dict[str, Any]]:
        """Return all pipelines with their tasks as dicts for JSON."""
        with self._lock:
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "tasks": [
                        {
                            "id": t.id,
                            "name": t.name,
                            "description": t.description,
                            "enabled": t.enabled,
                            "safe": t.safe,
                            "status": t.status,
                        }
                        for t in p.tasks
                    ],
                }
                for p in self._pipelines
            ]

    def set_task_enabled(
        self, pipeline_id: str, task_id: str, enabled: bool
    ) -> bool:
        """Toggle a task's enabled state. Returns True on success."""
        with self._lock:
            pipeline = self._find_pipeline(pipeline_id)
            if not pipeline:
                return False
            for task in pipeline.tasks:
                if task.id == task_id:
                    task.enabled = enabled
                    self._save_config()
                    return True
        return False

    def set_all_enabled(self, pipeline_id: str, enabled: bool) -> bool:
        """Toggle all tasks in a pipeline. Returns True on success."""
        with self._lock:
            pipeline = self._find_pipeline(pipeline_id)
            if not pipeline:
                return False
            for task in pipeline.tasks:
                task.enabled = enabled
            self._save_config()
        return True

    def connect(self) -> dict[str, Any]:
        """Connect to the game window."""
        try:
            config = DeviceConfig(
                window_title=AETHER_GAZER_CONFIG.window_title,
                screencap_method=AETHER_GAZER_CONFIG.screencap_method,
                mouse_method=AETHER_GAZER_CONFIG.mouse_method,
                keyboard_method=AETHER_GAZER_CONFIG.keyboard_method,
                design_resolution=AETHER_GAZER_CONFIG.design_resolution,
            )
            self._device = DeviceAdapter(config=config)
            self._device.connect()
            if not self._device.connected:
                return {"ok": False, "error": "无法连接到游戏窗口，请确认游戏已启动"}
            res = self._device.actual_resolution
            res_str = f"{res.width}x{res.height}" if res else "unknown"
            self._logger.info("已连接到游戏窗口，分辨率: {}", res_str)
            return {"ok": True, "resolution": res_str}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def disconnect(self) -> dict[str, Any]:
        """Disconnect from the game window."""
        if self._device:
            try:
                self._device.disconnect()
            except Exception:
                pass
            self._device = None
        return {"ok": True}

    def get_status(self) -> dict[str, Any]:
        """Get current connection and execution status."""
        elapsed = 0.0
        if self._running and self._start_time > 0:
            elapsed = time.time() - self._start_time
        return {
            "connected": self._device is not None and self._device.connected,
            "running": self._running,
            "elapsed_s": round(elapsed, 1),
            "completed": self._completed_count,
            "total": self._total_count,
        }

    def start(self, pipeline_id: str) -> dict[str, Any]:
        """Start executing a pipeline on a background thread."""
        if self._running:
            return {"ok": False, "error": "已有任务在运行中"}
        if not self._device or not self._device.connected:
            return {"ok": False, "error": "请先连接游戏窗口"}

        pipeline = self._find_pipeline(pipeline_id)
        if not pipeline:
            return {"ok": False, "error": f"未知 pipeline: {pipeline_id}"}

        enabled_tasks = [t for t in pipeline.tasks if t.enabled]
        if not enabled_tasks:
            return {"ok": False, "error": "没有选择任何任务"}

        # Reset task statuses
        with self._lock:
            for task in pipeline.tasks:
                task.status = "pending" if task.enabled else "skipped"

        self._stop_event.clear()
        self._running = True
        self._start_time = time.time()
        self._completed_count = 0
        self._total_count = len(enabled_tasks)

        self._worker = threading.Thread(
            target=self._run_pipeline,
            args=(pipeline,),
            daemon=True,
        )
        self._worker.start()
        return {"ok": True}

    def stop(self) -> dict[str, Any]:
        """Signal the worker thread to stop after the current task."""
        self._stop_event.set()
        self._logger.info("已请求停止，将在当前任务完成后停止")
        return {"ok": True}

    # ------------------------------------------------------------------
    # Background execution
    # ------------------------------------------------------------------

    def _run_pipeline(self, pipeline: PipelineDef) -> None:
        """Run enabled tasks in sequence on the worker thread."""
        try:
            asyncio.run(self._async_run(pipeline))
        except Exception as e:
            self._logger.error("Pipeline 执行异常: {}", e)
        finally:
            self._running = False
            self._push_js("window.onRunComplete && window.onRunComplete()")

    async def _async_run(self, pipeline: PipelineDef) -> None:
        """Async execution loop — runs each enabled task in order."""
        from anime_game_afk.games.aether_gazer.tasks.navigation_tasks import (
            ReturnToHub,
        )

        assert self._device is not None
        hub = ReturnToHub()

        ctx = ProcessContext(
            device=self._device,
            logger=get_logger(f"ui.{pipeline.id}"),
        )

        self._logger.info("=== 开始 {} ===", pipeline.name)

        # Return to hub first
        await hub.execute(ctx)

        for task_def in pipeline.tasks:
            if not task_def.enabled:
                continue

            if self._stop_event.is_set():
                task_def.status = "skipped"
                self._push_task_status(task_def.id, "skipped")
                continue

            # Update status to running
            task_def.status = "running"
            self._push_task_status(task_def.id, "running")
            self._logger.info("--- 执行: {} ---", task_def.name)

            try:
                # Find and instantiate the task class
                task_cls = self._resolve_task_class(pipeline.id, task_def.id)
                if task_cls is None:
                    task_def.status = "failed"
                    self._push_task_status(task_def.id, "failed")
                    self._logger.warning("找不到任务类: {}", task_def.id)
                    continue

                task_obj = task_cls()
                if hasattr(task_obj, "can_run") and not await task_obj.can_run(ctx):
                    task_def.status = "skipped"
                    self._push_task_status(task_def.id, "skipped")
                    self._logger.info("  {} — can_run=False, 跳过", task_def.id)
                else:
                    result = await task_obj.execute(ctx)
                    if result.status == "success":
                        task_def.status = "success"
                        self._push_task_status(task_def.id, "success")
                        self._completed_count += 1
                    elif result.status == "skipped":
                        task_def.status = "skipped"
                        self._push_task_status(task_def.id, "skipped")
                    else:
                        task_def.status = "failed"
                        self._push_task_status(task_def.id, "failed")
                        self._logger.warning(
                            "  {} — 失败: {}", task_def.id, result.message
                        )
            except Exception as e:
                task_def.status = "failed"
                self._push_task_status(task_def.id, "failed")
                self._logger.error("  {} — 异常: {}", task_def.id, e)

            # Return to hub between tasks
            try:
                await hub.execute(ctx)
            except Exception:
                pass

        self._logger.info(
            "=== {} 完成 ({}/{}) ===",
            pipeline.name,
            self._completed_count,
            self._total_count,
        )

    def _resolve_task_class(self, pipeline_id: str, task_id: str) -> Any:
        """Look up the task class for a given pipeline + task ID."""
        if pipeline_id == "daily_routine":
            for tid, cls in _DAILY_TASKS:
                if tid == task_id:
                    return cls
        elif pipeline_id == "push_main_story":
            if task_id == "push_main_story":
                return PushMainStory
        return None

    # ------------------------------------------------------------------
    # Frontend push helpers
    # ------------------------------------------------------------------

    def _push_task_status(self, task_id: str, status: str) -> None:
        """Push a task status update to the frontend (thread-safe)."""
        self._push_js(
            f"window.updateTaskStatus && window.updateTaskStatus("
            f"{json.dumps(task_id)}, {json.dumps(status)})"
        )

    def _push_js(self, js_code: str) -> None:
        """Execute JS in the frontend window (thread-safe)."""
        window = self._window
        if window is not None:
            try:
                window.evaluate_js(js_code)
            except Exception:
                pass  # Window may be closing

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_pipeline(self, pipeline_id: str) -> PipelineDef | None:
        """Find a pipeline by ID."""
        for p in self._pipelines:
            if p.id == pipeline_id:
                return p
        return None
