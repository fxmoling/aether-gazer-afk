"""Task manager: bridges the UI to the Pipeline/Process system.

Manages pipeline discovery, task selection state, and execution on a
background thread. Pushes per-task status updates to the frontend.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

# Imports from existing layers (L6, L3, L1) — UI only adds, never modifies
from anime_game_afk.core.device import DeviceAdapter
from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
from anime_game_afk.games.aether_gazer.registry import build_registry
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
        self._process: subprocess.Popen | None = None
        self._reader: threading.Thread | None = None
        self._stderr_reader: threading.Thread | None = None
        self._lock = threading.Lock()
        self._window: Any = None  # pywebview window
        self._running = False
        self._start_time: float = 0.0
        self._completed_count = 0
        self._total_count = 0
        self._logger = get_logger("ui.task_manager")
        # Verify-then-release: no persistent device
        self._game_verified = False
        self._resolution: str | None = None

        self._load_pipelines()
        self._load_config()

    def bind_window(self, window: Any) -> None:
        """Bind pywebview window for evaluate_js push."""
        self._window = window

    # ------------------------------------------------------------------
    # Pipeline / task discovery
    # ------------------------------------------------------------------

    def _load_pipelines(self) -> None:
        """Discover available pipelines from the shared ProcessRegistry."""
        registry = build_registry()

        for name in registry.available():
            factory = registry.get_factory(name)

            # Build task list from process metadata
            tasks: list[TaskState] = []
            if hasattr(factory, "task_defs"):
                for td in factory.task_defs():
                    tasks.append(TaskState(
                        id=td["id"],
                        name=td.get("name", td["id"]),
                        description=td.get("description", ""),
                        safe=td.get("safe", True),
                    ))

            self._pipelines.append(PipelineDef(
                id=name,
                name=getattr(factory, "name", name),
                description=getattr(factory, "description", ""),
                tasks=tasks,
            ))

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
        """Verify game window is accessible. Connect, get info, release."""
        try:
            device = DeviceAdapter(
                config=AETHER_GAZER_CONFIG.to_device_config(),
            )
            device.connect()
            if not device.connected:
                return {"ok": False, "error": "无法连接到游戏窗口，请确认游戏已启动"}
            res = device.actual_resolution
            res_str = f"{res.width}x{res.height}" if res else "unknown"
            device.disconnect()  # Release immediately — worker owns real connection
            self._game_verified = True
            self._resolution = res_str
            self._logger.info("游戏窗口已验证，分辨率: {}", res_str)
            return {"ok": True, "resolution": res_str}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def disconnect(self) -> dict[str, Any]:
        """Reset verified state."""
        self._game_verified = False
        self._resolution = None
        return {"ok": True}

    def get_status(self) -> dict[str, Any]:
        """Get current connection and execution status."""
        elapsed = 0.0
        if self._running and self._start_time > 0:
            elapsed = time.time() - self._start_time
        return {
            "connected": self._game_verified,
            "running": self._running,
            "elapsed_s": round(elapsed, 1),
            "completed": self._completed_count,
            "total": self._total_count,
        }

    def start(self, pipeline_id: str) -> dict[str, Any]:
        """Start executing a pipeline.

        In frozen mode, runs in-process (background thread) to avoid
        DLL loading issues with PyInstaller subprocess.
        In dev mode, uses subprocess for easy kill support.
        """
        if self._running:
            return {"ok": False, "error": "已有任务在运行中"}

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

        enabled = [t.id for t in pipeline.tasks if t.enabled]
        enabled_ids = set(enabled)

        self._running = True
        self._start_time = time.time()
        self._completed_count = 0
        self._total_count = len(enabled_tasks)

        if getattr(sys, "frozen", False):
            # Frozen: use subprocess with _MEIPASS passed via environment
            env = os.environ.copy()
            env["_MEIPASS"] = str(sys._MEIPASS)  # type: ignore[attr-defined]
            cmd = [sys.executable, "--worker",
                   "--pipeline", pipeline_id,
                   "--tasks", ",".join(enabled)]
        else:
            env = None
            cmd = [sys.executable, "-m", "anime_game_afk.ui.worker",
                   "--pipeline", pipeline_id,
                   "--tasks", ",".join(enabled)]

        self._process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env=env,
        )
        self._reader = threading.Thread(
            target=self._read_worker_output, daemon=True
        )
        self._reader.start()
        self._stderr_reader = threading.Thread(
            target=self._read_worker_stderr, daemon=True
        )
        self._stderr_reader.start()

        return {"ok": True}

    def stop(self) -> dict[str, Any]:
        """Stop execution."""
        # Subprocess mode
        proc = self._process
        if proc and proc.poll() is None:
            proc.kill()
            try:
                proc.wait(timeout=5)
            except Exception:
                pass
        # Reset any "running" tasks to "stopped"
        with self._lock:
            for p in self._pipelines:
                for t in p.tasks:
                    if t.status == "running":
                        t.status = "failed"
                        self._push_task_status(t.id, "failed")
        self._logger.info("已请求停止")
        return {"ok": True}

    # ------------------------------------------------------------------
    # Worker subprocess I/O
    # ------------------------------------------------------------------

    def _read_worker_output(self) -> None:
        """Reader thread: consume worker stdout JSON lines, push to frontend."""
        proc = self._process
        if proc is None or proc.stdout is None:
            return
        try:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type")

                if msg_type == "task_status":
                    task_id = msg.get("id", "")
                    status = msg.get("status", "")
                    with self._lock:
                        for p in self._pipelines:
                            for t in p.tasks:
                                if t.id == task_id:
                                    t.status = status
                    self._push_task_status(task_id, status)
                    if status == "success":
                        self._completed_count += 1

                elif msg_type == "connected":
                    res_str = msg.get("resolution", "")
                    self._game_verified = True
                    self._resolution = res_str
                    self._push_js(
                        f"window.onConnected && window.onConnected("
                        f"{json.dumps(res_str)})"
                    )

                elif msg_type == "status":
                    status_msg = msg.get("msg", "")
                    self._push_js(
                        f"window.onStatusMsg && window.onStatusMsg("
                        f"{json.dumps(status_msg)})"
                    )

                elif msg_type == "log":
                    level = msg.get("level", "info")
                    text = msg.get("msg", "")
                    self._push_js(
                        f"window.onLog && window.onLog("
                        f"{json.dumps(level)}, {json.dumps(text)})"
                    )

                elif msg_type == "error":
                    err = msg.get("msg", "unknown error")
                    self._push_js(
                        f"window.onError && window.onError({json.dumps(err)})"
                    )

                elif msg_type == "done":
                    pass  # completion signalled by EOF / _running=False below

        finally:
            self._running = False
            self._game_verified = False
            self._resolution = None
            # Check if worker crashed (non-zero exit code)
            proc = self._process
            if proc is not None:
                try:
                    proc.wait(timeout=2)
                except Exception:
                    pass
                if proc.returncode and proc.returncode != 0:
                    # Try to capture any remaining stderr
                    err_msg = ""
                    if proc.stderr:
                        try:
                            remaining = proc.stderr.read()
                            if remaining:
                                err_msg = remaining.strip().split('\n')[-1]
                        except Exception:
                            pass
                    if not err_msg:
                        err_msg = f"Worker 进程异常退出 (code {proc.returncode})"
                    self._logger.error("Worker crashed: {}", err_msg)
                    self._push_js(
                        f"window.onError && window.onError({json.dumps(err_msg)})"
                    )
            self._push_js("window.onRunComplete && window.onRunComplete()")

    def _read_worker_stderr(self) -> None:
        """Stderr reader thread: forward worker log lines to host logger."""
        proc = self._process
        if proc is None or proc.stderr is None:
            return
        try:
            for line in proc.stderr:
                line = line.rstrip()
                if line:
                    self._logger.debug("[worker] {}", line)
        except Exception:
            pass

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
