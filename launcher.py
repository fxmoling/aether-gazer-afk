"""Frozen-friendly entry point for packaged distribution.

Behavior:
    Double-click (no args)  -> Opens the pywebview GUI
    --cli                   -> Headless CLI mode (same as scripts/run.py)
    --cli --plan X.yaml     -> CLI with custom plan
    --cli --list            -> List available processes
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _setup_paths() -> Path:
    """Configure paths for frozen (PyInstaller) or normal execution.

    Returns:
        app_dir: The directory containing the .exe (frozen) or project root.
    """
    if getattr(sys, "frozen", False):
        # PyInstaller onedir: exe is in dist/anime-game-afk/
        app_dir = Path(sys.executable).resolve().parent
        # Internal data (Python packages) are in _internal/
        internal_dir = app_dir / "_internal"

        # MaaFw DLL path setup is handled by rthook_maa.py (runs before us).
        # Just ensure packages are importable.
        if str(internal_dir) not in sys.path:
            sys.path.insert(0, str(internal_dir))
    else:
        # Running from source
        app_dir = Path(__file__).resolve().parent
        src_dir = app_dir / "src"
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))

    # Create logs dir beside the exe if it doesn't exist
    (app_dir / "logs").mkdir(exist_ok=True)

    return app_dir


def _pause_before_exit() -> None:
    """Keep the console window open so the user can read output (CLI mode)."""
    if getattr(sys, "frozen", False):
        try:
            print()
            input("按回车键退出 / Press Enter to exit...")
        except (EOFError, OSError, RuntimeError):
            # No stdin available (windowed mode) — just return
            pass


# ── .NET Framework pre-flight check ─────────────────────────


_DOTNET_DOWNLOAD_URL = (
    "https://aka.ms/vs/17/release/vc_redist.x64.exe"
)

_DOTNET_REPAIR_CMD = (
    "DISM /Online /Cleanup-Image /RestoreHealth && "
    "sfc /scannow"
)


def _check_dotnet() -> bool:
    """Verify pythonnet can fully initialize (required by pywebview on Windows).

    Tests the entire chain: clr_loader → .NET Framework → Python.Runtime.dll.
    Returns True if OK, False if broken/missing.
    """
    try:
        import pythonnet
        pythonnet.load()
        return True
    except Exception:
        return False


def _show_dotnet_error() -> None:
    """Show a user-friendly dialog when pythonnet/.NET fails.
    
    Tries tkinter first (richer UI), falls back to Win32 MessageBoxW
    (always available, no Python package deps).
    """
    import webbrowser

    title = "AetherGazer AFK - 运行环境异常"
    message = (
        "程序的图形界面组件 (pywebview) 初始化失败。\n\n"
        "可能的原因和解决方法：\n"
        "1. 安装 Visual C++ 运行库 (vc_redist.x64.exe)\n"
        "2. 安装/修复 .NET Framework 4.8\n"
        "3. 运行系统修复命令（管理员 CMD）：\n"
        "     DISM /Online /Cleanup-Image /RestoreHealth\n"
        "     sfc /scannow\n\n"
        "点击「是」打开 VC++ 运行库下载页面。"
    )

    user_said_yes = False
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        user_said_yes = messagebox.askyesno(title, message)
        root.destroy()
    except Exception:
        # tkinter unavailable — fall back to Win32 API
        try:
            import ctypes
            # MB_YESNO=4, MB_ICONERROR=16
            result = ctypes.windll.user32.MessageBoxW(
                0, message, title, 4 | 16
            )
            user_said_yes = (result == 6)  # IDYES=6
        except Exception:
            # Last resort — console
            print(f"\n{'='*60}")
            print(f"  ERROR: {title}")
            print(f"{'='*60}")
            print(message)
            print(f"\n下载地址: {_DOTNET_DOWNLOAD_URL}")
            print(f"{'='*60}")
            user_said_yes = True  # Auto-open browser

    if user_said_yes:
        webbrowser.open(_DOTNET_DOWNLOAD_URL)


# ── GUI mode ────────────────────────────────────────────────


def _run_gui(app_dir: Path) -> None:
    """Launch the pywebview GUI."""
    if not _check_dotnet():
        _show_dotnet_error()
        sys.exit(1)

    from anime_game_afk.ui.app import main as gui_main
    gui_main()


# ── CLI mode ────────────────────────────────────────────────


def _run_cli(app_dir: Path) -> None:
    """Run headless CLI pipeline (same as scripts/run.py)."""
    import argparse
    import asyncio

    from anime_game_afk.config.user_config import UserConfig
    from anime_game_afk.core.device import DeviceAdapter
    from anime_game_afk.core.game_finder import find_aether_gazer
    from anime_game_afk.core.types import DeviceConfig
    from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG
    from anime_game_afk.games.aether_gazer.orchestrator.pipeline import Pipeline
    from anime_game_afk.games.aether_gazer.orchestrator.types import (
        ProcessDef,
        load_plan,
    )
    from anime_game_afk.games.aether_gazer.processes.base import ProcessContext
    from anime_game_afk.games.aether_gazer.registry import build_registry
    from anime_game_afk.games.aether_gazer.tasks.startup_tasks import (
        LaunchAndReachHub,
        ensure_game_running,
    )
    from anime_game_afk.runtime.logger import get_logger

    logger = get_logger("run")

    # Default plan: look beside exe first, then _internal, then source
    default_plan_candidates = [
        app_dir / "plans" / "default.yaml",
        app_dir / "_internal" / "plans" / "default.yaml",
        app_dir / "src" / "anime_game_afk" / "games" / "aether_gazer"
        / "orchestrator" / "plans" / "default.yaml",
    ]
    default_plan = str(
        next((p for p in default_plan_candidates if p.exists()), default_plan_candidates[0])
    )

    # Strip --cli from argv so argparse doesn't choke on it
    cli_argv = [a for a in sys.argv[1:] if a != "--cli"]

    parser = argparse.ArgumentParser(
        description="AetherGazer Automation (CLI mode)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--plan", type=str, default=default_plan, help="YAML plan file")
    parser.add_argument("--list", action="store_true", help="List available processes")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without executing")
    parser.add_argument("--launch", action="store_true", default=True,
                        help="Launch game before connecting (default)")
    parser.add_argument("--no-launch", action="store_true", help="Skip game launch")
    parser.add_argument("--detect-game", action="store_true", help="Auto-detect game path")
    args = parser.parse_args(cli_argv)

    print("=" * 60)
    print("  AetherGazer AFK - 深空之眼自动化 (CLI)")
    print("=" * 60)
    print()

    def make_device_config() -> DeviceConfig:
        return AETHER_GAZER_CONFIG.to_device_config()

    def build_context_factory(device: DeviceAdapter):  # type: ignore[return]
        def factory(proc_def: ProcessDef) -> ProcessContext:
            return ProcessContext(
                device=device,
                config=proc_def.config,
                logger=get_logger(f"process.{proc_def.name}"),
            )
        return factory

    async def run() -> int:
        registry = build_registry()

        if args.list:
            print("Available processes:")
            for name in registry.available():
                print(f"  - {name}")
            return 0

        if args.dry_run:
            plan = load_plan(args.plan)
            print(f"Plan: {args.plan}")
            print(f"Game: {plan.game}")
            print(f"Processes ({len(plan.enabled_processes)} enabled):")
            for proc in plan.processes:
                status = "ENABLED" if proc.enabled else "disabled"
                config_str = f" config={proc.config}" if proc.config else ""
                print(f"  [{status}] {proc.name}{config_str}")
            return 0

        user_cfg = UserConfig.load()

        if args.detect_game:
            game_id = "aether_gazer"
            exe_path = user_cfg.game_exe_path(game_id)
            if not exe_path or not Path(exe_path).exists():
                logger.info("Auto-detecting AetherGazer...")
                result = find_aether_gazer(search_drives=user_cfg.search_drives())
                if result["game_exe"]:
                    user_cfg.set_game_exe_path(game_id, result["game_exe"])
                    if result["launcher"]:
                        user_cfg.set_launcher_path(game_id, result["launcher"])
                    user_cfg.save()
                    exe_path = result["game_exe"]
            if exe_path:
                print(f"Game exe: {exe_path}")
                return 0
            print("ERROR: Could not find AetherGazer.")
            return 1

        if args.launch and not args.no_launch:
            game_id = "aether_gazer"
            exe_path = user_cfg.game_exe_path(game_id)
            if not exe_path or not Path(exe_path).exists():
                result = find_aether_gazer(search_drives=user_cfg.search_drives())
                if result["game_exe"]:
                    user_cfg.set_game_exe_path(game_id, result["game_exe"])
                    user_cfg.save()
                    exe_path = result["game_exe"]
            if not exe_path:
                logger.error("Cannot launch: game exe not found.")
                return 1
            timeout = user_cfg.launch_timeout("aether_gazer")
            if not ensure_game_running(
                exe_path=exe_path,
                window_title=user_cfg.window_title("aether_gazer") or "AetherGazer",
                timeout=timeout,
            ):
                logger.error("Failed to launch game within {t}s", t=timeout)
                return 1

        logger.info("Connecting to AetherGazer...")
        device = DeviceAdapter(config=make_device_config())
        try:
            device.connect()
        except Exception as exc:
            logger.error("Failed to connect: {exc}", exc=str(exc))
            return 1

        if not device.connected:
            logger.error("Failed to connect. Is AetherGazer running?")
            return 1

        logger.info("Connected. Resolution: {res}", res=device.actual_resolution)

        try:
            if args.launch and not args.no_launch:
                from anime_game_afk.games.aether_gazer.tasks.base import TaskContext
                ctx = TaskContext(device=device, logger=logger)
                launch_task = LaunchAndReachHub(
                    max_popup_attempts=user_cfg.popup_dismiss_max_attempts("aether_gazer"),
                )
                launch_result = await launch_task.execute(ctx)
                if launch_result.status != "success":
                    logger.error("Failed to reach hub: {msg}", msg=launch_result.message)
                    return 1

            pipeline = Pipeline(
                registry=registry,
                device=device,
                context_factory=build_context_factory(device),
            )
            result = await pipeline.run(args.plan)

            print("\n" + "=" * 60)
            print("Pipeline Summary")
            print("=" * 60)
            print(f"  Total:     {result.total}")
            print(f"  Succeeded: {result.succeeded}")
            print(f"  Failed:    {result.failed}")
            print(f"  Skipped:   {result.skipped}")
            print(f"  Time:      {result.elapsed_s:.1f}s")
            print(f"  Aborted:   {result.aborted}")
            print("=" * 60)
            return 0 if not result.aborted and result.failed == 0 else 1
        finally:
            device.disconnect()
            logger.info("Disconnected.")

    exit_code = asyncio.run(run())

    if exit_code == 0:
        print("\n任务全部完成 / All tasks completed.")
    else:
        print(f"\n任务未全部成功 / Some tasks failed (exit code {exit_code}).")

    _pause_before_exit()
    sys.exit(exit_code)


# ── Entry point ─────────────────────────────────────────────


def _run_worker() -> None:
    """Run the subprocess worker (called via --worker in frozen mode).
    
    The rthook sets PATH and MAAFW_BINARY_PATH, but os.add_dll_directory()
    is process-local and doesn't inherit to subprocesses. Re-register here
    before any import of maa triggers DLL loading.
    """
    if getattr(sys, "frozen", False):
        internal = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        maa_bin = internal / "maa" / "bin"
        if maa_bin.exists():
            try:
                os.add_dll_directory(str(maa_bin))
                # WARNING: Do NOT add _internal — its VC runtime conflicts with MaaFw
            except (OSError, AttributeError):
                pass

    # Strip --worker from argv so the worker's argparse sees only its own args
    sys.argv = [sys.argv[0]] + [a for a in sys.argv[1:] if a != "--worker"]
    from anime_game_afk.ui.worker import main as worker_main
    worker_main()


def _run_scheduled(app_dir: Path) -> None:
    """Run in scheduled mode — open normal GUI and auto-start the pipeline."""
    # Just set a flag; the GUI app will detect it and auto-start
    import builtins
    builtins._SCHEDULED_MODE = True  # type: ignore[attr-defined]
    _run_gui(app_dir)


def main() -> None:
    """Route to GUI (default), CLI, or worker based on arguments."""
    app_dir = _setup_paths()

    # ── Environment banner (always log, even if rest of startup fails) ──
    import platform
    _frozen = getattr(sys, "frozen", False)
    _env_lines = [
        f"AetherGazer AFK starting",
        f"  Python:    {sys.version}",
        f"  Platform:  {platform.platform()}",
        f"  Arch:      {platform.machine()}",
        f"  Frozen:    {_frozen}",
        f"  Exe:       {sys.executable}",
        f"  App dir:   {app_dir}",
        f"  CWD:       {os.getcwd()}",
        f"  Args:      {sys.argv}",
    ]
    if _frozen:
        _env_lines.append(f"  _MEIPASS:  {getattr(sys, '_MEIPASS', 'N/A')}")
    try:
        import importlib.metadata
        maa_ver = importlib.metadata.version("maafw")
        _env_lines.append(f"  MaaFw:     {maa_ver}")
    except Exception:
        _env_lines.append(f"  MaaFw:     (unknown)")
    _env_banner = "\n".join(_env_lines)

    # Write to log file FIRST (before any imports that might fail)
    _log_dir = app_dir / "logs"
    _log_dir.mkdir(exist_ok=True)
    _startup_log = _log_dir / "startup.log"
    try:
        from datetime import datetime
        with open(_startup_log, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"{datetime.now().isoformat()}\n")
            f.write(_env_banner + "\n")
            f.write(f"{'='*60}\n")
    except Exception:
        pass

    # Also print to stderr (visible in worker mode)
    print(_env_banner, file=sys.stderr)

    is_cli = "--cli" in sys.argv
    is_worker = "--worker" in sys.argv
    is_scheduled = "--scheduled" in sys.argv

    try:
        if is_worker:
            _run_worker()
        elif is_scheduled:
            _run_scheduled(app_dir)
        elif is_cli:
            _run_cli(app_dir)
        else:
            _run_gui(app_dir)
    except KeyboardInterrupt:
        print("\n用户中断 / Interrupted by user.")
        if is_cli:
            _pause_before_exit()
        sys.exit(1)
    except Exception as exc:
        print(f"\n程序出错 / Error: {exc}")
        import traceback
        traceback.print_exc()
        if is_cli:
            _pause_before_exit()
        sys.exit(1)


if __name__ == "__main__":
    main()
