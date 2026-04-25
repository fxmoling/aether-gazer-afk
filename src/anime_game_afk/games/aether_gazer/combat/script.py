"""Combat script data model and YAML loader.

A CombatScript is a sequence of CombatSteps loaded from a YAML file.
Three step types: press (tap key), hold (sustain key), wait (sleep).

Pure data — no device access, no side effects.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from anime_game_afk.games.aether_gazer.knowledge.keys import letter_to_vk

_DEFAULT_INTERVAL = 0.12
_STEP_ACTIONS = frozenset({"press", "hold", "wait"})

# Resolve config directory relative to project root.
# config/combat_scripts/ lives at the repo root, not inside src/.
_CONFIG_DIR = Path(__file__).resolve().parents[5] / "config" / "combat_scripts"


@dataclass(frozen=True)
class CombatStep:
    """Single action in a combat script."""

    action: Literal["press", "hold", "wait"]
    key: str | None  # Key name (None for wait)
    vk_code: int | None  # Resolved VK code (None for wait)
    duration: float  # Hold duration (hold) or sleep seconds (wait)
    interval: float  # Post-action wait in seconds


@dataclass(frozen=True)
class CombatScript:
    """Loaded and validated combat script."""

    name: str
    description: str
    steps: tuple[CombatStep, ...]


def load_script(name: str) -> CombatScript:
    """Load a named script from ``config/combat_scripts/{name}.yaml``."""
    path = _CONFIG_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Combat script not found: {path}")
    return load_script_file(path)


def load_script_file(path: Path) -> CombatScript:
    """Load and validate a combat script from an arbitrary YAML file."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    name = raw.get("name", path.stem)
    description = raw.get("description", "")
    default_interval = float(raw.get("interval", _DEFAULT_INTERVAL))

    raw_steps = raw.get("steps")
    if not raw_steps:
        raise ValueError(f"Combat script {name!r}: 'steps' must be a non-empty list")

    steps: list[CombatStep] = []
    for i, entry in enumerate(raw_steps):
        step = _parse_step(entry, default_interval, context=f"step {i}")
        steps.append(step)

    return CombatScript(name=name, description=description, steps=tuple(steps))


def _parse_step(entry: dict | float, default_interval: float, context: str) -> CombatStep:
    """Parse a single step entry from the YAML steps list."""
    # wait shorthand: `- wait: 0.5`
    if isinstance(entry, (int, float)):
        return CombatStep(
            action="wait", key=None, vk_code=None,
            duration=float(entry), interval=0.0,
        )

    # Determine which action keys are present
    found = _STEP_ACTIONS & entry.keys()
    if len(found) != 1:
        raise ValueError(
            f"{context}: step must have exactly one of 'press', 'hold', 'wait'; "
            f"found {found or 'none'}"
        )
    action = found.pop()
    interval = float(entry.get("interval", default_interval))

    if action == "wait":
        return CombatStep(
            action="wait", key=None, vk_code=None,
            duration=float(entry["wait"]), interval=0.0,
        )

    key_name = str(entry[action])
    vk_code = letter_to_vk(key_name)  # raises ValueError on bad key
    duration = 0.0
    if action == "hold":
        if "duration" not in entry:
            raise ValueError(f"{context}: 'hold' step requires 'duration'")
        duration = float(entry["duration"])
        if duration <= 0:
            raise ValueError(f"{context}: 'hold' duration must be > 0")

    return CombatStep(
        action=action, key=key_name, vk_code=vk_code,
        duration=duration, interval=interval,
    )
