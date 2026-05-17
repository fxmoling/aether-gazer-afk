"""Build script for packaging anime-game-afk into a distributable folder.

Usage:
    python build.py          # Build the distribution
    python build.py --clean  # Clean previous build artifacts first
    python build.py --zip    # Build and create a ZIP archive

Output:
    dist/anime-game-afk/     # Distributable folder
    dist/anime-game-afk.zip  # (with --zip) Ready-to-share archive
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
APP_NAME = "anime-game-afk"
SPEC_FILE = PROJECT_ROOT / f"{APP_NAME}.spec"

# Site-packages base — discover via sysconfig so it works for both
# system Python (Lib/site-packages beside python.exe) and venvs
# (where python.exe lives in Scripts/ but site-packages is one level
# up under Lib/).
import sysconfig
SITE_PACKAGES = Path(sysconfig.get_paths()["purelib"])
MAA_PKG = SITE_PACKAGES / "maa"
MAA_AGENT_BINARY = SITE_PACKAGES / "MaaAgentBinary"

if not MAA_PKG.exists():
    raise SystemExit(
        f"FATAL: maa package not found at {MAA_PKG}. "
        f"Run pip install -e .[dev] in the active environment first."
    )


def clean() -> None:
    """Remove previous build artifacts."""
    for d in [DIST_DIR, BUILD_DIR]:
        if d.exists():
            print(f"Cleaning {d}...")
            shutil.rmtree(d)
    print("Clean done.")


def generate_spec() -> str:
    """Generate the PyInstaller .spec file content programmatically.

    This is more maintainable than a static .spec file because we can
    compute paths dynamically.
    """
    # MaaFw DLLs: NOT included here. PyInstaller's binary reclassification and
    # bootloader preloading cause failures. We copy them manually in post-build.
    maa_datas = []

    # MaaAgentBinary — skip for Win32 builds (only needed for adb/Android, ~13MB)
    agent_datas = []
    # Uncomment next 2 lines if you need adb (Android emulator) support:
    # if MAA_AGENT_BINARY.exists():
    #     agent_datas.append((str(MAA_AGENT_BINARY), "MaaAgentBinary"))

    # Collect project assets -> assets/ (only templates remain)
    assets_dir = PROJECT_ROOT / "assets"
    project_datas = []
    if assets_dir.exists():
        for sub in assets_dir.rglob("*"):
            if sub.is_file():
                rel = sub.relative_to(assets_dir)
                project_datas.append((str(sub), f"assets/{rel.parent}"))

    # Collect config templates -> config/
    config_dir = PROJECT_ROOT / "config"
    if config_dir.exists():
        project_datas.append((str(config_dir), "config"))

    # Collect rapidocr_onnxruntime data files (config + models)
    rapidocr_pkg = SITE_PACKAGES / "rapidocr_onnxruntime"
    if rapidocr_pkg.exists():
        for sub in rapidocr_pkg.rglob("*"):
            if sub.is_file() and sub.suffix in (".yaml", ".yml", ".onnx"):
                rel = sub.relative_to(rapidocr_pkg)
                project_datas.append(
                    (str(sub), f"rapidocr_onnxruntime/{rel.parent}")
                )

    # OCR runtime collection.  rapidocr_onnxruntime is imported lazily at
    # runtime, so PyInstaller does not reliably discover it from static
    # analysis.  onnxruntime also ships native DLL/PYD files under capi/
    # that must be included explicitly.
    ocr_binaries = []
    extra_hidden_imports = []
    try:
        from PyInstaller.utils.hooks import (
            collect_data_files,
            collect_dynamic_libs,
            collect_submodules,
        )

        for pkg in ("rapidocr_onnxruntime", "onnxruntime", "pyclipper"):
            extra_hidden_imports.extend(collect_submodules(pkg))
        project_datas.extend(
            collect_data_files("rapidocr_onnxruntime", include_py_files=False)
        )
        project_datas.extend(
            collect_data_files("onnxruntime", include_py_files=False)
        )
        ocr_binaries.extend(collect_dynamic_libs("onnxruntime"))
        ocr_binaries.extend(collect_dynamic_libs("pyclipper"))
    except Exception as exc:
        print(f"WARNING: OCR runtime collection failed: {exc}")
    ort_capi = SITE_PACKAGES / "onnxruntime" / "capi"
    if ort_capi.exists():
        for sub in ort_capi.iterdir():
            if sub.is_file() and sub.suffix.lower() in (".dll", ".pyd"):
                ocr_binaries.append((str(sub), "onnxruntime/capi"))
    if ocr_binaries:
        seen_binaries = set()
        unique_binaries = []
        for src, dst in ocr_binaries:
            key = (str(Path(src).resolve()).lower(), dst.replace("\\", "/").lower())
            if key not in seen_binaries:
                seen_binaries.add(key)
                unique_binaries.append((src, dst))
        ocr_binaries = unique_binaries

    # Collect YAML plans -> plans/ (convenient top-level access)
    plans_dir = (
        PROJECT_ROOT
        / "src"
        / "anime_game_afk"
        / "games"
        / "aether_gazer"
        / "orchestrator"
        / "plans"
    )
    if plans_dir.exists():
        project_datas.append((str(plans_dir), "plans"))

    # Collect web UI files
    web_dir = PROJECT_ROOT / "src" / "anime_game_afk" / "ui" / "web"
    if web_dir.exists():
        project_datas.append(
            (str(web_dir), "anime_game_afk/ui/web")
        )

    # Format for .spec file
    def fmt_list(items: list[tuple[str, str]], indent: int = 8) -> str:
        if not items:
            return "[]"
        pad = " " * indent
        lines = [f"(r'{src}', r'{dst}')," for src, dst in items]
        return "[\n" + "\n".join(f"{pad}{line}" for line in lines) + "\n    ]"

    binaries_str = fmt_list(ocr_binaries)
    datas_str = fmt_list(maa_datas + agent_datas + project_datas)

    # Hidden imports: modules that PyInstaller can't detect via static analysis
    hidden_imports = [
        "maa",
        "maa.library",
        "maa.define",
        "maa.controller",
        "maa.toolkit",
        "maa.tasker",
        "maa.resource",
        "maa.context",
        "maa.buffer",
        "maa.job",
        "maa.custom_action",
        "maa.custom_recognition",
        "maa.agent",
        "maa.agent.agent_server",
        "maa.agent_client",
        "maa.event_sink",
        "maa.pipeline",
        "numpy",
        "cv2",
        "loguru",
        "yaml",
        "colorama",
        "win32ctypes",
        "webview",
        "anime_game_afk",
        "anime_game_afk.ui",
        "anime_game_afk.ui.app",
        "anime_game_afk.ui.api",
        "anime_game_afk.ui.bridge",
        "anime_game_afk.ui.task_manager",
        "anime_game_afk.core",
        "anime_game_afk.core.device",
        "anime_game_afk.core.types",
        "anime_game_afk.core.errors",
        "anime_game_afk.core.game_finder",
        "anime_game_afk.core.game_launcher",
        "anime_game_afk.vision",
        "anime_game_afk.vision.color",
        "anime_game_afk.vision.geometry",
        "anime_game_afk.vision.matcher",
        "anime_game_afk.vision.ocr",
        "anime_game_afk.runtime",
        "anime_game_afk.runtime.logger",
        "anime_game_afk.runtime.config",
        "anime_game_afk.runtime.state",
        "anime_game_afk.runtime.clock",
        "anime_game_afk.runtime.events",
        "anime_game_afk.runtime.errors",
        "anime_game_afk.runtime.scheduler",
        "anime_game_afk.runtime.headless",
        "anime_game_afk.config",
        "anime_game_afk.config.user_config",
        "anime_game_afk.games.aether_gazer",
        "anime_game_afk.games.aether_gazer.config",
        "anime_game_afk.games.aether_gazer.knowledge",
        "anime_game_afk.games.aether_gazer.knowledge.constants",
        "anime_game_afk.games.aether_gazer.orchestrator",
        "anime_game_afk.games.aether_gazer.orchestrator.pipeline",
        "anime_game_afk.games.aether_gazer.orchestrator.types",
        "anime_game_afk.games.aether_gazer.orchestrator.executor",
        "anime_game_afk.games.aether_gazer.orchestrator.recovery",
        "anime_game_afk.games.aether_gazer.processes",
        "anime_game_afk.games.aether_gazer.processes.base",
        "anime_game_afk.games.aether_gazer.processes.daily_routine",
        "anime_game_afk.games.aether_gazer.processes.push_main_story",
        "anime_game_afk.games.aether_gazer.processes.duowei_process",
        "anime_game_afk.games.aether_gazer.tasks.duowei_tasks",
        "anime_game_afk.games.aether_gazer.knowledge.keys",
        "anime_game_afk.games.aether_gazer.registry",
        "anime_game_afk.games.aether_gazer.tasks",
        "anime_game_afk.games.aether_gazer.tasks.base",
        "anime_game_afk.games.aether_gazer.tasks.startup_tasks",
        "anime_game_afk.games.aether_gazer.tasks.combat_tasks",
        "anime_game_afk.games.aether_gazer.tasks.story_tasks",
        "anime_game_afk.games.aether_gazer.tasks.stamina_tasks",
        "anime_game_afk.games.aether_gazer.tasks.shop_tasks",
        "anime_game_afk.games.aether_gazer.tasks.mail_tasks",
        "anime_game_afk.games.aether_gazer.tasks.guild_tasks",
        "anime_game_afk.games.aether_gazer.tasks.activity_tasks",
        "anime_game_afk.games.aether_gazer.tasks.navigation_tasks",
        "anime_game_afk.games.aether_gazer.tasks.amusement_tasks",
        "anime_game_afk.games.aether_gazer.tasks.observation_tasks",
        "anime_game_afk.games.aether_gazer.ops",
        "anime_game_afk.games.aether_gazer.ops.base",
        "rapidocr_onnxruntime",
        "rapidocr_onnxruntime.main",
        "onnxruntime",
        "onnxruntime.capi",
        "onnxruntime.capi.onnxruntime_pybind11_state",
        "onnxruntime.capi._pybind_state",
        "pyclipper",
        # Lazy imports — PyInstaller cannot trace these via static analysis
        "anime_game_afk.games.aether_gazer.combat.script",
        "anime_game_afk.games.aether_gazer.combat.service",
        "anime_game_afk.games.aether_gazer.ops.navigate.wake_hub_ui",
        "anime_game_afk.games.aether_gazer.knowledge.pages",
        "anime_game_afk.core.notifier",
        "anime_game_afk.core.hotkey_listener",
        "anime_game_afk.runtime.run_log",
    ]
    hidden_imports.extend(
        m for m in sorted(set(extra_hidden_imports))
        if m not in hidden_imports
    )

    hidden_str = ",\n        ".join(f"'{m}'" for m in hidden_imports)

    spec = f"""# -*- mode: python ; coding: utf-8 -*-
# Auto-generated by build.py — do not edit manually.
# Regenerate with: python build.py

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    [r'{PROJECT_ROOT / "launcher.py"}'],
    pathex=[r'{PROJECT_ROOT / "src"}'],
    binaries={binaries_str},
    datas={datas_str},
    hiddenimports=[
        {hidden_str}
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[r'{PROJECT_ROOT / "rthook_maa.py"}'],
    excludes=[
        'pytest', 'pytest_cov', 'pytest_asyncio',
        'mypy', 'ruff',
        'matplotlib', 'scipy', 'pandas',
        'IPython', 'jupyter',
        'torch', 'transformers', 'huggingface_hub',
        'pytesseract',
        # NOTE: bottle, pythonnet, clr_loader are needed by pywebview — do NOT exclude
        # NOTE: rapidocr_onnxruntime, onnxruntime, pyclipper are needed for OCR — do NOT exclude
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filter out MaaFw DLLs from auto-detected binaries.
# PyInstaller's Analysis finds these via `import maa` but the bootloader
# cannot preload them (they need PATH setup first). They are already
# included as datas in maa/bin/ and loaded by maa.__init__.py at runtime.
_maa_dll_names = {{
    'maaframework', 'maatoolkit', 'maautils', 'maaadbcontrolunit',
    'maaagentclient', 'maaagentserver', 'maacustomcontrolunit',
    'maagamepadcontrolunit', 'maarecordcontrolunit', 'maareplaycontrolunit',
    'maawin32controlunit', 'directml', 'fastdeploy_ppocr_maa',
    'onnxruntime_maa', 'opencv_world4_maa', 'vigemclient', 'maaplugindemo',
}}
def _is_maafw_binary(name, path):
    if Path(name).stem.lower() not in _maa_dll_names:
        return False
    source_parts = {{part.lower() for part in Path(path).parts}}
    return 'maa' in source_parts

a.binaries = [
    (name, path, typecode)
    for name, path, typecode in a.binaries
    if not _is_maafw_binary(name, path)
]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{APP_NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='{APP_NAME}',
)
"""
    return spec


def _ensure_directml_only_ort() -> None:
    """Ensure onnxruntime-directml is installed and the CPU-only
    ``onnxruntime`` package is NOT present.

    rapidocr_onnxruntime declares ``onnxruntime>=1.7.0`` as a dependency,
    so any plain ``pip install -e .`` will pull in the CPU-only build,
    which lacks ``DmlExecutionProvider`` and overrides any existing
    onnxruntime-directml install (they share the same module name).

    Without this, OCR silently falls back to CPU at ~1.4s/call instead
    of ~0.2s/call on GPU — a >6x slowdown on every screenshot.
    """
    import importlib.metadata as md

    have_cpu = False
    have_dml = False
    for d in md.distributions():
        name = (d.metadata["Name"] or "").lower()
        if name == "onnxruntime":
            have_cpu = True
        elif name == "onnxruntime-directml":
            have_dml = True

    # onnxruntime and onnxruntime-directml share the same Python package
    # name. If both distributions are present, files can overwrite each
    # other and PyInstaller may package a broken runtime. Always restore
    # the DirectML wheel after removing the CPU wheel.
    print("Ensuring onnxruntime-directml is the active ORT runtime...")
    if have_cpu:
        subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", "onnxruntime"],
            check=True,
        )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--force-reinstall",
            "--no-deps",
            "onnxruntime-directml",
        ],
        check=True,
    )

    # Verify OCR runtime is importable before spending time on PyInstaller.
    try:
        import importlib
        importlib.invalidate_caches()
        import onnxruntime as ort
        importlib.reload(ort)
        provs = ort.get_available_providers()
        if "CPUExecutionProvider" not in provs:
            raise RuntimeError(f"ORT providers missing CPU fallback: {provs}")
        if "DmlExecutionProvider" not in provs:
            print(
                f"WARNING: DmlExecutionProvider not available. "
                f"OCR will use CPU fallback. Providers: {provs}"
            )
        else:
            print(f"OK: ORT providers = {provs}")
        from rapidocr_onnxruntime import RapidOCR
        print(f"OK: RapidOCR import = {RapidOCR}")
    except Exception as exc:
        raise SystemExit(f"FATAL: OCR runtime verification failed: {exc}") from exc


def build(skip_spec: bool = False) -> None:
    """Run the PyInstaller build."""
    # Step 0: Sanity-check ORT install — must be directml, not CPU.
    # Without this, the dist will OCR on CPU and be ~6x slower.
    _ensure_directml_only_ort()

    # Step 1: Generate .spec
    if not skip_spec:
        spec_content = generate_spec()
        SPEC_FILE.write_text(spec_content, encoding="utf-8")
        print(f"Generated {SPEC_FILE}")

    # Step 1.5: Preserve user files from existing dist before PyInstaller wipes it
    dist_app = DIST_DIR / APP_NAME
    _user_files = ("scheduler.json", "schedule_log.json", "ui_state.json", "user_config.yaml")
    _preserved_user: dict[str, bytes] = {}
    config_dst_pre = dist_app / "config"
    if config_dst_pre.exists():
        for uf in _user_files:
            uf_path = config_dst_pre / uf
            if uf_path.exists():
                _preserved_user[uf] = uf_path.read_bytes()
        if _preserved_user:
            print(f"Preserved {len(_preserved_user)} user files before rebuild: {list(_preserved_user.keys())}")

    # Step 2: Run PyInstaller
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(SPEC_FILE),
        "--noconfirm",
        "--clean",
    ]
    print(f"\nRunning: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print(f"\nBuild FAILED (exit code {result.returncode})")
        sys.exit(1)

    # Step 3: Post-build — copy MaaFw DLLs, strip unnecessary files, copy user dirs
    dist_app = DIST_DIR / APP_NAME
    if dist_app.exists():
        internal = dist_app / "_internal"

        # Copy MaaFw DLLs manually (bypassing PyInstaller's binary handling entirely)
        # This avoids bootloader preload failures and reclassification issues.
        maa_bin_src = SITE_PACKAGES / "maa" / "bin"
        maa_bin_dst = internal / "maa" / "bin"
        if maa_bin_src.exists():
            if maa_bin_dst.exists():
                shutil.rmtree(maa_bin_dst)
            shutil.copytree(str(maa_bin_src), str(maa_bin_dst))
            print(f"Copied MaaFw DLLs -> {maa_bin_dst}")

        # Remove opencv ffmpeg DLL (~28MB, not needed for screenshots)
        for ffmpeg in internal.rglob("opencv_videoio_ffmpeg*.dll"):
            print(f"Removing unnecessary {ffmpeg.name} ({ffmpeg.stat().st_size // (1024*1024)}MB)")
            ffmpeg.unlink()

        # ── MSVCP140 DLL conflict (CRITICAL — read before changing) ──
        # PyInstaller bundles msvcp140.dll in _internal/. This version
        # conflicts with MaaFw's opencv_world4_maa.dll, causing WinError
        # 1114 (DllMain initialization failure).
        #
        # We MUST remove it so the system's copy (from VC++ Redistributable)
        # is used instead. This means VC++ 2015-2022 Redistributable is a
        # HARD REQUIREMENT for end users.
        #
        # Trade-off:
        #   - WITH these DLLs: App starts but MaaFw crashes → tasks fail
        #   - WITHOUT these DLLs: App won't start if VC++ not installed
        #   We chose "won't start" because it's a clear, one-time fixable
        #   error, whereas MaaFw crashes are confusing and unfixable.
        #
        # If you're tempted to revert this, see memory/17-packaging-v003-fixes.md
        # and test BOTH scenarios on a clean Windows install.
        for msvcp in ("MSVCP140_1.dll", "msvcp140.dll"):
            p = internal / msvcp
            if p.exists():
                print(f"Removing conflicting {msvcp} (MaaFw compatibility)")
                p.unlink()

        # Remove any leftover excluded packages that PyInstaller may have kept
        # WARNING: Do NOT add 'bottle' here — pywebview depends on it.
        # See memory/17-packaging-v003-fixes.md for the full story.
        for pkg_name in ["sympy", "mpmath", "pytesseract"]:
            pkg_dir = internal / pkg_name
            if pkg_dir.exists() and pkg_dir.is_dir():
                size_mb = sum(f.stat().st_size for f in pkg_dir.rglob("*") if f.is_file()) // (1024*1024)
                print(f"Removing unnecessary {pkg_name}/ ({size_mb}MB)")
                shutil.rmtree(pkg_dir)

        # Copy config/ to dist top-level (user-editable)
        # Merge: copy source config, but preserve user runtime files
        config_src = PROJECT_ROOT / "config"
        config_dst = dist_app / "config"
        if config_src.exists():
            if not config_dst.exists():
                shutil.copytree(config_src, config_dst)
            else:
                # Overlay source files onto existing config dir
                for item in config_src.rglob("*"):
                    if item.is_file():
                        rel = item.relative_to(config_src)
                        dst_file = config_dst / rel
                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dst_file)

            # Restore user files preserved before PyInstaller wiped dist/
            for uf, data in _preserved_user.items():
                (config_dst / uf).write_bytes(data)

            print(f"Copied config/ -> {config_dst} (restored {len(_preserved_user)} user files)")

        # Copy plans/ to dist top-level (user-editable, also found by launcher)
        plans_src = dist_app / "_internal" / "plans"
        plans_dst = dist_app / "plans"
        if plans_src.exists() and not plans_dst.exists():
            shutil.copytree(plans_src, plans_dst)
            print(f"Copied plans/ -> {plans_dst}")

        # Ensure logs/ dir exists
        (dist_app / "logs").mkdir(exist_ok=True)

        # Generate start.bat — checks VC++ runtime before launching exe
        start_bat = dist_app / "start.bat"
        start_bat.write_text(
            '@echo off\r\n'
            'chcp 65001 >nul 2>&1\r\n'
            'where /Q msvcp140.dll\r\n'
            'if errorlevel 1 (\r\n'
            '    echo [错误] 未检测到 Visual C++ 运行库\r\n'
            '    echo.\r\n'
            '    echo 请下载安装 VC++ 2015-2022 Redistributable (x64):\r\n'
            '    echo https://aka.ms/vs/17/release/vc_redist.x64.exe\r\n'
            '    echo.\r\n'
            '    echo 安装完成后重新运行此脚本。\r\n'
            '    echo.\r\n'
            '    start https://aka.ms/vs/17/release/vc_redist.x64.exe\r\n'
            '    pause\r\n'
            '    exit /b 1\r\n'
            ')\r\n'
            'start "" "%~dp0anime-game-afk.exe"\r\n',
            encoding='utf-8',
        )
        print(f"Generated {start_bat}")

        # Print final size
        total = sum(f.stat().st_size for f in dist_app.rglob("*") if f.is_file())
        print(f"\nBuild SUCCESS!")
        print(f"Output: {dist_app} ({total // (1024*1024)} MB)")
        print(f"Output: {dist_app}")
        print(f"\nTo run: {dist_app / f'{APP_NAME}.exe'}")
    else:
        print(f"\nWARNING: Expected output dir {dist_app} not found")


def create_zip() -> None:
    """Create a ZIP archive of the distribution."""
    dist_app = DIST_DIR / APP_NAME
    if not dist_app.exists():
        print(f"ERROR: {dist_app} does not exist. Run build first.")
        sys.exit(1)

    zip_path = DIST_DIR / APP_NAME
    print(f"Creating {zip_path}.zip ...")
    shutil.make_archive(str(zip_path), "zip", str(DIST_DIR), APP_NAME)
    zip_file = Path(f"{zip_path}.zip")
    size_mb = zip_file.stat().st_size / (1024 * 1024)
    print(f"Archive created: {zip_file} ({size_mb:.1f} MB)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build anime-game-afk distribution")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts first")
    parser.add_argument("--zip", action="store_true", help="Also create ZIP archive")
    parser.add_argument(
        "--spec-only", action="store_true", help="Only regenerate .spec file"
    )
    args = parser.parse_args()

    if args.clean:
        clean()

    if args.spec_only:
        spec_content = generate_spec()
        SPEC_FILE.write_text(spec_content, encoding="utf-8")
        print(f"Generated {SPEC_FILE}")
        return

    build()

    if args.zip:
        create_zip()


if __name__ == "__main__":
    main()
