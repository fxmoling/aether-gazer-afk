"""Recovery strategy framework for infrastructure failures.

Provides a base ``RecoveryStrategy`` and common implementations.

Game-specific recovery belongs in the game layer, not here.

Example::

    def reconnect() -> bool:
        return adb.connect()

    strategy = RetryStrategy(reconnect, max_retries=3, backoff=0.5)
    if not strategy.attempt():
        fallback.attempt()
"""
from __future__ import annotations

import time
from typing import Callable


class RecoveryStrategy:
    """Abstract base for recovery strategies.

    Subclasses must implement :py:meth:`attempt`.
    """

    def attempt(self) -> bool:
        """Try to recover from a failure.

        Returns:
            True if recovery succeeded, False otherwise.
        """
        raise NotImplementedError


class RetryStrategy(RecoveryStrategy):
    """Retry an action up to *max_retries* times with linear back-off.

    Each successive attempt waits ``backoff * attempt_number`` seconds
    before executing, giving transient failures time to resolve.
    """

    def __init__(
        self,
        action: Callable[[], bool],
        max_retries: int = 3,
        backoff: float = 1.0,
    ) -> None:
        self._action = action
        self._max_retries = max_retries
        self._backoff = backoff
        self._attempts = 0

    def attempt(self) -> bool:
        """Execute *action* up to *max_retries* times.

        Returns True on first success; False if all attempts fail.
        """
        for i in range(self._max_retries):
            self._attempts = i + 1
            if self._action():
                return True
            time.sleep(self._backoff * (i + 1))
        return False

    @property
    def attempts(self) -> int:
        """Number of action invocations made in the last :py:meth:`attempt` call."""
        return self._attempts


class FallbackStrategy(RecoveryStrategy):
    """Try a chain of strategies in order; first success wins.

    Useful for multi-tier recovery: e.g. try soft-reset, then hard-reset.
    """

    def __init__(self, strategies: list[RecoveryStrategy]) -> None:
        self._strategies = strategies

    def attempt(self) -> bool:
        """Attempt each strategy in sequence.

        Returns True as soon as one succeeds; False if all fail.
        """
        for strategy in self._strategies:
            if strategy.attempt():
                return True
        return False
