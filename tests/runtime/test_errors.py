"""Tests for runtime.errors — RecoveryStrategy framework."""
from __future__ import annotations

import pytest

from anime_game_afk.runtime.errors import (
    FallbackStrategy,
    RecoveryStrategy,
    RetryStrategy,
)


# ---------------------------------------------------------------------------
# RecoveryStrategy base — attempt() raises NotImplementedError
# ---------------------------------------------------------------------------


def test_base_strategy_attempt_raises() -> None:
    strategy = RecoveryStrategy()
    with pytest.raises(NotImplementedError):
        strategy.attempt()


# ---------------------------------------------------------------------------
# RetryStrategy — success on first try
# ---------------------------------------------------------------------------


def test_retry_success_on_first_attempt() -> None:
    calls: list[int] = []

    def action() -> bool:
        calls.append(1)
        return True

    strategy = RetryStrategy(action, max_retries=3, backoff=0.0)
    result = strategy.attempt()

    assert result is True
    assert len(calls) == 1
    assert strategy.attempts == 1


# ---------------------------------------------------------------------------
# RetryStrategy — success on third attempt
# ---------------------------------------------------------------------------


def test_retry_success_on_third_attempt() -> None:
    calls: list[int] = []

    def action() -> bool:
        calls.append(1)
        return len(calls) >= 3  # fail twice, succeed on third

    strategy = RetryStrategy(action, max_retries=5, backoff=0.0)
    result = strategy.attempt()

    assert result is True
    assert len(calls) == 3
    assert strategy.attempts == 3


# ---------------------------------------------------------------------------
# RetryStrategy — all retries exhausted
# ---------------------------------------------------------------------------


def test_retry_exhaustion_returns_false() -> None:
    calls: list[int] = []

    def action() -> bool:
        calls.append(1)
        return False

    strategy = RetryStrategy(action, max_retries=3, backoff=0.0)
    result = strategy.attempt()

    assert result is False
    assert len(calls) == 3
    assert strategy.attempts == 3


def test_retry_default_max_retries_is_3() -> None:
    calls: list[int] = []

    def action() -> bool:
        calls.append(1)
        return False

    strategy = RetryStrategy(action, backoff=0.0)
    strategy.attempt()
    assert len(calls) == 3


# ---------------------------------------------------------------------------
# RetryStrategy — attempts property tracks count
# ---------------------------------------------------------------------------


def test_retry_attempts_zero_before_calling() -> None:
    strategy = RetryStrategy(lambda: False, backoff=0.0)
    assert strategy.attempts == 0


# ---------------------------------------------------------------------------
# FallbackStrategy — first strategy succeeds
# ---------------------------------------------------------------------------


def test_fallback_first_succeeds() -> None:
    s1 = RetryStrategy(lambda: True, max_retries=1, backoff=0.0)
    s2 = RetryStrategy(lambda: True, max_retries=1, backoff=0.0)

    fb = FallbackStrategy([s1, s2])
    result = fb.attempt()
    assert result is True
    # s2 should not have been called (s1 already succeeded)
    assert s2.attempts == 0


# ---------------------------------------------------------------------------
# FallbackStrategy — first fails, second succeeds
# ---------------------------------------------------------------------------


def test_fallback_second_succeeds() -> None:
    s1 = RetryStrategy(lambda: False, max_retries=1, backoff=0.0)
    s2 = RetryStrategy(lambda: True, max_retries=1, backoff=0.0)

    fb = FallbackStrategy([s1, s2])
    result = fb.attempt()
    assert result is True
    assert s1.attempts == 1
    assert s2.attempts == 1


# ---------------------------------------------------------------------------
# FallbackStrategy — all strategies fail
# ---------------------------------------------------------------------------


def test_fallback_all_fail_returns_false() -> None:
    s1 = RetryStrategy(lambda: False, max_retries=1, backoff=0.0)
    s2 = RetryStrategy(lambda: False, max_retries=1, backoff=0.0)
    s3 = RetryStrategy(lambda: False, max_retries=1, backoff=0.0)

    fb = FallbackStrategy([s1, s2, s3])
    result = fb.attempt()
    assert result is False
    assert s1.attempts == 1
    assert s2.attempts == 1
    assert s3.attempts == 1


# ---------------------------------------------------------------------------
# FallbackStrategy — empty list
# ---------------------------------------------------------------------------


def test_fallback_empty_list_returns_false() -> None:
    fb = FallbackStrategy([])
    assert fb.attempt() is False


# ---------------------------------------------------------------------------
# FallbackStrategy — works with custom RecoveryStrategy subclass
# ---------------------------------------------------------------------------


class _AlwaysSuccess(RecoveryStrategy):
    def attempt(self) -> bool:
        return True


class _AlwaysFail(RecoveryStrategy):
    def attempt(self) -> bool:
        return False


def test_fallback_with_custom_subclasses() -> None:
    fb = FallbackStrategy([_AlwaysFail(), _AlwaysSuccess()])
    assert fb.attempt() is True


def test_fallback_all_custom_fail() -> None:
    fb = FallbackStrategy([_AlwaysFail(), _AlwaysFail()])
    assert fb.attempt() is False
