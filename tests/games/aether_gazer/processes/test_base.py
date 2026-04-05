"""Tests for processes.base — ProcessResult, ProcessContext, Process protocol."""
import asyncio
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from anime_game_afk.games.aether_gazer.processes.base import (
    Process,
    ProcessContext,
    ProcessResult,
)
from anime_game_afk.games.aether_gazer.tasks_v2.base import TaskContext
from anime_game_afk.games.aether_gazer.ops.base import OpContext


@dataclass
class MockDevice:
    def screenshot(self) -> np.ndarray:
        return np.zeros((900, 1600, 3), dtype=np.uint8)
    def click(self, x: int, y: int) -> None: ...
    def press_key(self, vk_code: int) -> None: ...
    def hold_key(self, vk_code: int, duration_s: float) -> None: ...


def _run(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro)


# --- ProcessResult ---

def test_process_result_success():
    r = ProcessResult(status="success")
    assert r.status == "success"
    assert r.message == ""
    assert r.data == {}


def test_process_result_failed_with_message():
    r = ProcessResult(status="failed", message="abort")
    assert r.status == "failed"
    assert r.message == "abort"


def test_process_result_data():
    r = ProcessResult(status="success", data={"stages_cleared": 3})
    assert r.data["stages_cleared"] == 3


# --- ProcessContext ---

def test_process_context_is_task_context():
    """ProcessContext must be usable where TaskContext is expected."""
    device = MockDevice()
    ctx = ProcessContext(device=device)
    assert isinstance(ctx, TaskContext)


def test_process_context_is_op_context():
    """ProcessContext inherits from OpContext via TaskContext."""
    device = MockDevice()
    ctx = ProcessContext(device=device)
    assert isinstance(ctx, OpContext)


def test_process_context_config_default_empty():
    device = MockDevice()
    ctx = ProcessContext(device=device)
    assert ctx.config == {}


def test_process_context_config_custom():
    device = MockDevice()
    ctx = ProcessContext(device=device, config={"max_stages": 5})
    assert ctx.config["max_stages"] == 5


def test_process_context_screenshot():
    device = MockDevice()
    ctx = ProcessContext(device=device)
    img = ctx.screenshot()
    assert img.shape == (900, 1600, 3)


# --- Process protocol ---

class _SuccessProcess:
    """Minimal Process implementation."""
    name = "success_process"
    description = "Always succeeds"

    async def execute(self, ctx: ProcessContext) -> ProcessResult:
        return ProcessResult(status="success")


def test_process_protocol_isinstance():
    proc = _SuccessProcess()
    assert isinstance(proc, Process)


def test_process_execute():
    device = MockDevice()
    ctx = ProcessContext(device=device)
    result = _run(_SuccessProcess().execute(ctx))
    assert result.status == "success"


def test_process_context_state_inherited():
    """ProcessContext inherits state dict from OpContext."""
    device = MockDevice()
    ctx = ProcessContext(device=device, state={"stamina": 100})
    assert ctx.state["stamina"] == 100
