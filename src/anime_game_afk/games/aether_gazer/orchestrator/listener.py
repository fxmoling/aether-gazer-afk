"""Pipeline event listener protocol.

Processes fire events through this protocol so that external consumers
(e.g. the subprocess worker) can observe progress without polling.

Usage::

    class MyListener:
        def on_task_status(self, task_id, status, message=""):
            print(f"{task_id}: {status}")
        ...

    ctx = ProcessContext(device=dev, listener=MyListener())
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PipelineListener(Protocol):
    """Observer for pipeline/process/task lifecycle events."""

    def on_task_status(
        self, task_id: str, status: str, message: str = "",
    ) -> None: ...

    def on_process_status(
        self, name: str, status: str, message: str = "",
    ) -> None: ...

    def on_connected(self, resolution: str) -> None: ...

    def on_done(
        self, completed: int, failed: int, elapsed_s: float,
    ) -> None: ...


class NullListener:
    """No-op listener used when no observer is attached."""

    def on_task_status(
        self, task_id: str, status: str, message: str = "",
    ) -> None:
        pass

    def on_process_status(
        self, name: str, status: str, message: str = "",
    ) -> None:
        pass

    def on_connected(self, resolution: str) -> None:
        pass

    def on_done(
        self, completed: int, failed: int, elapsed_s: float,
    ) -> None:
        pass
