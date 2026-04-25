"""Generic adapter for arbitrary executables.

Launches the configured executable with ``args_template`` and any
per-run ``extra_args``.  No tool-specific logic — useful for custom
scripts, batch files, or unsupported tools.
"""
from __future__ import annotations

from anime_game_afk.orchestrator.models import ToolConfig, ToolRun

from .base import BaseAdapter


class GenericAdapter(BaseAdapter):
    """Passthrough adapter for any executable."""

    _tool_id: str = "generic"

    def build_command(
        self,
        tool_config: ToolConfig,
        tool_run: ToolRun,
    ) -> list[str]:
        """Build command: ``<exe> [args_template...] [extra_args...]``."""
        return [tool_config.exe_path, *tool_config.args_template, *tool_run.extra_args]
