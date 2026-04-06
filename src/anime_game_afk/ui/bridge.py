"""Log forwarding bridge: loguru sink → pywebview evaluate_js.

Captures log entries into a ring buffer and pushes them to the
frontend in real time via window.evaluate_js().
"""
from __future__ import annotations

import collections
import json
import threading
from datetime import datetime
from typing import Any

from loguru import logger as _loguru


class LogForwarder:
    """Loguru sink that forwards log entries to the browser frontend."""

    def __init__(self, maxlen: int = 500) -> None:
        self._buffer: collections.deque[dict[str, str]] = collections.deque(
            maxlen=maxlen,
        )
        self._lock = threading.Lock()
        self._window: Any = None  # webview.Window, lazy-bound
        self._sink_id: int | None = None

    def install(self) -> int:
        """Add this forwarder as a loguru sink. Returns the sink ID."""
        self._sink_id = _loguru.add(
            self._sink,
            format="{message}",
            level="DEBUG",
        )
        return self._sink_id

    def uninstall(self) -> None:
        """Remove the loguru sink."""
        if self._sink_id is not None:
            _loguru.remove(self._sink_id)
            self._sink_id = None

    def bind_window(self, window: Any) -> None:
        """Bind a pywebview window for evaluate_js push."""
        self._window = window

    def get_recent(self, count: int = 100) -> list[dict[str, str]]:
        """Return the last *count* log entries from the buffer."""
        with self._lock:
            items = list(self._buffer)
        return items[-count:]

    def _sink(self, message: Any) -> None:
        """Loguru sink callback — called for every log record."""
        record = message.record
        entry = {
            "time": record["time"].strftime("%H:%M:%S"),
            "level": record["level"].name,
            "message": record["message"],
        }
        with self._lock:
            self._buffer.append(entry)

        # Push to frontend if window is bound
        window = self._window
        if window is not None:
            try:
                js_payload = json.dumps(entry, ensure_ascii=False)
                window.evaluate_js(f"window.appendLog && window.appendLog({js_payload})")
            except Exception:
                pass  # Window may be closing
