"""Adapter for ZZZ-OneDragon (绝区零 — Zenless Zone Zero assistant).

Command format: ``<exe> -o [--close-game] [--shutdown <delay>] [--instance N]``

* ``-o``           headless / one-dragon mode
* ``--close-game`` close the game after tasks finish
* ``--shutdown N`` shutdown the PC after *N* seconds (safety delay)
* ``--instance N`` multi-instance selector
"""
from __future__ import annotations

from anime_game_afk.orchestrator.models import ToolConfig, ToolRun

from .base import BaseAdapter


class ZzzAdapter(BaseAdapter):
    """ZZZ-OneDragon adapter (绝区零)."""

    _tool_id: str = "zzz"

    def build_command(
        self,
        tool_config: ToolConfig,
        tool_run: ToolRun,
    ) -> list[str]:
        """Build command: ``<exe> -o [options...] [extra_args...]``.

        Recognised ``extra_args`` tokens (processed in order):
        * ``--close-game``        — appended verbatim
        * ``--shutdown <seconds>``— appended with its value
        * ``--instance <N>``      — appended with its value
        * anything else           — appended as-is
        """
        cmd = [tool_config.exe_path, "-o"]

        if tool_config.args_template:
            cmd.extend(tool_config.args_template)

        cmd.extend(tool_run.extra_args)
        return cmd
