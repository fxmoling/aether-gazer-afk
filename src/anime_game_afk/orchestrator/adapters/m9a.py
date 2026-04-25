"""Adapter for M9A (1999 助手).

M9A runs in non-interactive daemon mode via the ``-d`` flag.
It reads its task pipeline from a config file and exits upon completion.
Default timeout is 30 minutes.
"""
from __future__ import annotations

from anime_game_afk.orchestrator.models import ToolConfig, ToolRun

from .base import BaseAdapter


class M9aAdapter(BaseAdapter):
    """M9A adapter (重返未来：1999)."""

    _tool_id: str = "m9a"

    def build_command(
        self,
        tool_config: ToolConfig,
        tool_run: ToolRun,
    ) -> list[str]:
        """Build command: ``<exe> -d [extra_args...]``.

        ``-d`` enables non-interactive (daemon) mode — the tool reads its
        saved task list, executes them sequentially, and exits.
        """
        cmd = [tool_config.exe_path, "-d"]

        if tool_config.args_template:
            cmd.extend(tool_config.args_template)

        cmd.extend(tool_run.extra_args)
        return cmd
