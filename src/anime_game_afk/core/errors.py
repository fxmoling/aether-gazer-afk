"""自动化异常层次"""


class AutomationError(Exception):
    """所有自动化错误的基类"""


class WindowNotFoundError(AutomationError):
    """找不到游戏窗口"""


class ConnectionError(AutomationError):
    """连接游戏窗口失败"""


class ScreenshotError(AutomationError):
    """截图失败"""


class PipelineError(AutomationError):
    """管线执行失败"""


class RecognitionError(AutomationError):
    """图像识别失败"""


class GameNotRunningError(AutomationError):
    """游戏未运行"""
