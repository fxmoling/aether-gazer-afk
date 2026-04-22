"""Tests for runtime.logger — structured logging wrapper around loguru."""
from __future__ import annotations

import sys

import pytest
from loguru import logger as _loguru

from anime_game_afk.runtime.logger import Logger, get_logger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _capture_logs(level: str = "DEBUG") -> list[str]:
    """Return a mutable list; loguru will append formatted records to it."""
    return []


def _install_sink(records: list[str], level: str = "DEBUG") -> int:
    """Add a string sink to loguru and return the sink id."""
    sink_id = _loguru.add(
        records.append,
        level=level,
        format="{level}|{message}",
        colorize=False,
    )
    return sink_id


def _remove_sink(sink_id: int) -> None:
    _loguru.remove(sink_id)


# ---------------------------------------------------------------------------
# get_logger
# ---------------------------------------------------------------------------


def test_get_logger_returns_logger_instance() -> None:
    log = get_logger("test_module")
    assert isinstance(log, Logger)


def test_get_logger_stores_name() -> None:
    log = get_logger("my_component")
    assert log.name == "my_component"


def test_get_logger_no_context_by_default() -> None:
    log = get_logger("x")
    assert log.context == {}


# ---------------------------------------------------------------------------
# Emission — info / debug / warning / error
# ---------------------------------------------------------------------------


def test_info_emits_message() -> None:
    records: list[str] = []
    sid = _install_sink(records)
    try:
        log = get_logger("emu")
        log.info("hello world")
    finally:
        _remove_sink(sid)

    assert any("hello world" in r for r in records)


def test_debug_emits_message() -> None:
    records: list[str] = []
    sid = _install_sink(records, level="DEBUG")
    try:
        get_logger("emu").debug("debug msg")
    finally:
        _remove_sink(sid)

    assert any("debug msg" in r for r in records)


def test_warning_emits_message() -> None:
    records: list[str] = []
    sid = _install_sink(records)
    try:
        get_logger("emu").warning("watch out")
    finally:
        _remove_sink(sid)

    assert any("watch out" in r for r in records)


def test_error_emits_message() -> None:
    records: list[str] = []
    sid = _install_sink(records)
    try:
        get_logger("emu").error("something broke")
    finally:
        _remove_sink(sid)

    assert any("something broke" in r for r in records)


def test_level_prefix_appears_in_output() -> None:
    """The loguru level label should appear in the formatted record."""
    records: list[str] = []
    sid = _install_sink(records)
    try:
        get_logger("emu").info("level check")
    finally:
        _remove_sink(sid)

    assert any("INFO" in r for r in records)


# ---------------------------------------------------------------------------
# Name prefix in message
# ---------------------------------------------------------------------------


def test_logger_name_appears_in_message() -> None:
    records: list[str] = []
    sid = _install_sink(records)
    try:
        get_logger("aether_gazer").info("started")
    finally:
        _remove_sink(sid)

    assert any("[aether_gazer]" in r for r in records)


# ---------------------------------------------------------------------------
# Message formatting with positional args
# ---------------------------------------------------------------------------


def test_message_format_with_single_arg() -> None:
    records: list[str] = []
    sid = _install_sink(records)
    try:
        get_logger("fmt").info("value={}", 42)
    finally:
        _remove_sink(sid)

    assert any("value=42" in r for r in records)


def test_message_format_with_multiple_args() -> None:
    records: list[str] = []
    sid = _install_sink(records)
    try:
        get_logger("fmt").info("{} + {} = {}", 1, 2, 3)
    finally:
        _remove_sink(sid)

    assert any("1 + 2 = 3" in r for r in records)


def test_message_format_bad_placeholder_does_not_raise() -> None:
    """If placeholder count doesn't match args, emit raw msg without crashing."""
    log = get_logger("fmt")
    records: list[str] = []
    sid = _install_sink(records)
    try:
        # More placeholders than args — should not raise
        log.info("{} {} {}", "only_one")
    finally:
        _remove_sink(sid)
    # At minimum, something was logged
    assert records


# ---------------------------------------------------------------------------
# with_context
# ---------------------------------------------------------------------------


def test_with_context_returns_new_logger() -> None:
    parent = get_logger("parent")
    child = parent.with_context(task="login")
    assert child is not parent
    assert isinstance(child, Logger)


def test_with_context_preserves_name() -> None:
    child = get_logger("comp").with_context(step="1")
    assert child.name == "comp"


def test_with_context_merges_keys() -> None:
    parent = get_logger("comp").with_context(game="ag")
    child = parent.with_context(task="daily")
    assert child.context == {"game": "ag", "task": "daily"}


def test_with_context_new_key_overrides_existing() -> None:
    parent = get_logger("comp").with_context(step="a")
    child = parent.with_context(step="b")
    assert child.context["step"] == "b"


def test_with_context_parent_unchanged() -> None:
    parent = get_logger("comp").with_context(game="ag")
    _child = parent.with_context(task="daily")
    assert "task" not in parent.context


def test_with_context_appears_in_log_output() -> None:
    records: list[str] = []
    sid = _install_sink(records)
    try:
        log = get_logger("comp").with_context(task="grind", step="3")
        log.info("fighting")
    finally:
        _remove_sink(sid)

    combined = " ".join(records)
    assert "task=grind" in combined
    assert "step=3" in combined
    assert "fighting" in combined


def test_no_context_no_brackets_in_message() -> None:
    records: list[str] = []
    sid = _install_sink(records)
    try:
        get_logger("bare").info("clean message")
    finally:
        _remove_sink(sid)

    # The message body should not contain a context block like " [key=val]"
    assert any("[bare]  clean message" not in r and "clean message" in r for r in records)
    # Ensure no spurious extra brackets appear between name and message
    assert not any("[bare] [" in r for r in records)


# ---------------------------------------------------------------------------
# context property
# ---------------------------------------------------------------------------


def test_context_property_returns_copy() -> None:
    """Mutating the returned dict must not affect the logger."""
    log = get_logger("x").with_context(a=1)
    ctx = log.context
    ctx["a"] = 999
    assert log.context["a"] == 1


# ---------------------------------------------------------------------------
# Keyword formatting
# ---------------------------------------------------------------------------


def test_keyword_formatting() -> None:
    """Logger._log should resolve {keyword} placeholders from kwargs."""
    records: list[str] = []
    sid = _install_sink(records)
    try:
        get_logger("kw").info("count: {n}/{total}", n=3, total=10)
    finally:
        _remove_sink(sid)

    assert any("count: 3/10" in r for r in records)
    assert not any("{n}" in r for r in records)


def test_mixed_positional_and_keyword_formatting() -> None:
    """Logger._log should handle both positional and keyword args together."""
    records: list[str] = []
    sid = _install_sink(records)
    try:
        get_logger("mix").info("{} items in {place}", 5, place="shop")
    finally:
        _remove_sink(sid)

    assert any("5 items in shop" in r for r in records)


def test_keyword_formatting_bad_key_does_not_crash() -> None:
    """Mismatched keyword names should not raise."""
    records: list[str] = []
    sid = _install_sink(records)
    try:
        get_logger("kw").info("no placeholder here", extra="unused")
    finally:
        _remove_sink(sid)

    assert any("no placeholder here" in r for r in records)
