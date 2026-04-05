"""Automation exception hierarchy."""


class AutomationError(Exception):
    """Base class for all automation errors."""


class DeviceError(AutomationError):
    """Base class for device-related failures (window, connection, screenshot)."""


class WindowNotFoundError(DeviceError):
    """Game window could not be found."""


class ConnectionError(DeviceError):
    """Failed to connect to the game window."""


class ScreenshotError(DeviceError):
    """Failed to capture a screenshot."""


class PipelineError(AutomationError):
    """Pipeline execution failed."""


class RecognitionError(AutomationError):
    """Image recognition failed."""


class GameNotRunningError(AutomationError):
    """Game process is not running."""
