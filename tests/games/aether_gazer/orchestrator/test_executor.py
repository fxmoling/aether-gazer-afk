"""Tests for process executor."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from anime_game_afk.core.errors import InfrastructureError
from anime_game_afk.games.aether_gazer.orchestrator.executor import (
    ExecutionRecord,
    ProcessExecutor,
    classify_infra_error,
)
from anime_game_afk.games.aether_gazer.orchestrator.recovery import (
    InfraFailure,
    RecoveryManager,
)
from anime_game_afk.games.aether_gazer.orchestrator.types import ProcessDef


@dataclass
class FakeProcessResult:
    status: str = "success"
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class FakeProcess:
    """Mock process for testing."""

    def __init__(
        self,
        result: FakeProcessResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result or FakeProcessResult()
        self._error = error
        self.execute_count = 0

    async def execute(self, ctx: Any) -> FakeProcessResult:
        self.execute_count += 1
        if self._error is not None:
            raise self._error
        return self._result


class FakeRecovery:
    """Mock recovery manager."""

    def __init__(self, succeeds: bool = True) -> None:
        self._succeeds = succeeds
        self.handle_calls: list[InfraFailure] = []

    async def handle(self, failure: InfraFailure) -> bool:
        self.handle_calls.append(failure)
        return self._succeeds


@pytest.fixture
def recovery() -> FakeRecovery:
    return FakeRecovery()


@pytest.fixture
def executor(recovery: FakeRecovery) -> ProcessExecutor:
    return ProcessExecutor(recovery=recovery)  # type: ignore[arg-type]


class TestClassifyInfraError:
    def test_device_disconnected(self) -> None:
        err = InfrastructureError("device_disconnected: controller lost")
        assert classify_infra_error(err) == InfraFailure.DEVICE_DISCONNECTED

    def test_window_lost(self) -> None:
        err = InfrastructureError("window_lost: HWND invalid")
        assert classify_infra_error(err) == InfraFailure.WINDOW_LOST

    def test_unknown_error(self) -> None:
        err = InfrastructureError("something weird happened")
        assert classify_infra_error(err) is None


class TestExecuteOne:
    @pytest.mark.asyncio
    async def test_successful_process(self, executor: ProcessExecutor) -> None:
        process = FakeProcess(FakeProcessResult(status="success", data={"stages": 5}))
        proc_def = ProcessDef(name="test_process")

        record = await executor.execute_one(process, proc_def, ctx=None)

        assert record.status == "success"
        assert record.process_name == "test_process"
        assert record.elapsed_s >= 0
        assert record.data == {"stages": 5}

    @pytest.mark.asyncio
    async def test_failed_process(self, executor: ProcessExecutor) -> None:
        process = FakeProcess(FakeProcessResult(status="failed", message="no stamina"))
        proc_def = ProcessDef(name="farm")

        record = await executor.execute_one(process, proc_def, ctx=None)

        assert record.status == "failed"
        assert record.infra_failure is None

    @pytest.mark.asyncio
    async def test_infra_error_classified(self, executor: ProcessExecutor) -> None:
        process = FakeProcess(
            error=InfrastructureError("device_disconnected: lost connection")
        )
        proc_def = ProcessDef(name="daily")

        record = await executor.execute_one(process, proc_def, ctx=None)

        assert record.status == "error"
        assert record.infra_failure == InfraFailure.DEVICE_DISCONNECTED

    @pytest.mark.asyncio
    async def test_unexpected_error(self, executor: ProcessExecutor) -> None:
        process = FakeProcess(error=RuntimeError("something broke"))
        proc_def = ProcessDef(name="push")

        record = await executor.execute_one(process, proc_def, ctx=None)

        assert record.status == "error"
        assert record.infra_failure is None
        assert "something broke" in record.message


class TestExecuteAll:
    @pytest.mark.asyncio
    async def test_all_succeed(self, executor: ProcessExecutor) -> None:
        pairs = [
            (FakeProcess(), ProcessDef(name="a"), None),
            (FakeProcess(), ProcessDef(name="b"), None),
            (FakeProcess(), ProcessDef(name="c"), None),
        ]
        records = await executor.execute_all(pairs)

        assert len(records) == 3
        assert all(r.status == "success" for r in records)

    @pytest.mark.asyncio
    async def test_infra_error_triggers_recovery(
        self, recovery: FakeRecovery, executor: ProcessExecutor
    ) -> None:
        # Process that fails once with infra error, then succeeds on retry
        call_count = 0

        async def flaky_execute(ctx: Any) -> FakeProcessResult:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise InfrastructureError("device_disconnected: lost")
            return FakeProcessResult(status="success")

        flaky = FakeProcess()
        flaky.execute = flaky_execute  # type: ignore[method-assign]

        pairs: list[Any] = [
            (flaky, ProcessDef(name="flaky_proc"), None),
            (FakeProcess(), ProcessDef(name="b"), None),
        ]
        await executor.execute_all(pairs)

        assert len(recovery.handle_calls) == 1
        assert recovery.handle_calls[0] == InfraFailure.DEVICE_DISCONNECTED

    @pytest.mark.asyncio
    async def test_unrecoverable_error_aborts(self) -> None:
        bad_recovery = FakeRecovery(succeeds=False)
        local_executor = ProcessExecutor(
            recovery=bad_recovery  # type: ignore[arg-type]
        )

        fail_proc = FakeProcess(
            error=InfrastructureError("window_lost: gone")
        )
        pairs: list[Any] = [
            (fail_proc, ProcessDef(name="a"), None),
            (FakeProcess(), ProcessDef(name="b"), None),  # should not run
        ]
        records = await local_executor.execute_all(pairs)

        # Only the failed process should have a record (b never runs)
        process_names = [r.process_name for r in records]
        assert "a" in process_names
        assert "b" not in process_names
