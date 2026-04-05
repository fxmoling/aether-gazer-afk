"""Main pipeline: load plan, resolve processes, execute.

The Pipeline is the single entry point for running automation.
External code (scripts/run.py) creates a Pipeline and calls run().
"""
from __future__ import annotations

import time
from typing import Any

from anime_game_afk.games.aether_gazer.orchestrator.executor import (
    ExecutionRecord,
    ProcessExecutor,
)
from anime_game_afk.games.aether_gazer.orchestrator.recovery import RecoveryManager
from anime_game_afk.games.aether_gazer.orchestrator.types import (
    PipelineResult,
    PlanConfig,
    ProcessDef,
    load_plan,
)
from anime_game_afk.runtime.logger import get_logger

logger = get_logger("orchestrator.pipeline")


class ProcessRegistry:
    """Maps process names to process factory functions.

    Processes register themselves here. The pipeline looks up
    process names from the user plan and instantiates them.
    """

    def __init__(self) -> None:
        self._factories: dict[str, Any] = {}

    def register(self, name: str, factory: Any) -> None:
        """Register a process factory by name.

        Args:
            name: Process name as it appears in the YAML plan.
            factory: Callable that returns a Process instance.
        """
        self._factories[name] = factory
        logger.debug("Registered process: {name}", name=name)

    def create(self, name: str) -> Any:
        """Create a process instance by name.

        Args:
            name: Process name from the YAML plan.

        Returns:
            A Process instance.

        Raises:
            KeyError: If the process name is not registered.
        """
        if name not in self._factories:
            available = ", ".join(sorted(self._factories.keys()))
            raise KeyError(
                f"Unknown process '{name}'. Available: [{available}]"
            )
        return self._factories[name]()

    def available(self) -> list[str]:
        """Return sorted list of registered process names."""
        return sorted(self._factories.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._factories


class Pipeline:
    """Top-level orchestrator. Loads a plan and executes processes.

    Usage::

        registry = ProcessRegistry()
        registry.register("daily_routine", DailyRoutine)
        registry.register("push_main_story", PushMainStory)

        pipeline = Pipeline(
            registry=registry,
            device=device_adapter,
            context_factory=build_process_context,
        )
        result = await pipeline.run("plans/my_plan.yaml")
    """

    def __init__(
        self,
        registry: ProcessRegistry,
        device: Any,
        context_factory: Any,
    ) -> None:
        """Initialize the pipeline.

        Args:
            registry: ProcessRegistry with registered process factories.
            device: DeviceAdapter instance for device interaction.
            context_factory: Callable(proc_def) -> ProcessContext.
                             Builds a context for each process from its config.
        """
        self._registry = registry
        self._device = device
        self._context_factory = context_factory
        self._recovery = RecoveryManager(device=device)
        self._executor = ProcessExecutor(recovery=self._recovery)

    async def run(self, plan_source: Any) -> PipelineResult:
        """Load a plan and execute all enabled processes.

        Args:
            plan_source: Path to YAML file, or a dict / PlanConfig.

        Returns:
            PipelineResult with execution summary.
        """
        # Load plan
        if isinstance(plan_source, PlanConfig):
            plan = plan_source
        else:
            plan = load_plan(plan_source)

        enabled = plan.enabled_processes
        total = len(plan.processes)
        skipped = total - len(enabled)

        logger.info(
            "Pipeline starting: {enabled}/{total} processes enabled",
            enabled=len(enabled),
            total=total,
        )

        # Validate all process names before starting
        unknown = [p.name for p in enabled if p.name not in self._registry]
        if unknown:
            logger.error(
                "Unknown processes in plan: {unknown}. Available: {available}",
                unknown=unknown,
                available=self._registry.available(),
            )
            return PipelineResult(
                total=len(enabled),
                failed=len(enabled),
                skipped=skipped,
                aborted=True,
                details=[{"error": f"Unknown processes: {unknown}"}],
            )

        # Build (process, proc_def, ctx) tuples
        process_pairs: list[tuple[Any, ProcessDef, Any]] = []
        for proc_def in enabled:
            process = self._registry.create(proc_def.name)
            ctx = self._context_factory(proc_def)
            process_pairs.append((process, proc_def, ctx))

        # Execute
        start = time.monotonic()
        records = await self._executor.execute_all(process_pairs)
        elapsed = time.monotonic() - start

        # Aggregate results
        result = self._aggregate(records, skipped, elapsed)

        logger.info(
            "Pipeline complete: {succeeded}/{total} succeeded, "
            "{failed} failed, {skipped} skipped in {elapsed:.1f}s",
            succeeded=result.succeeded,
            total=result.total,
            failed=result.failed,
            skipped=result.skipped,
            elapsed=result.elapsed_s,
        )

        return result

    def _aggregate(
        self,
        records: list[ExecutionRecord],
        skipped: int,
        elapsed: float,
    ) -> PipelineResult:
        """Aggregate execution records into a PipelineResult.

        Args:
            records: List of per-process execution records.
            skipped: Number of processes skipped (disabled in plan).
            elapsed: Total wall-clock time in seconds.

        Returns:
            Aggregated PipelineResult.
        """
        aborted = any(
            r.infra_failure is not None and r.status == "error" for r in records
        )

        # Deduplicate: if a process was retried after recovery,
        # keep only the final (most recent) attempt per name
        seen_names: set[str] = set()
        unique_records: list[ExecutionRecord] = []
        for record in reversed(records):
            if record.process_name not in seen_names:
                seen_names.add(record.process_name)
                unique_records.append(record)
        unique_records.reverse()

        details = [
            {
                "name": r.process_name,
                "status": r.status,
                "elapsed_s": round(r.elapsed_s, 2),
                "message": r.message,
            }
            for r in records  # All records including retries
        ]

        return PipelineResult(
            total=len(unique_records),
            succeeded=sum(
                1 for r in unique_records if r.status in ("success", "recovered")
            ),
            failed=sum(
                1 for r in unique_records if r.status in ("failed", "error")
            ),
            skipped=skipped,
            aborted=aborted,
            details=details,
            elapsed_s=round(elapsed, 2),
        )
