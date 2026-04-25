"""Adapter for MAA (MaaAssistantArknights) CLI.

Supports two launch modes:
* ``maa run <config>``  — run a saved task pipeline
* ``maa fight <stage> -m <medicine> --times <N>``  — single-stage farming

The adapter also checks that the ``maa`` CLI binary is reachable.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from loguru import logger

from anime_game_afk.orchestrator.models import ToolConfig, ToolRun

from .base import BaseAdapter


class MaaAdapter(BaseAdapter):
    """MAA CLI adapter (明日方舟 - Arknights)."""

    _tool_id: str = "maa"

    async def preflight(self, tool_config: ToolConfig) -> tuple[bool, str]:
        """Verify exe_path exists *and* ``maa`` CLI is on PATH."""
        ok, msg = await super().preflight(tool_config)
        if not ok:
            return ok, msg

        # Also check that the maa CLI itself is reachable.
        exe = Path(tool_config.exe_path)
        exe_name = exe.stem.lower()
        if exe_name == "maa" or exe_name == "maa_cli":
            # The configured exe IS the maa cli — already validated above.
            return True, ""

        # exe_path might point to MaaCore; verify `maa` is on PATH.
        if shutil.which("maa") is None:
            parent_dir = exe.parent
            maa_candidates = list(parent_dir.glob("maa.exe")) + list(
                parent_dir.glob("maa")
            )
            if not maa_candidates:
                return False, "maa CLI 不在 PATH 中, 也不在工具目录下"
            logger.debug("maa CLI 找到: {}", maa_candidates[0])
        return True, ""

    def build_command(
        self,
        tool_config: ToolConfig,
        tool_run: ToolRun,
    ) -> list[str]:
        """Build MAA CLI command.

        Priority:
        1. ``args_template`` if explicitly set on the config.
        2. ``extra_args`` from the run (e.g. ``["fight", "1-7", "-m", "3"]``).
        3. Default fallback: ``maa run daily``.
        """
        exe = tool_config.exe_path

        # User provided an explicit args template — use it verbatim.
        if tool_config.args_template:
            return [exe, *tool_config.args_template, *tool_run.extra_args]

        # Extra args can carry a full sub-command (fight, copilot, ...).
        if tool_run.extra_args:
            return [exe, *tool_run.extra_args]

        # Default: run a named config (or "daily").
        config = tool_run.config_name or "daily"
        return [exe, "run", config]
