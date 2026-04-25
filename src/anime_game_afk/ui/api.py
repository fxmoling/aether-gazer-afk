"""API class exposed to the frontend via pywebview js_api.

All public methods are callable from JavaScript as:
    const result = await pywebview.api.method_name(args...)

Return values must be JSON-serializable (dict, list, str, int, bool, None).
"""
from __future__ import annotations

from typing import Any

from anime_game_afk import __version__
from anime_game_afk.ui.bridge import LogForwarder
from anime_game_afk.ui.task_manager import TaskManager


class Api:
    """JavaScript-callable API for the automation GUI."""

    def __init__(
        self,
        task_manager: TaskManager,
        log_forwarder: LogForwarder,
        orch_manager: Any | None = None,
    ) -> None:
        self._tm = task_manager
        self._lf = log_forwarder
        self._orch = orch_manager

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> dict[str, Any]:
        """Connect to the game window."""
        return self._tm.connect()

    def disconnect(self) -> dict[str, Any]:
        """Disconnect from the game window."""
        return self._tm.disconnect()

    def get_status(self) -> dict[str, Any]:
        """Get current connection and execution status."""
        return self._tm.get_status()

    # ------------------------------------------------------------------
    # Pipelines & tasks
    # ------------------------------------------------------------------

    def get_pipelines(self) -> list[dict[str, Any]]:
        """Get all available pipelines and their tasks."""
        return self._tm.get_pipelines()

    def set_task_enabled(
        self, pipeline_id: str, task_id: str, enabled: bool
    ) -> dict[str, Any]:
        """Toggle a task's enabled state within a pipeline."""
        ok = self._tm.set_task_enabled(pipeline_id, task_id, enabled)
        return {"ok": ok}

    def set_all_enabled(
        self, pipeline_id: str, enabled: bool
    ) -> dict[str, Any]:
        """Toggle all tasks in a pipeline."""
        ok = self._tm.set_all_enabled(pipeline_id, enabled)
        return {"ok": ok}

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def start_run(self, pipeline_id: str) -> dict[str, Any]:
        """Start executing the selected pipeline."""
        return self._tm.start(pipeline_id)

    def stop_run(self) -> dict[str, Any]:
        """Stop execution after the current task completes."""
        return self._tm.stop()

    # ------------------------------------------------------------------
    # Auto-battle
    # ------------------------------------------------------------------

    def start_auto_battle(self, script_name: str = "default") -> dict[str, Any]:
        """Start the auto-battle toggle."""
        return self._tm.start_auto_battle(script_name)

    def stop_auto_battle(self) -> dict[str, Any]:
        """Stop the auto-battle toggle."""
        return self._tm.stop_auto_battle()

    def get_auto_battle_status(self) -> dict[str, Any]:
        """Get auto-battle status."""
        return {"enabled": self._tm._auto_battle_enabled}

    def list_combat_scripts(self) -> list[dict[str, str]]:
        """List available combat scripts from config/combat_scripts/."""
        from anime_game_afk.games.aether_gazer.combat.script import (
            load_script, _CONFIG_DIR,
        )
        scripts = []
        if _CONFIG_DIR.exists():
            for f in sorted(_CONFIG_DIR.glob("*.yaml")):
                try:
                    s = load_script(f.stem)
                    scripts.append({"id": f.stem, "name": s.name})
                except Exception:
                    scripts.append({"id": f.stem, "name": f.stem})
        return scripts

    # ------------------------------------------------------------------
    # Logs
    # ------------------------------------------------------------------

    def get_recent_logs(self, count: int = 200) -> list[dict[str, str]]:
        """Get recent log entries from the ring buffer."""
        return self._lf.get_recent(count)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def get_settings(self) -> dict[str, Any]:
        """Get current user settings."""
        from anime_game_afk.config.user_config import UserConfig

        cfg = UserConfig.load()
        game = cfg.raw.get("games", {}).get("aether_gazer", {})
        return {
            "version": __version__,
            "window_title": game.get("window_title", "AetherGazer"),
            "game_exe_path": game.get("game_exe_path", ""),
            "auto_update": cfg.auto_update(),
            "notify_on_complete": cfg.notify_on_complete(),
            "combat_keybinds": cfg.combat_keybinds(),
        }

    def save_settings(
        self, window_title: str,
    ) -> dict[str, Any]:
        """Save user settings to config file."""
        from anime_game_afk.config.user_config import UserConfig

        try:
            cfg = UserConfig.load()
            game = cfg._game("aether_gazer")
            game["window_title"] = window_title
            cfg.save()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def save_combat_keybinds(self, binds: dict[str, str]) -> dict[str, Any]:
        """Save combat keybind mapping."""
        from anime_game_afk.config.user_config import UserConfig

        try:
            cfg = UserConfig.load()
            cfg.set_combat_keybinds(binds)
            cfg.save()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Auto-update
    # ------------------------------------------------------------------

    def check_update(self) -> dict[str, Any]:
        """Check GitHub for a newer release version."""
        from anime_game_afk.updater import check_for_update

        result = check_for_update(timeout=8.0)
        if result is None:
            return {"ok": False, "error": "无法连接到 GitHub，请检查网络。"}
        return {"ok": True, **result}

    def set_auto_update(self, enabled: bool) -> dict[str, Any]:
        """Toggle the auto-update check on startup."""
        from anime_game_afk.config.user_config import UserConfig

        try:
            cfg = UserConfig.load()
            cfg.set_auto_update(enabled)
            cfg.save()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_notify_on_complete(self, enabled: bool) -> dict[str, Any]:
        """Toggle task-completion toast notifications."""
        from anime_game_afk.config.user_config import UserConfig

        try:
            cfg = UserConfig.load()
            cfg.set_notify_on_complete(enabled)
            cfg.save()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Game launch
    # ------------------------------------------------------------------

    def detect_game(self) -> dict[str, Any]:
        """Check if the game is running, return exe path if found."""
        from anime_game_afk.core.game_finder import find_aether_gazer
        from anime_game_afk.core.game_launcher import GameLauncher

        launcher = GameLauncher(
            exe_path="AetherGazer.exe",
            window_title="AetherGazer",
        )
        running = launcher.is_running()

        result: dict[str, Any] = {"running": running}

        if not running:
            # Try to find the game exe
            found = find_aether_gazer()
            result["game_exe"] = found.get("game_exe") or ""
        else:
            # Get path from running process
            from anime_game_afk.core.game_finder import GameFinder
            finder = GameFinder()
            path = finder._find_from_running_process("AetherGazer.exe")
            result["game_exe"] = path or ""

        return result

    # ------------------------------------------------------------------
    # Orchestrator (multi-script scheduler)
    # ------------------------------------------------------------------

    def _require_orch(self) -> Any:
        """Return the orchestrator manager or raise."""
        if self._orch is None:
            raise RuntimeError("OrchestratorRunManager not initialised")
        return self._orch

    def orch_get_tools(self) -> list[dict[str, Any]]:
        """Get all registered orchestrator tools."""
        try:
            return self._require_orch().get_tools()
        except Exception as e:
            return [{"error": str(e)}]

    def orch_save_tool(self, tool: dict[str, Any]) -> dict[str, Any]:
        """Add or update an orchestrator tool."""
        try:
            return self._require_orch().save_tool(tool)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def orch_remove_tool(self, tool_id: str) -> dict[str, Any]:
        """Remove an orchestrator tool by ID."""
        try:
            return self._require_orch().remove_tool(tool_id)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def orch_scan_tools(self) -> list[dict[str, Any]]:
        """Scan common paths for installed automation tools."""
        try:
            return self._require_orch().scan_tools()
        except Exception as e:
            return [{"error": str(e)}]

    def orch_get_schedules(self) -> list[dict[str, Any]]:
        """Get all schedule entries."""
        try:
            return self._require_orch().get_schedules()
        except Exception as e:
            return [{"error": str(e)}]

    def orch_save_schedule(self, schedule: dict[str, Any]) -> dict[str, Any]:
        """Add or update a schedule entry."""
        try:
            return self._require_orch().save_schedule(schedule)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def orch_remove_schedule(self, schedule_id: str) -> dict[str, Any]:
        """Remove a schedule entry by ID."""
        try:
            return self._require_orch().remove_schedule(schedule_id)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def orch_run_now(self, schedule_id: str) -> dict[str, Any]:
        """Manually trigger a schedule immediately."""
        try:
            return self._require_orch().run_now(schedule_id)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def orch_run_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Execute a RunPlan directly."""
        try:
            return self._require_orch().run_plan(plan)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def orch_stop(self) -> dict[str, Any]:
        """Stop the current orchestrator run."""
        try:
            return self._require_orch().stop()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def orch_get_run_status(self) -> dict[str, Any]:
        """Get current orchestrator run status."""
        try:
            return self._require_orch().get_run_status()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Game launch
    # ------------------------------------------------------------------

    def launch_game(self) -> dict[str, Any]:
        """Launch the game and wait for its window to appear."""
        from anime_game_afk.config.user_config import UserConfig
        from anime_game_afk.core.game_finder import find_aether_gazer
        from anime_game_afk.core.game_launcher import GameLauncher

        cfg = UserConfig.load()
        exe_path = cfg.game_exe_path("aether_gazer")

        if not exe_path:
            # Auto-detect
            found = find_aether_gazer()
            exe_path = found.get("game_exe") or ""
            if exe_path:
                cfg.set_game_exe_path("aether_gazer", exe_path)
                cfg.save()

        if not exe_path:
            return {
                "ok": False,
                "error": "未找到游戏路径。请在设置中手动指定游戏 exe 路径。",
            }

        window_title = cfg.window_title("aether_gazer") or "AetherGazer"
        launcher = GameLauncher(
            exe_path=exe_path,
            window_title=window_title,
        )

        if launcher.is_running():
            return {"ok": True, "message": "游戏已在运行"}

        ok = launcher.ensure_running(timeout=120)
        if ok:
            return {"ok": True, "message": "游戏已启动"}
        return {"ok": False, "error": "游戏启动超时，请手动启动游戏"}
