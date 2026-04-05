"""Automation exception hierarchy."""


class AutomationError(Exception):
    """Base class for all automation errors."""


class DeviceError(AutomationError):
    """Base class for device-related failures (window, connection, screenshot)."""


class WindowNotFoundError(DeviceError):
    """Game window could not be found."""


class DeviceConnectionError(DeviceError):
    """Failed to connect to the game window.

    Named DeviceConnectionError to avoid shadowing builtins.ConnectionError.
    """


# Backward-compatible alias — will be removed after full migration.
ConnectionError = DeviceConnectionError  # noqa: A001


class ScreenshotError(DeviceError):
    """Failed to capture a screenshot."""


class PipelineError(AutomationError):
    """Pipeline execution failed."""


class RecognitionError(AutomationError):
    """Image recognition failed."""


class GameNotRunningError(AutomationError):
    """Game process is not running."""
