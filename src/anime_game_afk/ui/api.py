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

    def start_auto_battle(self, script_name: str = "") -> dict[str, Any]:
        """Start the auto-battle toggle."""
        return self._tm.start_auto_battle(script_name)

    def stop_auto_battle(self) -> dict[str, Any]:
        """Stop the auto-battle toggle."""
        return self._tm.stop_auto_battle()

    def swap_auto_battle_script(self, script_name: str) -> dict[str, Any]:
        """Hot-swap combat script while auto-battle is running."""
        return self._tm.swap_auto_battle_script(script_name)

    def get_auto_battle_status(self) -> dict[str, Any]:
        """Get auto-battle status."""
        return {
            "enabled": self._tm._auto_battle_enabled,
            "script": self._tm._auto_battle_script,
        }

    def list_combat_scripts(self) -> list[dict[str, Any]]:
        """List available combat scripts from config/combat_scripts/."""
        from anime_game_afk.games.aether_gazer.combat.script import list_scripts
        return list_scripts()

    def get_combat_script(self, script_id: str) -> dict[str, Any]:
        """Get full YAML content of a combat script."""
        from anime_game_afk.games.aether_gazer.combat.script import (
            _CONFIG_DIR, load_script, validate_script_id,
        )
        try:
            script_id = validate_script_id(script_id)
            path = _CONFIG_DIR / f"{script_id}.yaml"
            if not path.exists():
                return {"ok": False, "error": f"Script '{script_id}' not found"}
            content = path.read_text(encoding="utf-8")
            script = load_script(script_id)
            return {
                "ok": True, "id": script_id,
                "content": content, "script": script.to_dict(),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def save_combat_script(
        self, script_id: str, content: str,
    ) -> dict[str, Any]:
        """Validate and save a combat script YAML file."""
        from anime_game_afk.games.aether_gazer.combat.script import save_script_file
        try:
            path = save_script_file(script_id, content)
            return {"ok": True, "path": str(path)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def delete_combat_script(self, script_id: str) -> dict[str, Any]:
        """Delete a combat script (cannot delete 'default')."""
        from anime_game_afk.games.aether_gazer.combat.script import delete_script_file
        try:
            delete_script_file(script_id)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def validate_combat_script(self, content: str) -> dict[str, Any]:
        """Validate a YAML combat script without saving."""
        from anime_game_afk.games.aether_gazer.combat.script import load_script_from_string
        try:
            script = load_script_from_string(content)
            return {
                "ok": True,
                "name": script.name,
                "startup_count": len(script.startup_steps),
                "loop_count": len(script.loop_steps),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_combat_script(self, script_name: str) -> dict[str, Any]:
        """Set the active combat script in user config."""
        from anime_game_afk.config.user_config import UserConfig
        try:
            cfg = UserConfig.load()
            cfg.set_combat_script(script_name)
            cfg.save()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Combo recording
    # ------------------------------------------------------------------

    def start_combo_recording(
        self, section: str = "loop", countdown: int = 3,
    ) -> dict[str, Any]:
        """Start recording keyboard inputs for a combo."""
        return self._tm.start_combo_recording(section, countdown)

    def stop_combo_recording(self) -> dict[str, Any]:
        """Stop recording and return compiled steps."""
        return self._tm.stop_combo_recording()

    def get_combo_recorder_status(self) -> dict[str, Any]:
        """Get recorder state (idle/countdown/recording + event count)."""
        return self._tm.get_combo_recorder_status()

    def consume_combo_result(self) -> dict[str, Any]:
        """Consume pending recording result (for hotkey-initiated stops)."""
        return self._tm.consume_combo_result()

    def test_combo_playback(
        self, steps_data: list, loops: int = 1,
    ) -> dict[str, Any]:
        """Replay combo steps in-game for testing."""
        return self._tm.test_combo_playback(steps_data, loops)

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
            "combat_script": cfg.combat_script(),
            "duowei_swipe_multiplier": cfg.duowei_swipe_multiplier(),
            "theme": cfg.theme(),
            "post_run_action": cfg.post_run_action(),
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

    def save_duowei_swipe_multiplier(self, value: float) -> dict[str, Any]:
        """Save duowei camera rotation multiplier (0.5–2.0)."""
        from anime_game_afk.config.user_config import UserConfig

        try:
            cfg = UserConfig.load()
            cfg.set_duowei_swipe_multiplier(value)
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
    # Theme
    # ------------------------------------------------------------------

    def set_theme(self, theme_id: str) -> dict[str, Any]:
        """Save UI theme preference."""
        from anime_game_afk.config.user_config import UserConfig

        try:
            cfg = UserConfig.load()
            cfg.set_theme(theme_id)
            cfg.save()
            return {"ok": True, "theme": theme_id}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_post_run_action(self, action: str) -> dict[str, Any]:
        """Save post-run action preference."""
        from anime_game_afk.config.user_config import UserConfig

        try:
            cfg = UserConfig.load()
            cfg.set_post_run_action(action)
            cfg.save()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def open_log_folder(self) -> dict[str, Any]:
        """Open the logs directory in the system file explorer."""
        import os
        import subprocess
        from pathlib import Path

        # Prefer run-log directory (logs/), fall back to app logs
        logs_dir = Path(__file__).resolve().parent.parent.parent.parent / "logs"
        if not logs_dir.exists():
            logs_dir.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer", str(logs_dir)])
        return {"ok": True, "path": str(logs_dir)}

    # ------------------------------------------------------------------
    # Schedule (lightweight scheduler)
    # ------------------------------------------------------------------

    def get_schedule(self) -> dict[str, Any]:
        """Get current schedule configuration and status.

        If the config file is missing but a Windows task is registered,
        reconstructs the config from the task XML and persists it.
        """
        from anime_game_afk.runtime.scheduler import (
            WinScheduler,
            load_schedule_config,
            save_schedule_config,
            schedule_config_exists,
            reconstruct_config_from_task,
        )
        config = load_schedule_config()
        sched = WinScheduler()
        task_info = sched.query_task()

        # Self-heal: if config file missing but task is registered,
        # reconstruct config from Windows Task Scheduler XML.
        if not schedule_config_exists() and task_info.registered:
            recovered = reconstruct_config_from_task()
            if recovered is not None:
                config = recovered
                try:
                    save_schedule_config(config)
                except Exception:
                    pass  # Best-effort persistence; still return recovered config

        return {
            "config": config.to_dict(),
            "task": {
                "registered": task_info.registered,
                "enabled": task_info.enabled,
                "next_run_time": task_info.next_run_time,
                "last_run_time": task_info.last_run_time,
                "last_result": task_info.last_result,
                "status": task_info.status,
            },
        }

    def save_schedule(self, config: dict[str, Any]) -> dict[str, Any]:
        """Save schedule config and register/update Windows task."""
        from anime_game_afk.runtime.scheduler import (
            ScheduleConfig,
            WinScheduler,
            save_schedule_config,
        )
        try:
            cfg = ScheduleConfig.from_dict(config)
            save_schedule_config(cfg)

            sched = WinScheduler()
            if cfg.enabled:
                ok, msg = sched.create_task(cfg)
            else:
                ok, msg = sched.delete_task()

            return {"ok": ok, "message": msg}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def delete_schedule(self) -> dict[str, Any]:
        """Delete the scheduled task and disable config."""
        from anime_game_afk.runtime.scheduler import (
            ScheduleConfig,
            WinScheduler,
            load_schedule_config,
            save_schedule_config,
        )
        try:
            cfg = load_schedule_config()
            cfg.enabled = False
            save_schedule_config(cfg)

            sched = WinScheduler()
            ok, msg = sched.delete_task()
            return {"ok": ok, "message": msg}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_schedule_history(self) -> list[dict[str, Any]]:
        """Get schedule execution history (most recent first)."""
        from anime_game_afk.runtime.scheduler import load_schedule_log
        records = load_schedule_log()
        records.reverse()
        return records[:20]

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
