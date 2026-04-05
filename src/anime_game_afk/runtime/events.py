"""Infrastructure-level event bus.

Handles ONLY infrastructure events:

- ``device_disconnected``
- ``window_lost``
- ``screenshot_timeout``
- ``unhandled_exception``
- ``session_expired``

Game events (``battle_started``, ``character_died``, …) belong in the
game layer, not here.

Example::

    bus = EventBus()

    def on_lost(**kw):
        print("window lost:", kw)

    bus.on(WINDOW_LOST, on_lost)
    bus.emit(WINDOW_LOST, reason="process_exited")
    bus.off(WINDOW_LOST, on_lost)
"""
from __future__ import annotations

from typing import Any, Callable

from loguru import logger as _loguru

EventHandler = Callable[..., None]

# ---------------------------------------------------------------------------
# Standard infrastructure event names
# ---------------------------------------------------------------------------

DEVICE_DISCONNECTED = "device_disconnected"
WINDOW_LOST = "window_lost"
SCREENSHOT_TIMEOUT = "screenshot_timeout"
UNHANDLED_EXCEPTION = "unhandled_exception"
SESSION_EXPIRED = "session_expired"


class EventBus:
    """Simple pub/sub event bus for infrastructure events.

    Handlers are called synchronously in registration order.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def on(self, event: str, handler: EventHandler) -> None:
        """Register *handler* to be called when *event* is emitted."""
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def off(self, event: str, handler: EventHandler) -> None:
        """Unregister *handler* from *event*.

        No-op if the handler was never registered.
        """
        if event in self._handlers:
            self._handlers[event] = [
                h for h in self._handlers[event] if h is not handler
            ]

    def clear(self) -> None:
        """Remove all registered handlers for all events."""
        self._handlers.clear()

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def emit(self, event: str, **kwargs: Any) -> None:
        """Call every handler registered for *event*, passing *kwargs*.

        A failing handler is logged and skipped — it does NOT prevent
        subsequent handlers from running.
        """
        for handler in self._handlers.get(event, []):
            try:
                handler(**kwargs)
            except Exception:
                _loguru.opt(depth=1).exception(
                    "Handler {!r} failed for event {!r}", handler, event
                )
