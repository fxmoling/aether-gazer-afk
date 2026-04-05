"""Tests for runtime.events — EventBus pub/sub infrastructure bus."""
from __future__ import annotations

from anime_game_afk.runtime.events import (
    DEVICE_DISCONNECTED,
    SESSION_EXPIRED,
    SCREENSHOT_TIMEOUT,
    UNHANDLED_EXCEPTION,
    WINDOW_LOST,
    EventBus,
)


# ---------------------------------------------------------------------------
# on / emit — basic
# ---------------------------------------------------------------------------


def test_emit_calls_registered_handler() -> None:
    bus = EventBus()
    received: list[str] = []

    def handler(**kw: object) -> None:
        received.append("fired")

    bus.on(WINDOW_LOST, handler)
    bus.emit(WINDOW_LOST)
    assert received == ["fired"]


def test_emit_passes_kwargs_to_handler() -> None:
    bus = EventBus()
    captured: dict[str, object] = {}

    def handler(**kw: object) -> None:
        captured.update(kw)

    bus.on(DEVICE_DISCONNECTED, handler)
    bus.emit(DEVICE_DISCONNECTED, device_id="emulator-5554", code=1)
    assert captured == {"device_id": "emulator-5554", "code": 1}


def test_emit_unknown_event_is_noop() -> None:
    """Emitting an event with no handlers must not raise."""
    bus = EventBus()
    bus.emit("no_one_listens")  # should not raise


# ---------------------------------------------------------------------------
# Multiple handlers for the same event
# ---------------------------------------------------------------------------


def test_multiple_handlers_all_called() -> None:
    bus = EventBus()
    log: list[int] = []

    bus.on(SCREENSHOT_TIMEOUT, lambda **kw: log.append(1))
    bus.on(SCREENSHOT_TIMEOUT, lambda **kw: log.append(2))
    bus.on(SCREENSHOT_TIMEOUT, lambda **kw: log.append(3))

    bus.emit(SCREENSHOT_TIMEOUT)
    assert log == [1, 2, 3]


def test_handlers_called_in_registration_order() -> None:
    bus = EventBus()
    order: list[str] = []

    bus.on(SESSION_EXPIRED, lambda **kw: order.append("first"))
    bus.on(SESSION_EXPIRED, lambda **kw: order.append("second"))

    bus.emit(SESSION_EXPIRED)
    assert order == ["first", "second"]


# ---------------------------------------------------------------------------
# off
# ---------------------------------------------------------------------------


def test_off_removes_handler() -> None:
    bus = EventBus()
    fired: list[bool] = []

    def handler(**kw: object) -> None:
        fired.append(True)

    bus.on(WINDOW_LOST, handler)
    bus.off(WINDOW_LOST, handler)
    bus.emit(WINDOW_LOST)
    assert fired == []


def test_off_removes_only_specified_handler() -> None:
    """off() must not affect other handlers on the same event."""
    bus = EventBus()
    log: list[str] = []

    def h1(**kw: object) -> None:
        log.append("h1")

    def h2(**kw: object) -> None:
        log.append("h2")

    bus.on(UNHANDLED_EXCEPTION, h1)
    bus.on(UNHANDLED_EXCEPTION, h2)
    bus.off(UNHANDLED_EXCEPTION, h1)
    bus.emit(UNHANDLED_EXCEPTION)
    assert log == ["h2"]


def test_off_unregistered_handler_is_noop() -> None:
    """Calling off() for a handler that was never registered must not raise."""
    bus = EventBus()

    def ghost(**kw: object) -> None:
        pass  # pragma: no cover

    bus.off(WINDOW_LOST, ghost)  # should not raise


def test_off_unknown_event_is_noop() -> None:
    bus = EventBus()

    def h(**kw: object) -> None:
        pass  # pragma: no cover

    bus.off("nonexistent_event", h)  # should not raise


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


def test_clear_removes_all_handlers() -> None:
    bus = EventBus()
    fired: list[bool] = []

    bus.on(WINDOW_LOST, lambda **kw: fired.append(True))
    bus.on(DEVICE_DISCONNECTED, lambda **kw: fired.append(True))
    bus.clear()

    bus.emit(WINDOW_LOST)
    bus.emit(DEVICE_DISCONNECTED)
    assert fired == []


# ---------------------------------------------------------------------------
# Standard event name constants are exported
# ---------------------------------------------------------------------------


def test_standard_event_name_constants() -> None:
    assert DEVICE_DISCONNECTED == "device_disconnected"
    assert WINDOW_LOST == "window_lost"
    assert SCREENSHOT_TIMEOUT == "screenshot_timeout"
    assert UNHANDLED_EXCEPTION == "unhandled_exception"
    assert SESSION_EXPIRED == "session_expired"


# ---------------------------------------------------------------------------
# Same handler registered twice emits twice
# ---------------------------------------------------------------------------


def test_same_handler_registered_twice_fires_twice() -> None:
    bus = EventBus()
    count: list[int] = []

    def handler(**kw: object) -> None:
        count.append(1)

    bus.on(WINDOW_LOST, handler)
    bus.on(WINDOW_LOST, handler)
    bus.emit(WINDOW_LOST)
    assert len(count) == 2
