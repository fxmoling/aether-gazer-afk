"""Time utilities — cooldowns, timers.

Thin wrappers around ``time.monotonic`` for game-automation timing.

Example::

    cd = Cooldown(5.0)
    cd.ready        # True  (never triggered)
    cd.trigger()
    cd.ready        # False (just triggered)

    t = Timer("screenshot")
    t.start()
    t.elapsed       # seconds since start
    elapsed = t.stop()
"""
from __future__ import annotations

import time


class Cooldown:
    """Track whether enough time has passed since the last trigger.

    Uses ``time.monotonic`` so it is immune to system-clock adjustments.
    """

    def __init__(self, duration: float) -> None:
        self._duration = duration
        self._last_trigger: float = 0.0

    @property
    def ready(self) -> bool:
        """True if the cooldown period has fully elapsed."""
        return (time.monotonic() - self._last_trigger) >= self._duration

    def trigger(self) -> None:
        """Mark 'now' as the last trigger time, resetting the cooldown."""
        self._last_trigger = time.monotonic()

    @property
    def remaining(self) -> float:
        """Seconds until the cooldown becomes ready; 0.0 if already ready."""
        elapsed = time.monotonic() - self._last_trigger
        return max(0.0, self._duration - elapsed)


class Timer:
    """Measure elapsed time for a named operation.

    Designed for lightweight profiling of game-automation steps.
    """

    def __init__(self, name: str = "") -> None:
        self.name = name
        self._start: float = 0.0
        self._running = False

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin timing."""
        self._start = time.monotonic()
        self._running = True

    def stop(self) -> float:
        """Stop timing and return elapsed seconds.

        Returns 0.0 if the timer was not running.
        """
        if not self._running:
            return 0.0
        self._running = False
        return time.monotonic() - self._start

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    @property
    def elapsed(self) -> float:
        """Seconds since ``start()`` was last called.

        Returns the live reading while running; 0.0 when stopped.
        """
        if self._running:
            return time.monotonic() - self._start
        return 0.0

    @property
    def running(self) -> bool:
        """True while the timer is active."""
        return self._running
