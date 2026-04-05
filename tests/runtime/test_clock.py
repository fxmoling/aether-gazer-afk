"""Tests for runtime.clock — Cooldown and Timer utilities."""
from __future__ import annotations

import time

from anime_game_afk.runtime.clock import Cooldown, Timer


# ---------------------------------------------------------------------------
# Cooldown — initial state
# ---------------------------------------------------------------------------


def test_cooldown_ready_before_first_trigger() -> None:
    """A freshly created Cooldown should be ready immediately."""
    cd = Cooldown(duration=10.0)
    assert cd.ready is True


def test_cooldown_remaining_before_first_trigger() -> None:
    """Before first trigger the remaining time is 0 (cooldown never started)."""
    cd = Cooldown(duration=10.0)
    assert cd.remaining == 0.0


# ---------------------------------------------------------------------------
# Cooldown — after trigger
# ---------------------------------------------------------------------------


def test_cooldown_not_ready_immediately_after_trigger() -> None:
    cd = Cooldown(duration=5.0)
    cd.trigger()
    assert cd.ready is False


def test_cooldown_remaining_positive_after_trigger() -> None:
    cd = Cooldown(duration=5.0)
    cd.trigger()
    assert cd.remaining > 0.0
    assert cd.remaining <= 5.0


# ---------------------------------------------------------------------------
# Cooldown — elapsed
# ---------------------------------------------------------------------------


def test_cooldown_ready_after_duration_elapses() -> None:
    cd = Cooldown(duration=0.05)
    cd.trigger()
    assert cd.ready is False
    time.sleep(0.08)
    assert cd.ready is True


def test_cooldown_remaining_zero_when_ready() -> None:
    cd = Cooldown(duration=0.05)
    cd.trigger()
    time.sleep(0.08)
    assert cd.remaining == 0.0


# ---------------------------------------------------------------------------
# Cooldown — zero duration
# ---------------------------------------------------------------------------


def test_cooldown_zero_duration_always_ready() -> None:
    cd = Cooldown(duration=0.0)
    cd.trigger()
    assert cd.ready is True


# ---------------------------------------------------------------------------
# Timer — initial state
# ---------------------------------------------------------------------------


def test_timer_not_running_initially() -> None:
    t = Timer()
    assert t.running is False


def test_timer_elapsed_zero_when_not_running() -> None:
    t = Timer()
    assert t.elapsed == 0.0


def test_timer_name_stored() -> None:
    t = Timer(name="screenshot")
    assert t.name == "screenshot"


def test_timer_default_name_empty_string() -> None:
    t = Timer()
    assert t.name == ""


# ---------------------------------------------------------------------------
# Timer — start / elapsed while running
# ---------------------------------------------------------------------------


def test_timer_running_after_start() -> None:
    t = Timer()
    t.start()
    assert t.running is True


def test_timer_elapsed_positive_while_running() -> None:
    t = Timer()
    t.start()
    time.sleep(0.05)
    assert t.elapsed > 0.0


def test_timer_elapsed_increases_over_time() -> None:
    t = Timer()
    t.start()
    time.sleep(0.05)
    e1 = t.elapsed
    time.sleep(0.05)
    e2 = t.elapsed
    assert e2 > e1


# ---------------------------------------------------------------------------
# Timer — stop
# ---------------------------------------------------------------------------


def test_timer_stop_returns_elapsed_seconds() -> None:
    t = Timer()
    t.start()
    time.sleep(0.05)
    elapsed = t.stop()
    assert elapsed >= 0.04  # allow small timing jitter


def test_timer_not_running_after_stop() -> None:
    t = Timer()
    t.start()
    t.stop()
    assert t.running is False


def test_timer_elapsed_zero_after_stop() -> None:
    """elapsed property returns 0.0 once the timer is stopped."""
    t = Timer()
    t.start()
    t.stop()
    assert t.elapsed == 0.0


def test_timer_stop_without_start_returns_zero() -> None:
    t = Timer()
    assert t.stop() == 0.0


# ---------------------------------------------------------------------------
# Timer — restart
# ---------------------------------------------------------------------------


def test_timer_can_be_restarted() -> None:
    t = Timer()
    t.start()
    time.sleep(0.05)
    t.stop()
    t.start()
    assert t.running is True
    assert t.elapsed < 0.05  # fresh start, should be much less than first run
