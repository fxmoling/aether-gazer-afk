"""Combat script data model and YAML loader.

A CombatScript has two phases:

- **startup** — runs once when battle begins (optional, may be empty)
- **loop** — repeats until battle ends (required, at least one step)

Three step types: press (tap key), hold (sustain key), wait (sleep).

YAML format (new)::

    name: 梵天
    startup:
      - hold: space
        duration: 0.3
    loop:
      - press: j
      - press: u

Legacy format (backward-compatible)::

    name: 默认
    steps:
      - press: j

When only ``steps:`` is present, it is treated as ``loop:`` with no startup.

Pure data — no device access, no side effects.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from anime_game_afk.games.aether_gazer.knowledge.keys import letter_to_vk

_DEFAULT_INTERVAL = 0.12
_STEP_ACTIONS = frozenset({"press", "hold", "wait"})
_VALID_TOP_KEYS = frozenset({
    "name", "description", "interval", "steps", "startup", "loop",
})

# Resolve config directory relative to project root.
# config/combat_scripts/ lives at the repo root, not inside src/.
if getattr(sys, "frozen", False):
    _CONFIG_DIR = Path(sys.executable).resolve().parent / "config" / "combat_scripts"
else:
    _CONFIG_DIR = Path(__file__).resolve().parents[5] / "config" / "combat_scripts"

# Strict filename pattern for user-created scripts
_VALID_SCRIPT_ID = re.compile(r"^[a-zA-Z0-9_\-\u4e00-\u9fff]+$")
_MAX_SCRIPT_ID_LEN = 64


@dataclass(frozen=True)
class CombatStep:
    """Single action in a combat script."""

    action: Literal["press", "hold", "wait"]
    key: str | None  # Key name (None for wait)
    vk_code: int | None  # Resolved VK code (None for wait)
    duration: float  # Hold duration (hold) or sleep seconds (wait)
    interval: float  # Post-action wait in seconds

    def to_dict(self) -> dict[str, Any]:
        """Serialize to YAML-compatible dict."""
        if self.action == "wait":
            return {"wait": self.duration}
        d: dict[str, Any] = {self.action: self.key}
        if self.action == "hold":
            d["duration"] = self.duration
        if self.interval != _DEFAULT_INTERVAL:
            d["interval"] = self.interval
        return d


@dataclass(frozen=True)
class CombatScript:
    """Loaded and validated combat script.

    Attributes:
        startup_steps: Steps executed once when battle begins (may be empty).
        loop_steps: Steps repeated until battle ends.
    """

    name: str
    description: str
    startup_steps: tuple[CombatStep, ...]
    loop_steps: tuple[CombatStep, ...]

    @property
    def steps(self) -> tuple[CombatStep, ...]:
        """All steps concatenated (startup + loop). For inspection only."""
        return self.startup_steps + self.loop_steps

    def to_dict(self) -> dict[str, Any]:
        """Serialize to YAML-compatible dict."""
        d: dict[str, Any] = {"name": self.name}
        if self.description:
            d["description"] = self.description
        if self.startup_steps:
            d["startup"] = [s.to_dict() for s in self.startup_steps]
        d["loop"] = [s.to_dict() for s in self.loop_steps]
        return d

    def to_yaml(self) -> str:
        """Serialize to YAML string."""
        return yaml.dump(
            self.to_dict(), default_flow_style=False,
            allow_unicode=True, sort_keys=False,
        )


def validate_script_id(script_id: str) -> str:
    """Validate and normalize a script ID for use as filename.

    Raises ValueError on invalid IDs.
    """
    script_id = script_id.strip()
    if not script_id:
        raise ValueError("Script ID must not be empty")
    if len(script_id) > _MAX_SCRIPT_ID_LEN:
        raise ValueError(f"Script ID too long (max {_MAX_SCRIPT_ID_LEN})")
    if not _VALID_SCRIPT_ID.match(script_id):
        raise ValueError(
            f"Script ID {script_id!r} contains invalid characters. "
            "Use letters, digits, underscore, hyphen, or Chinese characters."
        )
    return script_id


def list_scripts() -> list[dict[str, Any]]:
    """List all available combat scripts with metadata.

    Returns:
        List of dicts with keys: id, name, description,
        has_startup, startup_count, loop_count.
    """
    result: list[dict[str, Any]] = []
    if not _CONFIG_DIR.exists():
        return result
    for f in sorted(_CONFIG_DIR.glob("*.yaml")):
        try:
            s = load_script(f.stem)
            result.append({
                "id": f.stem,
                "name": s.name,
                "description": s.description,
                "has_startup": len(s.startup_steps) > 0,
                "startup_count": len(s.startup_steps),
                "loop_count": len(s.loop_steps),
            })
        except Exception:
            result.append({
                "id": f.stem, "name": f.stem, "description": "(load error)",
                "has_startup": False, "startup_count": 0, "loop_count": 0,
            })
    return result


def load_script(name: str) -> CombatScript:
    """Load a named script from ``config/combat_scripts/{name}.yaml``."""
    path = _CONFIG_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Combat script not found: {path}")
    return load_script_file(path)


def save_script_file(script_id: str, content: str) -> Path:
    """Validate and save a combat script YAML string.

    Args:
        script_id: Filename stem (validated for safety).
        content: Raw YAML string to validate and save.

    Returns:
        Path to the saved file.

    Raises:
        ValueError: On invalid script_id or invalid YAML content.
    """
    script_id = validate_script_id(script_id)
    # Parse and validate content (will raise on errors)
    load_script_from_string(content)

    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    target = _CONFIG_DIR / f"{script_id}.yaml"
    # Verify resolved path stays under config dir (prevent traversal)
    if not target.resolve().parent == _CONFIG_DIR.resolve():
        raise ValueError("Invalid script path")

    # Atomic write: temp file + rename
    tmp = target.with_suffix(".yaml.tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(target)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return target


def delete_script_file(script_id: str) -> None:
    """Delete a combat script file.

    Raises ValueError if trying to delete the built-in 'default' script.
    """
    script_id = validate_script_id(script_id)
    if script_id == "default":
        raise ValueError("Cannot delete the built-in 'default' script")
    path = _CONFIG_DIR / f"{script_id}.yaml"
    if not path.resolve().parent == _CONFIG_DIR.resolve():
        raise ValueError("Invalid script path")
    if path.exists():
        path.unlink()


def load_script_from_string(content: str) -> CombatScript:
    """Parse and validate a combat script from a YAML string."""
    raw = yaml.safe_load(content)
    if not isinstance(raw, dict):
        raise ValueError("Combat script must be a YAML mapping")
    return _load_from_dict(raw, source="<string>")


def load_script_file(path: Path) -> CombatScript:
    """Load and validate a combat script from an arbitrary YAML file."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError(f"Combat script {path}: must be a YAML mapping")
    return _load_from_dict(raw, source=str(path))


def _load_from_dict(raw: dict[str, Any], source: str = "") -> CombatScript:
    """Internal: build CombatScript from parsed YAML dict."""
    # Reject unknown top-level keys
    unknown = set(raw.keys()) - _VALID_TOP_KEYS
    if unknown:
        raise ValueError(f"Unknown top-level keys: {unknown}")

    name = raw.get("name", Path(source).stem if source else "unnamed")
    description = raw.get("description", "")
    default_interval = float(raw.get("interval", _DEFAULT_INTERVAL))

    has_steps = "steps" in raw
    has_startup = "startup" in raw
    has_loop = "loop" in raw

    # Reject mixing legacy and new format
    if has_steps and (has_startup or has_loop):
        raise ValueError(
            f"Script {name!r}: use either 'steps' (legacy) or "
            "'startup'/'loop' (new format), not both"
        )

    if has_steps:
        # Legacy format: steps → loop, no startup
        raw_loop = raw["steps"]
        raw_startup = []
    elif has_loop:
        # New format
        raw_loop = raw["loop"]
        raw_startup = raw.get("startup", []) or []
    else:
        raise ValueError(
            f"Script {name!r}: must have 'loop' (or legacy 'steps') section"
        )

    if not raw_loop:
        raise ValueError(f"Script {name!r}: 'loop' must be a non-empty list")

    startup_steps = _parse_steps(raw_startup, default_interval, "startup")
    loop_steps = _parse_steps(raw_loop, default_interval, "loop")

    return CombatScript(
        name=name, description=description,
        startup_steps=tuple(startup_steps),
        loop_steps=tuple(loop_steps),
    )


def _parse_steps(
    raw_steps: list, default_interval: float, section: str,
) -> list[CombatStep]:
    """Parse a list of raw step entries."""
    steps: list[CombatStep] = []
    for i, entry in enumerate(raw_steps):
        step = _parse_step(entry, default_interval, context=f"{section}[{i}]")
        steps.append(step)
    return steps


def _parse_step(entry: dict | float, default_interval: float, context: str) -> CombatStep:
    """Parse a single step entry from the YAML steps list."""
    # wait shorthand: `- 0.5`
    if isinstance(entry, (int, float)):
        return CombatStep(
            action="wait", key=None, vk_code=None,
            duration=float(entry), interval=0.0,
        )

    if not isinstance(entry, dict):
        raise ValueError(f"{context}: step must be a mapping or number, got {type(entry).__name__}")

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
