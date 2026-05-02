"""Windows Task Scheduler integration for scheduled daily tasks.

Uses ``schtasks.exe`` to create/delete/query scheduled tasks.
No external dependencies (no pywin32/COM) — works in PyInstaller builds.

Usage::

    from anime_game_afk.runtime.scheduler import WinScheduler, ScheduleConfig

    cfg = ScheduleConfig(time="04:00", days=["mon", "tue"])
    sched = WinScheduler()
    sched.create_task(cfg)       # Register in Windows Task Scheduler
    info = sched.query_task()    # Check status
    sched.delete_task()          # Remove
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from anime_game_afk.runtime.logger import get_logger

logger = get_logger("scheduler")

# Task lives under \AetherGazerAFK\ in Task Scheduler
TASK_FOLDER = "\\AetherGazerAFK"
TASK_NAME = "DailyTask"
TASK_FULL_PATH = f"{TASK_FOLDER}\\{TASK_NAME}"


@dataclass
class ScheduleConfig:
    """Persistent schedule configuration."""

    enabled: bool = False
    time: str = "04:00"  # HH:MM 24h
    days: list[str] = field(default_factory=list)  # empty = daily
    pipeline_id: str = "daily_routine"
    retry_on_failure: bool = False
    post_action: str = "exit_app_and_game"  # nothing | exit_app | kill_game | exit_app_and_game

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScheduleConfig":
        return cls(
            enabled=bool(data.get("enabled", False)),
            time=str(data.get("time", "04:00")),
            days=list(data.get("days", [])),
            pipeline_id=str(data.get("pipeline_id", "daily_routine")),
            retry_on_failure=bool(data.get("retry_on_failure", False)),
            post_action=str(data.get("post_action", "nothing")),
        )


@dataclass
class ScheduleTaskInfo:
    """Info about the registered Windows scheduled task."""

    registered: bool = False
    enabled: bool = False
    next_run_time: str = ""
    last_run_time: str = ""
    last_result: int = 0
    status: str = "Unknown"


# ---------------------------------------------------------------------------
# Config persistence
# ---------------------------------------------------------------------------

def _config_path() -> Path:
    """Return path to scheduler config file."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "config" / "scheduler.json"
    return Path(__file__).resolve().parent.parent.parent.parent / "config" / "scheduler.json"


def schedule_config_exists() -> bool:
    """Check if schedule config file exists on disk."""
    return _config_path().exists()


def reconstruct_config_from_task() -> ScheduleConfig | None:
    """Reconstruct schedule config from Windows Task Scheduler XML.

    Used when the config file is missing but the task is registered.
    Returns None if the task is not registered or parsing fails.
    App-specific fields (pipeline_id, retry_on_failure, post_action) use defaults.
    """
    import xml.etree.ElementTree as ET

    try:
        cmd = [
            "schtasks", "/Query",
            "/TN", TASK_FULL_PATH,
            "/XML",
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            return None

        ns = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
        root = ET.fromstring(result.stdout)

        config = ScheduleConfig(enabled=True)

        # Parse start time from <StartBoundary>2026-01-01T15:07:00</StartBoundary>
        sb = root.find(".//t:StartBoundary", ns)
        if sb is not None and sb.text and "T" in sb.text:
            time_part = sb.text.split("T")[1][:5]  # "15:07"
            config.time = time_part

        # Parse daily vs weekly schedule
        if root.find(".//t:ScheduleByWeek", ns) is not None:
            dow = root.find(".//t:DaysOfWeek", ns)
            if dow is not None:
                _day_tag_map = {
                    "Monday": "mon", "Tuesday": "tue", "Wednesday": "wed",
                    "Thursday": "thu", "Friday": "fri",
                    "Saturday": "sat", "Sunday": "sun",
                }
                for child in dow:
                    tag = child.tag.split("}")[-1]  # Remove namespace prefix
                    if tag in _day_tag_map:
                        config.days.append(_day_tag_map[tag])
        # ScheduleByDay → days stays [] (= every day)

        # Check if task is enabled via Settings/Enabled (absent = enabled)
        enabled_el = root.find(".//t:Settings/t:Enabled", ns)
        if enabled_el is not None and (enabled_el.text or "").lower() == "false":
            config.enabled = False

        logger.info("Reconstructed schedule config from Windows task: {}", config)
        return config

    except Exception as e:
        logger.warning("Failed to reconstruct config from task XML: {}", e)
        return None


def load_schedule_config() -> ScheduleConfig:
    """Load schedule config from disk."""
    path = _config_path()
    if not path.exists():
        return ScheduleConfig()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ScheduleConfig.from_dict(data)
    except Exception as e:
        logger.error("Failed to load schedule config: {}", e)
        return ScheduleConfig()


def save_schedule_config(config: ScheduleConfig) -> None:
    """Save schedule config to disk (atomic write)."""
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    logger.info("Schedule config saved to {}", path)


# ---------------------------------------------------------------------------
# Schedule log (execution history)
# ---------------------------------------------------------------------------

def _log_path() -> Path:
    """Return path to schedule execution log."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "config" / "schedule_log.json"
    return Path(__file__).resolve().parent.parent.parent.parent / "config" / "schedule_log.json"


def append_schedule_log(entry: dict[str, Any]) -> None:
    """Append an execution record to the schedule log."""
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception:
            records = []

    records.append(entry)
    # Keep last 50 records
    records = records[-50:]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def load_schedule_log() -> list[dict[str, Any]]:
    """Load execution history."""
    path = _log_path()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Windows Task Scheduler wrapper (schtasks.exe)
# ---------------------------------------------------------------------------

_DAY_MAP = {
    "mon": "MON", "tue": "TUE", "wed": "WED", "thu": "THU",
    "fri": "FRI", "sat": "SAT", "sun": "SUN",
}


class WinScheduler:
    """Create/delete/query Windows scheduled tasks via schtasks.exe."""

    def _get_exe_path(self) -> str:
        """Get the path to our executable."""
        if getattr(sys, "frozen", False):
            return str(Path(sys.executable).resolve())
        # Dev mode: use python.exe + launcher.py
        return str(Path(sys.executable).resolve())

    def _get_exe_args(self) -> str:
        """Get arguments for the scheduled task action."""
        if getattr(sys, "frozen", False):
            return "--scheduled"
        # Dev mode: run launcher.py --scheduled
        launcher = Path(__file__).resolve().parent.parent.parent.parent / "launcher.py"
        return f'"{launcher}" --scheduled'

    def _build_xml(self, config: ScheduleConfig) -> str:
        """Build Windows Task Scheduler XML for the schedule."""
        hour, minute = config.time.split(":")
        # Start boundary: today at the specified time
        start_boundary = f"2026-01-01T{hour}:{minute}:00"

        exe_path = self._get_exe_path()
        exe_args = self._get_exe_args()

        # Working directory = exe's parent
        if getattr(sys, "frozen", False):
            working_dir = str(Path(sys.executable).resolve().parent)
        else:
            working_dir = str(
                Path(__file__).resolve().parent.parent.parent.parent
            )

        # Build trigger
        if config.days:
            # Weekly trigger with specific days
            days_of_week = ""
            for day in config.days:
                tag = _DAY_MAP.get(day.lower(), "")
                if tag:
                    day_full = {
                        "MON": "Monday", "TUE": "Tuesday", "WED": "Wednesday",
                        "THU": "Thursday", "FRI": "Friday", "SAT": "Saturday",
                        "SUN": "Sunday",
                    }[tag]
                    days_of_week += f"        <{day_full} />\n"
            trigger_xml = f"""    <CalendarTrigger>
      <StartBoundary>{start_boundary}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByWeek>
        <DaysOfWeek>
{days_of_week}        </DaysOfWeek>
        <WeeksInterval>1</WeeksInterval>
      </ScheduleByWeek>
    </CalendarTrigger>"""
        else:
            # Daily trigger
            trigger_xml = f"""    <CalendarTrigger>
      <StartBoundary>{start_boundary}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>"""

        xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>AetherGazer AFK daily automation task</Description>
    <Author>AetherGazerAFK</Author>
  </RegistrationInfo>
  <Triggers>
{trigger_xml}
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT4H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{exe_path}</Command>
      <Arguments>{exe_args}</Arguments>
      <WorkingDirectory>{working_dir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""
        return xml

    def create_task(self, config: ScheduleConfig) -> tuple[bool, str]:
        """Register the scheduled task. Returns (success, message)."""
        try:
            # Delete existing task first (ignore errors)
            self.delete_task()

            # Write XML to temp file
            xml_content = self._build_xml(config)
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".xml", encoding="utf-16",
                delete=False,
            ) as f:
                f.write(xml_content)
                xml_path = f.name

            try:
                cmd = [
                    "schtasks", "/Create",
                    "/TN", TASK_FULL_PATH,
                    "/XML", xml_path,
                    "/F",  # Force overwrite
                ]
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=15,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if result.returncode != 0:
                    err = (result.stderr or result.stdout).strip()
                    logger.error("schtasks /Create failed: {}", err)
                    return False, f"创建计划任务失败: {err}"

                logger.info("Scheduled task created: {}", TASK_FULL_PATH)
                return True, "计划任务已创建"
            finally:
                try:
                    os.unlink(xml_path)
                except OSError:
                    pass

        except Exception as e:
            logger.error("Failed to create scheduled task: {}", e)
            return False, f"创建计划任务异常: {e}"

    def delete_task(self) -> tuple[bool, str]:
        """Delete the scheduled task. Returns (success, message)."""
        try:
            cmd = [
                "schtasks", "/Delete",
                "/TN", TASK_FULL_PATH,
                "/F",
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0:
                logger.info("Scheduled task deleted: {}", TASK_FULL_PATH)
                return True, "计划任务已删除"
            # Task doesn't exist — not an error
            stderr = (result.stderr or "").lower()
            if "cannot find" in stderr or "does not exist" in stderr or "找不到" in (result.stderr or ""):
                return True, "计划任务不存在"
            err = (result.stderr or result.stdout).strip()
            logger.warning("schtasks /Delete failed: {}", err)
            return False, f"删除失败: {err}"
        except Exception as e:
            logger.error("Failed to delete scheduled task: {}", e)
            return False, f"删除异常: {e}"

    def enable_task(self, enabled: bool) -> tuple[bool, str]:
        """Enable or disable the scheduled task."""
        try:
            cmd = [
                "schtasks", "/Change",
                "/TN", TASK_FULL_PATH,
                "/ENABLE" if enabled else "/DISABLE",
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0:
                state = "启用" if enabled else "禁用"
                logger.info("Scheduled task {}: {}", state, TASK_FULL_PATH)
                return True, f"计划任务已{state}"
            err = (result.stderr or result.stdout).strip()
            return False, f"操作失败: {err}"
        except Exception as e:
            return False, f"操作异常: {e}"

    def query_task(self) -> ScheduleTaskInfo:
        """Query the current state of the scheduled task."""
        info = ScheduleTaskInfo()
        try:
            cmd = [
                "schtasks", "/Query",
                "/TN", TASK_FULL_PATH,
                "/FO", "CSV", "/V", "/NH",
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode != 0:
                return info  # Task not found

            info.registered = True
            # Parse CSV output (one line, verbose)
            line = result.stdout.strip().split("\n")[0]
            fields = _parse_csv_line(line)

            # CSV verbose format has many columns; key ones:
            # [0]=HostName, [1]=TaskName, [2]=NextRunTime, [3]=Status,
            # [4]=LogonMode, [5]=LastRunTime, [6]=LastResult, ...
            if len(fields) > 3:
                info.next_run_time = fields[2] if fields[2] != "N/A" else ""
                info.status = fields[3]
                info.enabled = fields[3] in ("Ready", "Running", "就绪", "正在运行")
            if len(fields) > 6:
                info.last_run_time = fields[5] if fields[5] != "N/A" else ""
                try:
                    info.last_result = int(fields[6])
                except (ValueError, IndexError):
                    pass

        except Exception as e:
            logger.warning("Failed to query scheduled task: {}", e)

        return info


def _parse_csv_line(line: str) -> list[str]:
    """Parse a CSV line handling quoted fields."""
    fields: list[str] = []
    current = ""
    in_quotes = False
    for ch in line:
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == "," and not in_quotes:
            fields.append(current.strip())
            current = ""
        else:
            current += ch
    fields.append(current.strip())
    return fields
