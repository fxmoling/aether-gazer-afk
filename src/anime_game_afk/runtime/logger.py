"""Structured logging for the automation framework.

Wraps loguru with context tags (game, task, step) for structured output.
"""
from __future__ import annotations

from typing import Any

from loguru import logger as _loguru


def get_logger(name: str) -> "Logger":
    """Get a structured logger with the given name."""
    return Logger(name)


class Logger:
    """Structured logger that adds context to all messages.

    Context key/value pairs are appended to every emitted log line,
    making it easy to filter logs by game, task, or step.

    Example::

        log = get_logger("aether_gazer")
        task_log = log.with_context(task="daily_missions", step="login")
        task_log.info("Starting login flow")
        # → [aether_gazer] [task=daily_missions, step=login] Starting login flow
    """

    def __init__(self, name: str, **context: Any) -> None:
        self._name = name
        self._context: dict[str, Any] = context

    # ------------------------------------------------------------------
    # Public log methods
    # ------------------------------------------------------------------

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Emit an INFO-level message."""
        self._log("INFO", msg, *args, **kwargs)

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Emit a DEBUG-level message."""
        self._log("DEBUG", msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Emit a WARNING-level message."""
        self._log("WARNING", msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Emit an ERROR-level message."""
        self._log("ERROR", msg, *args, **kwargs)

    # ------------------------------------------------------------------
    # Context management
    # ------------------------------------------------------------------

    def with_context(self, **ctx: Any) -> "Logger":
        """Return a child logger with additional context merged in.

        The parent logger is unchanged; a new Logger instance is returned.
        New keys override existing keys with the same name.
        """
        merged = {**self._context, **ctx}
        return Logger(self._name, **merged)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Logger name (typically the module or component name)."""
        return self._name

    @property
    def context(self) -> dict[str, Any]:
        """A copy of the current context dict."""
        return dict(self._context)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _log(self, level: str, msg: str, *args: Any, **kwargs: Any) -> None:
        """Format and emit a log message with context tags.

        Supports loguru-style ``{}`` positional placeholders in *msg*.
        Extra *kwargs* are silently ignored (for future extensibility).
        """
        # Build bracketed context annotation, e.g. " [task=login, step=1]"
        ctx_parts = [f"{k}={v}" for k, v in self._context.items()]
        ctx_str = f" [{', '.join(ctx_parts)}]" if ctx_parts else ""

        # Expand positional placeholders when args are provided
        if args:
            try:
                formatted = msg.format(*args)
            except (IndexError, KeyError):
                formatted = msg
        else:
            formatted = msg

        full_msg = f"[{self._name}]{ctx_str} {formatted}"
        # depth=2: skip _log + the public method (info/debug/…) so loguru
        # reports the caller's file/line, not this file.
        _loguru.opt(depth=2).log(level, full_msg)
