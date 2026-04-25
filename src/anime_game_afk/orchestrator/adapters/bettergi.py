"""Adapter for BetterGI (原神 — Genshin Impact helper).

BetterGI uses ``startOneDragon <config_name>`` to launch its daily-task
pipeline.  It does **not** auto-exit on completion, so the adapter uses
TIMEOUT-based polling and an extended ``stop()`` that also kills the game
processes listed in :pyattr:`ToolConfig.game_process_names`.
"""
from __future__ import annotations

import asyncio
import subprocess
import sys

from loguru import logger

from anime_game_afk.orchestrator.models import ToolConfig, ToolRun, ToolRunStatus

from .base import BaseAdapter, _STOP_GRACE_SECONDS


class BetterGiAdapter(BaseAdapter):
    """BetterGI adapter (原神 - Genshin Impact)."""

    _tool_id: str = "bettergi"

    def build_command(
        self,
        tool_config: ToolConfig,
        tool_run: ToolRun,
    ) -> list[str]:
        """Build command: ``<exe> startOneDragon <config>``."""
        config = tool_run.config_name or "默认"

        cmd = [tool_config.exe_path, "startOneDragon", config]

        if tool_config.args_template:
            cmd.extend(tool_config.args_template)

        cmd.extend(tool_run.extra_args)
        return cmd

    # -- poll (timeout strategy) ---------------------------------------------

    async def poll(self, process: subprocess.Popen[bytes]) -> ToolRunStatus:
        """BetterGI does not auto-exit; rely on the executor's timeout.

        While the process is alive we always report RUNNING.  The DAG
        executor is responsible for comparing elapsed time against
        ``ToolRun.timeout_minutes`` and calling ``stop()`` when exceeded.
        If the process exits on its own, treat exit-code 0 as success.
        """
        rc = process.poll()
        if rc is None:
            return ToolRunStatus.RUNNING
        # Unexpected self-exit: respect exit code.
        return ToolRunStatus.SUCCESS if rc == 0 else ToolRunStatus.FAILED

    # -- stop (also kill game processes) -------------------------------------

    async def stop(self, process: subprocess.Popen[bytes]) -> None:
        """Stop BetterGI and optionally kill related game processes."""
        await super().stop(process)
        await self._kill_game_processes()

    async def stop_with_config(
        self,
        process: subprocess.Popen[bytes],
        tool_config: ToolConfig,
    ) -> None:
        """Extended stop that uses the tool config's game_process_names."""
        await super().stop(process)
        if tool_config.game_process_names:
            await self._kill_game_processes(tool_config.game_process_names)

    # -- internals -----------------------------------------------------------

    @staticmethod
    async def _kill_game_processes(
        names: list[str] | None = None,
    ) -> None:
        """Best-effort kill of known Genshin-related processes."""
        targets = names or ["YuanShen.exe", "GenshinImpact.exe", "Genshin Impact"]
        if sys.platform != "win32":
            return

        for name in targets:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "taskkill", "/F", "/IM", name,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                await proc.wait()
            except FileNotFoundError:
                pass
            except OSError as exc:
                logger.debug("结束 {} 失败: {}", name, exc)
