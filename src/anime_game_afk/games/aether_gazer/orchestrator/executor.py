"""Process executor with timing, logging, and error handling.

Runs processes one at a time. Each process gets its own timing context
and structured log output. Errors are caught, classified, and reported
back to the pipeline for recovery decisions.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from anime_game_afk.core.errors import InfrastructureError
from anime_game_afk.games.aether_gazer.orchestrator.recovery import (
    InfraFailure,
    RecoveryManager,
)
from anime_game_afk.games.aether_gazer.orchestrator.types import ProcessDef
from anime_game_afk.runtime.logger import get_logger

logger = get_logger("orchestrator.executor")


# Map exception types/messages to InfraFailure categories
_INFRA_ERROR_MAP: dict[str, InfraFailure] = {
    "device_disconnected": InfraFailure.DEVICE_DISCONNECTED,
    "window_lost": InfraFailure.WINDOW_LOST,
    "screenshot_timeout": InfraFailure.SCREENSHOT_TIMEOUT,
    "game_crash": InfraFailure.GAME_CRASH,
    "session_expired": InfraFailure.SESSION_EXPIRED,
}


@dataclass
class ExecutionRecord:
    """Result of executing a single process.

    Attributes:
        process_name: Name of the process that ran.
        status: One of "success", "failed", "error", "recovered".
        elapsed_s: Wall-clock time in seconds.
        message: Human-readable result summary.
        data: Process-specific output data.
        infra_failure: If an infrastructure failure occurred, its type.
    """
    process_name: str
    status: str
    elapsed_s: float = 0.0
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    infra_failure: InfraFailure | None = None


def classify_infra_error(error: InfrastructureError) -> InfraFailure | None:
    """Classify an InfrastructureError into an InfraFailure category.

    Args:
        error: The caught InfrastructureError.

    Returns:
        Matching InfraFailure or None if unclassifiable.
    """
    error_msg = str(error).lower()
    for keyword, failure in _INFRA_ERROR_MAP.items():
        if keyword in error_msg:
            logger.debug(
                "Classified infra error as {failure}: {msg}",
                failure=failure.value,
                msg=error_msg,
            )
            return failure
    logger.debug("Unclassifiable infra error: {msg}", msg=error_msg)
    return None


class ProcessExecutor:
    """Execute processes with timing, logging, and error classification.

    This class does NOT handle recovery directly. It catches errors,
    classifies them, and returns structured records. The Pipeline
    decides whether to attempt recovery.
    """

    def __init__(self, recovery: RecoveryManager) -> None:
        self._recovery = recovery

    async def execute_one(
        self,
        process: Any,
        proc_def: ProcessDef,
        ctx: Any,
    ) -> ExecutionRecord:
        """Execute a single process with timing and error handling.

        Args:
            process: A Process instance with an async execute(ctx) method.
            proc_def: The ProcessDef from the user plan (for metadata).
            ctx: ProcessContext to pass to process.execute().

        Returns:
            ExecutionRecord with status, timing, and any error info.
        """
        logger.info("Starting process: {name}", name=proc_def.name)
        logger.debug(
            "Process {name} config: {config}",
            name=proc_def.name,
            config=proc_def.config,
        )
        start = time.monotonic()

        try:
            result = await process.execute(ctx)
            elapsed = time.monotonic() - start

            record = ExecutionRecord(
                process_name=proc_def.name,
                status=result.status,
                elapsed_s=elapsed,
                message=result.message if hasattr(result, "message") else "",
                data=result.data if hasattr(result, "data") else {},
            )
            logger.info(
                "Process {name} completed: status={status} in {elapsed:.1f}s",
                name=proc_def.name,
                status=record.status,
                elapsed=elapsed,
            )
            return record

        except InfrastructureError as e:
            elapsed = time.monotonic() - start
            failure = classify_infra_error(e)
            logger.error(
                "Process {name} hit infrastructure error after {elapsed:.1f}s: {err}",
                name=proc_def.name,
                elapsed=elapsed,
                err=str(e),
            )
            return ExecutionRecord(
                process_name=proc_def.name,
                status="error",
                elapsed_s=elapsed,
                message=f"Infrastructure error: {e}",
                infra_failure=failure,
            )

        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error(
                "Process {name} raised unexpected error after {elapsed:.1f}s: {err}",
                name=proc_def.name,
                elapsed=elapsed,
                err=str(e),
            )
            return ExecutionRecord(
                process_name=proc_def.name,
                status="error",
                elapsed_s=elapsed,
                message=f"Unexpected error: {e}",
            )

    async def execute_all(
        self,
        process_pairs: list[tuple[Any, ProcessDef, Any]],
    ) -> list[ExecutionRecord]:
        """Execute a list of processes sequentially.

        Attempts recovery on infrastructure failures. If recovery succeeds,
        retries the failed process once. If recovery fails, stops execution.

        Args:
            process_pairs: List of (process_instance, proc_def, ctx) tuples.

        Returns:
            List of ExecutionRecords, one per attempted process.
        """
        records: list[ExecutionRecord] = []
        logger.info(
            "Executing {count} processes sequentially",
            count=len(process_pairs),
        )

        for process, proc_def, ctx in process_pairs:
            record = await self.execute_one(process, proc_def, ctx)
            records.append(record)

            # If infrastructure error, attempt recovery
            if record.infra_failure is not None:
                recovered = await self._recovery.handle(record.infra_failure)
                if recovered:
                    logger.info(
                        "Recovery succeeded. Retrying process {name}...",
                        name=proc_def.name,
                    )
                    retry_record = await self.execute_one(process, proc_def, ctx)
                    retry_record.status = (
                        "recovered"
                        if retry_record.status == "success"
                        else retry_record.status
                    )
                    records.append(retry_record)
                    # If retry also failed with infra error, abort
                    if retry_record.infra_failure is not None:
                        logger.error("Retry also failed with infra error. Aborting.")
                        break
                else:
                    logger.error(
                        "Recovery failed for {failure}. Aborting pipeline.",
                        failure=record.infra_failure.value,
                    )
                    break

        succeeded = sum(1 for r in records if r.status in ("success", "recovered"))
        failed = sum(1 for r in records if r.status in ("failed", "error"))
        logger.info(
            "Execution batch done: {succeeded} succeeded, {failed} failed, "
            "{recovered} recovered out of {total} attempts",
            succeeded=succeeded,
            failed=failed,
            recovered=sum(1 for r in records if r.status == "recovered"),
            total=len(records),
        )
        return records
