"""任务模块"""

from anime_game_afk.games.aether_gazer.tasks.base import (
    BaseTask,
    CompleteTask,
    SinglePointTask,
    TaskContext,
    TaskSequence,
    TaskStatus,
)
from anime_game_afk.games.aether_gazer.tasks.atomic import (
    ClickAt,
    ClickElement,
    EnsureHub,
    GoBack,
    NavigateToPage,
    PressKey,
    Wait,
    WakeUI,
)
from anime_game_afk.games.aether_gazer.tasks.daily import (
    CollectEventsRewards,
    CollectGuildRewards,
    CollectMail,
    CollectTacticsRewards,
    DailyCheckin,
    FullDailyRoutine,
    ViewDailyTasks,
)

__all__ = [
    # Base
    "BaseTask",
    "CompleteTask",
    "SinglePointTask",
    "TaskContext",
    "TaskSequence",
    "TaskStatus",
    # Atomic
    "ClickAt",
    "ClickElement",
    "EnsureHub",
    "GoBack",
    "NavigateToPage",
    "PressKey",
    "Wait",
    "WakeUI",
    # Daily
    "CollectEventsRewards",
    "CollectGuildRewards",
    "CollectMail",
    "CollectTacticsRewards",
    "DailyCheckin",
    "FullDailyRoutine",
    "ViewDailyTasks",
]
