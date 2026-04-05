"""Tests for tasks.base — TaskResult, TaskContext, Task protocol."""
import asyncio
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from anime_game_afk.games.aether_gazer.tasks.base import (
    Task,
    TaskContext,
    TaskResult,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext


@dataclass
class MockDevice:
    click_log: list = field(default_factory=list)
    key_log: list = field(default_factory=list)

    def screenshot(self) -> np.ndarray:
        return np.zeros((900, 1600, 3), dtype=np.uint8)
    def click(self, x: int, y: int) -> None:
        self.click_log.append((x, y))
    def press_key(self, vk_code: int) -> None:
        self.key_log.append(vk_code)
    def hold_key(self, vk_code: int, duration_s: float) -> None:
        self.key_log.append((vk_code, duration_s))


def _run(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro)


# --- TaskResult ---

def test_task_result_success():
    r = TaskResult(status="success")
    assert r.status == "success"
    assert r.message == ""
    assert r.data == {}


def test_task_result_failed_with_message():
    r = TaskResult(status="failed", message="oops")
    assert r.status == "failed"
    assert r.message == "oops"


def test_task_result_skipped_with_data():
    r = TaskResult(status="skipped", data={"reason": "no stamina"})
    assert r.status == "skipped"
    assert r.data["reason"] == "no stamina"


# --- TaskContext ---

def test_task_context_is_op_context_subclass():
    """TaskContext must be usable wherever OpContext is expected."""
    device = MockDevice()
    ctx = TaskContext(device=device)
    assert isinstance(ctx, OpContext)


def test_task_context_screenshot():
    """TaskContext inherits screenshot() convenience method."""
    device = MockDevice()
    ctx = TaskContext(device=device)
    img = ctx.screenshot()
    assert img.shape == (900, 1600, 3)


def test_task_context_state_dict():
    device = MockDevice()
    ctx = TaskContext(device=device, state={"stamina": 120})
    assert ctx.state["stamina"] == 120


# --- Task protocol ---

class _SuccessTask:
    """Minimal Task implementation."""
    name = "success_task"

    async def execute(self, ctx: TaskContext) -> TaskResult:
        return TaskResult(status="success")

    async def can_run(self, ctx: TaskContext) -> bool:
        return True


class _SkipTask:
    """Task that always skips."""
    name = "skip_task"

    async def execute(self, ctx: TaskContext) -> TaskResult:
        return TaskResult(status="skipped", message="always skip")

    async def can_run(self, ctx: TaskContext) -> bool:
        return False


def test_task_protocol_isinstance():
    """Any class with name/execute/can_run satisfies Task protocol."""
    task = _SuccessTask()
    assert isinstance(task, Task)


def test_task_execute_success():
    device = MockDevice()
    ctx = TaskContext(device=device)
    result = _run(_SuccessTask().execute(ctx))
    assert result.status == "success"


def test_task_can_run_true():
    device = MockDevice()
    ctx = TaskContext(device=device)
    assert _run(_SuccessTask().can_run(ctx)) is True


def test_task_can_run_false():
    device = MockDevice()
    ctx = TaskContext(device=device)
    assert _run(_SkipTask().can_run(ctx)) is False


def test_task_execute_skipped():
    device = MockDevice()
    ctx = TaskContext(device=device)
    result = _run(_SkipTask().execute(ctx))
    assert result.status == "skipped"
    assert "always skip" in result.message
