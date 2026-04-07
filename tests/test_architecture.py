"""Architecture validation tests.

Ensures layer boundaries and module existence constraints are met.
"""
import importlib
from pathlib import Path

import pytest

# Task source directory
_TASKS_DIR = Path(__file__).resolve().parent.parent / (
    "src/anime_game_afk/games/aether_gazer/tasks"
)


def _task_files() -> list[Path]:
    """Return all task .py files, excluding base.py and helpers.py."""
    return [
        f for f in _TASKS_DIR.glob("*.py")
        if f.name not in ("__init__.py", "base.py", "helpers.py")
    ]


def test_tasks_do_not_call_device():
    """Task files should not call ctx.device.* directly."""
    for task_file in _task_files():
        source = task_file.read_text(encoding="utf-8")
        assert "ctx.device." not in source, (
            f"{task_file.name} violates rule: task must not call ctx.device.* "
            f"directly — use Op classes instead"
        )


def test_tasks_do_not_import_vision():
    """Task files should not import from anime_game_afk.vision."""
    for task_file in _task_files():
        source = task_file.read_text(encoding="utf-8")
        assert "from anime_game_afk.vision" not in source, (
            f"{task_file.name} violates rule: task must not import vision "
            f"functions directly — use Check classes instead"
        )


# ── Checks package existence ──


def test_checks_base_importable():
    mod = importlib.import_module(
        "anime_game_afk.games.aether_gazer.checks.base"
    )
    assert hasattr(mod, "CheckResult")
    assert hasattr(mod, "Check")


def test_checks_ocr_importable():
    mod = importlib.import_module(
        "anime_game_afk.games.aether_gazer.checks.ocr"
    )
    assert hasattr(mod, "HasTextCheck")
    assert hasattr(mod, "FindTextCheck")
    assert hasattr(mod, "FindAllTextCheck")
    assert hasattr(mod, "OcrScanCheck")
    assert hasattr(mod, "OcrFullCheck")


def test_checks_page_importable():
    mod = importlib.import_module(
        "anime_game_afk.games.aether_gazer.checks.page"
    )
    assert hasattr(mod, "OnPageCheck")
    assert hasattr(mod, "IdentifyPageCheck")
    assert hasattr(mod, "AtHubCheck")


def test_checks_state_importable():
    mod = importlib.import_module(
        "anime_game_afk.games.aether_gazer.checks.state"
    )
    assert hasattr(mod, "DetectGameStateCheck")
    assert hasattr(mod, "ScreenUnchangedCheck")


def test_checks_vision_importable():
    mod = importlib.import_module(
        "anime_game_afk.games.aether_gazer.checks.vision"
    )
    assert hasattr(mod, "TemplateMatchCheck")
    assert hasattr(mod, "HasColorCheck")


# ── Primitives existence ──


def test_primitives_all_importable():
    mod = importlib.import_module(
        "anime_game_afk.games.aether_gazer.ops.primitives"
    )
    assert hasattr(mod, "ClickOp")
    assert hasattr(mod, "PressKeyOp")
    assert hasattr(mod, "HoldKeyOp")
    assert hasattr(mod, "SwipeOp")
    assert hasattr(mod, "SleepOp")
    assert hasattr(mod, "ScreenshotOp")
