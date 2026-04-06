"""API class exposed to the frontend via pywebview js_api.

All public methods are callable from JavaScript as:
    const result = await pywebview.api.method_name(args...)

Return values must be JSON-serializable (dict, list, str, int, bool, None).
"""
from __future__ import annotations

from typing import Any

from anime_game_afk.ui.bridge import LogForwarder
from anime_game_afk.ui.task_manager import TaskManager


class Api:
    """JavaScript-callable API for the automation GUI."""

    def __init__(
        self, task_manager: TaskManager, log_forwarder: LogForwarder
    ) -> None:
        self._tm = task_manager
        self._lf = log_forwarder

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> dict[str, Any]:
        """Connect to the game window."""
        return self._tm.connect()

    def disconnect(self) -> dict[str, Any]:
        """Disconnect from the game window."""
        return self._tm.disconnect()

    def get_status(self) -> dict[str, Any]:
        """Get current connection and execution status."""
        return self._tm.get_status()

    # ------------------------------------------------------------------
    # Pipelines & tasks
    # ------------------------------------------------------------------

    def get_pipelines(self) -> list[dict[str, Any]]:
        """Get all available pipelines and their tasks."""
        return self._tm.get_pipelines()

    def set_task_enabled(
        self, pipeline_id: str, task_id: str, enabled: bool
    ) -> dict[str, Any]:
        """Toggle a task's enabled state within a pipeline."""
        ok = self._tm.set_task_enabled(pipeline_id, task_id, enabled)
        return {"ok": ok}

    def set_all_enabled(
        self, pipeline_id: str, enabled: bool
    ) -> dict[str, Any]:
        """Toggle all tasks in a pipeline."""
        ok = self._tm.set_all_enabled(pipeline_id, enabled)
        return {"ok": ok}

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def start_run(self, pipeline_id: str) -> dict[str, Any]:
        """Start executing the selected pipeline."""
        return self._tm.start(pipeline_id)

    def stop_run(self) -> dict[str, Any]:
        """Stop execution after the current task completes."""
        return self._tm.stop()

    # ------------------------------------------------------------------
    # Logs
    # ------------------------------------------------------------------

    def get_recent_logs(self, count: int = 200) -> list[dict[str, str]]:
        """Get recent log entries from the ring buffer."""
        return self._lf.get_recent(count)
