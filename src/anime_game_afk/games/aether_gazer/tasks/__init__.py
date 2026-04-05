"""DEPRECATED: This module has been migrated.

BaseTask / TaskContext → processes/base.py (Layer 7) or tasks_v2/base.py (Layer 6)
SinglePointTask → ops/ (Layer 5, one file per op)
CompleteTask → tasks_v2/ (Layer 6, composable tasks)
TaskSequence → orchestrator/pipeline.py (Layer 8)
atomic.py → ops/ (Layer 5, split into subdirectories)
daily.py → processes/daily_routine.py (Layer 7)

This wrapper exists temporarily so old imports produce clear errors.
Remove after all references have been updated.
"""
import warnings

_MIGRATION_MAP: dict[str, str] = {
    "BaseTask": "processes/base.py or tasks_v2/base.py",
    "TaskContext": "processes/base.py (ProcessContext)",
    "SinglePointTask": "ops/ (one file per atomic operation)",
    "CompleteTask": "tasks_v2/ (composable task modules)",
    "TaskSequence": "orchestrator/pipeline.py (Pipeline)",
    "TaskStatus": "processes/base.py or tasks_v2/base.py",
}


def __getattr__(name: str) -> object:
    """Raise clear deprecation error for any attribute access."""
    new_location = _MIGRATION_MAP.get(name, "see architecture docs")
    warnings.warn(
        f"anime_game_afk.games.aether_gazer.tasks is DEPRECATED. "
        f"'{name}' has moved to: {new_location}\n"
        f"Update your imports accordingly.",
        DeprecationWarning,
        stacklevel=2,
    )
    raise ImportError(
        f"Module 'tasks' (old) is deprecated. '{name}' has moved to: {new_location}"
    )
