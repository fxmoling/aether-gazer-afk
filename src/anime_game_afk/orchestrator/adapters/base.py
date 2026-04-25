"""Base protocol and shared logic for tool adapters.

Each adapter knows how to launch, poll, and stop one external automation
tool (MAA, ok-ww, BetterGI, etc.).  The orchestrator's DAG executor
calls these methods — adapters never ``await`` long-running work themselves.
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Protocol, runtime_checkable

from loguru import logger

from anime_game_afk.orchestrator.models import (
    CompletionStrategy,
    ToolConfig,
    ToolRun,
    ToolRunStatus,
)

# Grace period before force-killing a process (seconds).
_STOP_GRACE_SECONDS: int = 5


# ---------------------------------------------------------------------------
# Protocol (interface)
# ---------------------------------------------------------------------------

@runtime_checkable
class ToolAdapter(Protocol):
    """Interface that every tool adapter must satisfy."""

    @property
    def tool_id(self) -> str:
        """Unique identifier matching :pyattr:`ToolConfig.tool_id`."""
        ...

    async def preflight(self, tool_config: ToolConfig) -> tuple[bool, str]:
        """Verify the tool is ready to run.

        Returns ``(True, "")`` on success or ``(False, reason)`` on failure.
        """
        ...

    async def start(
        self,
        tool_config: ToolConfig,
        tool_run: ToolRun,
    ) -> subprocess.Popen[bytes]:
        """Launch the tool as a subprocess and return the handle.

        The caller (DAG executor) owns polling / timeout logic.
        """
        ...

    async def poll(self, process: subprocess.Popen[bytes]) -> ToolRunStatus:
        """Non-blocking check of current process state."""
        ...

    async def stop(self, process: subprocess.Popen[bytes]) -> None:
        """Gracefully terminate, then force-kill after a grace period."""
        ...

    def build_command(
        self,
        tool_config: ToolConfig,
        tool_run: ToolRun,
    ) -> list[str]:
        """Build the full command-line argument list."""
        ...


# ---------------------------------------------------------------------------
# Base implementation with common logic
# ---------------------------------------------------------------------------

class BaseAdapter:
    """Shared implementation for :class:`ToolAdapter`.

    Subclasses typically only need to override :meth:`build_command`.
    """

    _tool_id: str = ""

    @property
    def tool_id(self) -> str:
        return self._tool_id

    # -- preflight -----------------------------------------------------------

    async def preflight(self, tool_config: ToolConfig) -> tuple[bool, str]:
        """Check that ``exe_path`` exists and is a file."""
        exe = Path(tool_config.exe_path)
        if not exe.exists():
            return False, f"可执行文件不存在: {exe}"
        if not exe.is_file():
            return False, f"路径不是文件: {exe}"
        return True, ""

    # -- start ---------------------------------------------------------------

    async def start(
        self,
        tool_config: ToolConfig,
        tool_run: ToolRun,
    ) -> subprocess.Popen[bytes]:
        """Launch the process with platform-appropriate flags."""
        cmd = self.build_command(tool_config, tool_run)
        cwd = tool_config.working_dir or str(Path(tool_config.exe_path).parent)

        logger.info("[{}] 启动命令: {}", self.tool_id, " ".join(cmd))

        creation_flags: int = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
        )
        logger.info("[{}] 进程已启动, PID={}", self.tool_id, process.pid)
        return process

    # -- poll ----------------------------------------------------------------

    async def poll(self, process: subprocess.Popen[bytes]) -> ToolRunStatus:
        """Return status based on ``process.poll()``."""
        rc = process.poll()
        if rc is None:
            return ToolRunStatus.RUNNING
        return ToolRunStatus.SUCCESS if rc == 0 else ToolRunStatus.FAILED

    # -- stop ----------------------------------------------------------------

    async def stop(self, process: subprocess.Popen[bytes]) -> None:
        """Graceful terminate → wait → force kill."""
        if process.poll() is not None:
            return  # already exited

        logger.info("[{}] 终止进程 PID={}", self.tool_id, process.pid)
        try:
            process.terminate()
        except OSError:
            return

        try:
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, process.wait,
                ),
                timeout=_STOP_GRACE_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning("[{}] 进程未响应, 强制结束 PID={}", self.tool_id, process.pid)
            try:
                process.kill()
                process.wait(timeout=3)
            except OSError:
                pass

    # -- build_command (subclasses override) ----------------------------------

    def build_command(
        self,
        tool_config: ToolConfig,
        tool_run: ToolRun,
    ) -> list[str]:
        """Default: exe_path + args_template + extra_args."""
        return [tool_config.exe_path, *tool_config.args_template, *tool_run.extra_args]
