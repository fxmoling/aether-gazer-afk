"""Manages orchestrator config within user_config.yaml.

Provides CRUD operations for tool registrations and schedule entries
stored under the ``orchestrator`` section of the user config YAML.

Config structure::

    orchestrator:
      tools:
        - tool_id: maa
          display_name: "MAA (明日方舟)"
          exe_path: "C:/tools/MAA/MAA.exe"
          tool_type: cli
          ...
      schedules:
        - schedule_id: abc123
          name: "每日凌晨任务"
          cron_expr: "0 4 * * *"
          plan: {...}
          enabled: true

Example::

    mgr = OrchestratorConfigManager()
    tools = mgr.get_tools()
    mgr.save_tool(ToolConfig(tool_id="maa", ...))
"""
from __future__ import annotations

from typing import Any

from loguru import logger

from anime_game_afk.config.user_config import UserConfig
from anime_game_afk.orchestrator.models import (
    CompletionStrategy,
    ScheduleEntry,
    ToolConfig,
    ToolType,
)


# ---------------------------------------------------------------------------
# Default tool presets
# ---------------------------------------------------------------------------

_DEFAULT_TOOLS: list[dict[str, Any]] = [
    {
        "tool_id": "maa",
        "display_name": "MAA (明日方舟)",
        "exe_path": "",
        "tool_type": "cli",
        "args_template": [],
        "completion": "process_exit",
        "timeout_minutes": 60,
        "icon": "🏰",
        "game_process_names": ["明日方舟.exe", "Arknights.exe"],
    },
    {
        "tool_id": "m9a",
        "display_name": "M9A (1999)",
        "exe_path": "",
        "tool_type": "replay",
        "args_template": ["-d"],
        "completion": "process_exit",
        "timeout_minutes": 45,
        "icon": "🎭",
        "game_process_names": ["Reverse1999.exe"],
    },
    {
        "tool_id": "okww",
        "display_name": "ok-ww (鸣潮)",
        "exe_path": "",
        "tool_type": "cli",
        "args_template": [],
        "completion": "process_exit",
        "timeout_minutes": 45,
        "icon": "🌊",
        "game_process_names": ["Wuthering Waves.exe", "Client-Win64-Shipping.exe"],
    },
    {
        "tool_id": "bettergi",
        "display_name": "BetterGI (原神)",
        "exe_path": "",
        "tool_type": "gui_cli",
        "args_template": [],
        "completion": "process_exit",
        "timeout_minutes": 60,
        "icon": "⚡",
        "game_process_names": ["YuanShen.exe", "GenshinImpact.exe"],
    },
    {
        "tool_id": "zzz",
        "display_name": "ZZZ (绝区零)",
        "exe_path": "",
        "tool_type": "headless",
        "args_template": ["-o"],
        "completion": "process_exit",
        "timeout_minutes": 45,
        "icon": "🎵",
        "game_process_names": ["ZenlessZoneZero.exe"],
    },
]


# ---------------------------------------------------------------------------
# OrchestratorConfigManager
# ---------------------------------------------------------------------------

class OrchestratorConfigManager:
    """Manages tool registry and schedule entries in user_config.yaml.

    All reads reload from disk to stay in sync with external edits.
    All writes flush immediately.
    """

    def __init__(self) -> None:
        self._cfg: UserConfig | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> UserConfig:
        """(Re)load config from disk."""
        self._cfg = UserConfig.load()
        return self._cfg

    def _orch_section(self) -> dict[str, Any]:
        """Get or create the ``orchestrator`` section in config."""
        cfg = self._load()
        return cfg.raw.setdefault("orchestrator", {})

    def _save(self) -> None:
        """Persist current config to disk."""
        if self._cfg is not None:
            self._cfg.save()

    # ------------------------------------------------------------------
    # Tool management
    # ------------------------------------------------------------------

    def get_tools(self) -> list[ToolConfig]:
        """Return all registered tools."""
        orch = self._orch_section()
        raw_tools: list[dict[str, Any]] = orch.get("tools", [])
        tools: list[ToolConfig] = []
        for d in raw_tools:
            try:
                tools.append(ToolConfig.from_dict(d))
            except (KeyError, ValueError) as exc:
                logger.warning("Skipping invalid tool config: {} — {}", d, exc)
        return tools

    def save_tool(self, tool: ToolConfig) -> None:
        """Add or update a tool in the registry.

        If a tool with the same ``tool_id`` exists, it is replaced.
        """
        orch = self._orch_section()
        raw_tools: list[dict[str, Any]] = orch.setdefault("tools", [])

        # Replace existing or append
        replaced = False
        for i, d in enumerate(raw_tools):
            if d.get("tool_id") == tool.tool_id:
                raw_tools[i] = tool.to_dict()
                replaced = True
                break
        if not replaced:
            raw_tools.append(tool.to_dict())

        self._save()
        logger.info("Saved tool: {}", tool.tool_id)

    def remove_tool(self, tool_id: str) -> bool:
        """Remove a tool by ID. Returns True if found and removed."""
        orch = self._orch_section()
        raw_tools: list[dict[str, Any]] = orch.get("tools", [])
        original_len = len(raw_tools)
        orch["tools"] = [d for d in raw_tools if d.get("tool_id") != tool_id]

        if len(orch["tools"]) < original_len:
            self._save()
            logger.info("Removed tool: {}", tool_id)
            return True
        return False

    def get_default_tools(self) -> list[ToolConfig]:
        """Return preset tool configs for common tools.

        These have empty ``exe_path`` — the user needs to fill them in
        or use the auto-scan feature.
        """
        return [ToolConfig.from_dict(d) for d in _DEFAULT_TOOLS]

    # ------------------------------------------------------------------
    # Schedule management
    # ------------------------------------------------------------------

    def get_schedules(self) -> list[ScheduleEntry]:
        """Return all schedule entries."""
        orch = self._orch_section()
        raw_schedules: list[dict[str, Any]] = orch.get("schedules", [])
        entries: list[ScheduleEntry] = []
        for d in raw_schedules:
            try:
                entries.append(ScheduleEntry.from_dict(d))
            except (KeyError, ValueError) as exc:
                logger.warning("Skipping invalid schedule config: {} — {}", d, exc)
        return entries

    def save_schedule(self, entry: ScheduleEntry | Any) -> None:
        """Add or update a schedule entry.

        Accepts either a :class:`ScheduleEntry` or a dict (for
        convenience when the ``last_run`` timestamp is updated on a
        deserialized entry).
        """
        if isinstance(entry, ScheduleEntry):
            entry_dict = entry.to_dict()
            schedule_id = entry.schedule_id
        else:
            entry_dict = entry
            schedule_id = entry.get("schedule_id", "")

        orch = self._orch_section()
        raw_schedules: list[dict[str, Any]] = orch.setdefault("schedules", [])

        replaced = False
        for i, d in enumerate(raw_schedules):
            if d.get("schedule_id") == schedule_id:
                raw_schedules[i] = entry_dict
                replaced = True
                break
        if not replaced:
            raw_schedules.append(entry_dict)

        self._save()
        logger.info("Saved schedule: {} ({})", schedule_id, entry_dict.get("name", ""))

    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a schedule by ID. Returns True if found and removed."""
        orch = self._orch_section()
        raw_schedules: list[dict[str, Any]] = orch.get("schedules", [])
        original_len = len(raw_schedules)
        orch["schedules"] = [
            d for d in raw_schedules if d.get("schedule_id") != schedule_id
        ]

        if len(orch["schedules"]) < original_len:
            self._save()
            logger.info("Removed schedule: {}", schedule_id)
            return True
        return False
