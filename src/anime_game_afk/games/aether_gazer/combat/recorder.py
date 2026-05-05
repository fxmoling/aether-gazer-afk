"""Combo recorder — capture keyboard inputs and compile to CombatScript format.

Captures key presses during gameplay via pynput, then converts to the
existing press/hold/wait YAML format used by CombatScript.

Global hotkeys: F9 = toggle recording, F10 = toggle playback, F11 = stop all.

Architecture note: this module is combo-specific today. If future task
recording is needed, extract an ``InputRecorder`` protocol at that time.
"""
from __future__ import annotations

import enum
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable

from loguru import logger
from pynput import keyboard

from anime_game_afk.games.aether_gazer.knowledge.keys import letter_to_vk

# Keys the game uses (only record these)
_GAME_KEYS = {
    "j", "u", "i", "o", "r",    # combat
    "1", "2",                     # QTE
    "space",                      # dodge
    "w", "a", "s", "d",          # movement
}

# Hotkey VKs to filter out of recordings
_HOTKEY_VKS = {0x78, 0x79, 0x7A}  # F9, F10, F11

# Max recent keys kept for live UI feedback
_MAX_RECENT_KEYS = 30


class RecState(str, enum.Enum):
    IDLE = "idle"
    COUNTDOWN = "countdown"
    RECORDING = "recording"


@dataclass
class _RawEvent:
    """A single raw keyboard event."""
    key_name: str
    pressed: bool      # True = down, False = up
    timestamp: float   # perf_counter seconds


@dataclass
class CompiledStep:
    """One compiled step in CombatScript format."""
    action: str        # "press" | "hold" | "wait"
    key: str | None = None
    duration: float = 0.0
    interval: float | None = None

    def to_yaml_dict(self) -> dict[str, Any]:
        if self.action == "wait":
            return {"wait": round(self.duration, 2)}
        d: dict[str, Any] = {self.action: self.key}
        if self.action == "hold":
            d["duration"] = round(self.duration, 2)
        if self.interval is not None:
            d["interval"] = round(self.interval, 2)
        return d


class ComboRecorder:
    """Record keyboard inputs and compile to combat script steps.

    Usage::
        rec = ComboRecorder()
        rec.start()         # start global hotkey listener
        rec.begin_recording("loop")  # begin capture
        # ... user plays game ...
        steps = rec.stop_recording()  # returns list[CompiledStep]
        rec.stop()           # stop hotkey listener

    Results are buffered after stop_recording() so the frontend can poll
    and consume them asynchronously (important for hotkey-initiated stops).
    """

    def __init__(self) -> None:
        self._state = RecState.IDLE
        self._events: list[_RawEvent] = []
        self._lock = threading.Lock()
        self._kb_listener: keyboard.Listener | None = None
        self._hotkey_listener: keyboard.Listener | None = None
        self._start_time: float = 0.0
        self._recording_section: str = "loop"
        self._countdown_cancel = threading.Event()
        self._countdown_remaining: int = 0
        # Recent key presses for live UI feedback (bounded ring buffer)
        self._recent_keys: deque[dict[str, Any]] = deque(maxlen=_MAX_RECENT_KEYS)
        self._recent_seq: int = 0
        # Track currently held keys to suppress auto-repeat in UI
        self._held_keys: set[str] = set()
        # Buffered result: populated after stop_recording, consumed once by frontend
        self._pending_result: dict[str, Any] | None = None
        # Callbacks
        self._on_state: Callable[[dict[str, Any]], None] | None = None

    @property
    def state(self) -> RecState:
        return self._state

    @property
    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    def set_callbacks(
        self,
        on_state: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._on_state = on_state

    # ------------------------------------------------------------------
    # Hotkey listener
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the global hotkey listener."""
        if self._hotkey_listener:
            return
        self._hotkey_listener = keyboard.Listener(on_press=self._on_hotkey)
        self._hotkey_listener.start()
        logger.info("ComboRecorder hotkey listener started (F9/F11)")

    def stop(self) -> None:
        """Stop everything."""
        if self._state == RecState.RECORDING:
            self.stop_recording()
        if self._hotkey_listener:
            self._hotkey_listener.stop()
            self._hotkey_listener = None
        if self._kb_listener:
            self._kb_listener.stop()
            self._kb_listener = None
        logger.info("ComboRecorder stopped")

    def _on_hotkey(self, key: Any) -> None:
        """Handle global hotkey presses.

        F9 = toggle recording (start if idle, stop if recording).
        F11 = force stop recording.
        Runs callbacks on a daemon thread to avoid blocking pynput.
        """
        if isinstance(key, keyboard.Key):
            if key == keyboard.Key.f9:
                threading.Thread(target=self._hotkey_toggle, daemon=True).start()
            elif key == keyboard.Key.f11:
                if self._state != RecState.IDLE:
                    threading.Thread(
                        target=self.stop_recording, daemon=True,
                    ).start()

    def _hotkey_toggle(self) -> None:
        """Toggle recording via hotkey. If idle, start loop recording."""
        if self._state == RecState.IDLE:
            self.begin_recording(section=self._recording_section, countdown=3)
        else:
            self.stop_recording()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def begin_recording(
        self, section: str = "loop", countdown: int = 3,
    ) -> dict[str, Any]:
        """Start recording keyboard inputs.

        The section and countdown are set by the frontend. Recording captures
        into a temp buffer; results are delivered on stop.
        """
        if self._state != RecState.IDLE:
            return {"ok": False, "error": "already recording"}
        self._recording_section = section
        self._state = RecState.COUNTDOWN
        self._countdown_cancel.clear()
        self._countdown_remaining = countdown
        self._recent_keys.clear()
        self._recent_seq = 0
        self._held_keys.clear()
        self._pending_result = None
        self._notify()

        def _countdown() -> None:
            for i in range(countdown, 0, -1):
                if self._countdown_cancel.is_set():
                    self._state = RecState.IDLE
                    self._countdown_remaining = 0
                    self._notify()
                    return
                self._countdown_remaining = i
                self._notify()
                time.sleep(1)
            self._countdown_remaining = 0
            self._start_capture()

        threading.Thread(target=_countdown, daemon=True).start()
        return {"ok": True, "countdown": countdown}

    def _start_capture(self) -> None:
        """Begin the actual input capture."""
        with self._lock:
            self._events.clear()
        self._start_time = time.perf_counter()
        self._kb_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._kb_listener.start()
        self._state = RecState.RECORDING
        self._notify()
        logger.info("Recording started (section={})", self._recording_section)

    def stop_recording(self) -> list[CompiledStep]:
        """Stop recording and compile events into steps.

        Also buffers the result as ``_pending_result`` so the frontend can
        consume it via ``consume_result()`` on next poll.
        """
        if self._state == RecState.COUNTDOWN:
            self._countdown_cancel.set()
            self._state = RecState.IDLE
            self._countdown_remaining = 0
            self._pending_result = {
                "ok": True, "steps": [], "count": 0,
                "section": self._recording_section,
            }
            self._notify()
            return []

        if self._state != RecState.RECORDING:
            return []

        if self._kb_listener:
            self._kb_listener.stop()
            self._kb_listener = None

        self._state = RecState.IDLE
        with self._lock:
            events = list(self._events)
            self._events.clear()

        steps = _compile_events(events)
        logger.info("Recording stopped: {} raw events → {} steps",
                     len(events), len(steps))

        # Buffer result for frontend consumption
        self._pending_result = {
            "ok": True,
            "steps": [s.to_yaml_dict() for s in steps],
            "count": len(steps),
            "section": self._recording_section,
        }
        self._notify()
        return steps

    def consume_result(self) -> dict[str, Any] | None:
        """Consume the pending recording result (returns it exactly once).

        This is the safe delivery mechanism for hotkey-initiated stops:
        the frontend polls status, sees state=idle + has_result=True,
        then calls consume_result() to get the steps.
        """
        result = self._pending_result
        self._pending_result = None
        return result

    # ------------------------------------------------------------------
    # Key event handlers
    # ------------------------------------------------------------------

    def _resolve_key(self, key: Any) -> str | None:
        """Extract a game key name from a pynput key, or None."""
        if isinstance(key, keyboard.Key):
            if key == keyboard.Key.space:
                return "space"
            return None  # ignore non-game keys
        if isinstance(key, keyboard.KeyCode):
            if key.vk and key.vk in _HOTKEY_VKS:
                return None  # filter hotkeys
            ch = key.char
            if ch and ch.lower() in _GAME_KEYS:
                return ch.lower()
            # Numeric keys
            if key.vk and 0x30 <= key.vk <= 0x39:
                digit = str(key.vk - 0x30)
                if digit in _GAME_KEYS:
                    return digit
        return None

    def _on_key_press(self, key: Any) -> None:
        name = self._resolve_key(key)
        if not name:
            return
        now = time.perf_counter() - self._start_time
        evt = _RawEvent(key_name=name, pressed=True, timestamp=now)
        with self._lock:
            self._events.append(evt)

        # Live UI: suppress auto-repeat (key already held down)
        if name in self._held_keys:
            return
        self._held_keys.add(name)

        self._recent_seq += 1
        self._recent_keys.append({
            "key": name, "seq": self._recent_seq,
            "t": round(now, 2), "holding": True,
        })
        self._notify()

    def _on_key_release(self, key: Any) -> None:
        name = self._resolve_key(key)
        if not name:
            return
        now = time.perf_counter() - self._start_time
        evt = _RawEvent(key_name=name, pressed=False, timestamp=now)
        with self._lock:
            self._events.append(evt)

        self._held_keys.discard(name)

        # Update the matching recent-key entry: mark as released, compute duration
        for entry in reversed(self._recent_keys):
            if entry["key"] == name and entry.get("holding"):
                entry["holding"] = False
                entry["dur"] = round(now - entry["t"], 2)
                break
        self._notify()

    # ------------------------------------------------------------------
    # Notification & status
    # ------------------------------------------------------------------

    def _notify(self) -> None:
        if self._on_state:
            try:
                self._on_state(self.get_status())
            except Exception:
                pass

    def get_status(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "event_count": self.event_count,
            "section": self._recording_section,
            "countdown_remaining": self._countdown_remaining,
            "recent_keys": list(self._recent_keys),
            "has_result": self._pending_result is not None,
        }


# ---------------------------------------------------------------------------
# Compile raw events → CombatScript steps
# ---------------------------------------------------------------------------

_HOLD_THRESHOLD = 0.25  # seconds: above this = hold, below = press
_LONG_GAP = 1.5         # seconds: gaps above this become explicit wait steps


def _compile_events(events: list[_RawEvent]) -> list[CompiledStep]:
    """Convert raw key events into press/hold/wait steps with real timing.

    Strategy:
    - Pair each key_down with the next key_up for the same key
    - Short press (<250ms) → press step
    - Long press (≥250ms) → hold step with duration
    - Gap between consecutive actions → stored as ``interval`` on previous step
    - Very long gaps (>1.5s) → explicit wait step (user paused intentionally)

    The ``interval`` on each step represents the real measured delay from
    when this action ended to when the next action began, giving faithful
    playback timing.
    """
    if not events:
        return []

    # Pair downs with ups
    pairs: list[tuple[str, float, float]] = []  # (key, start_s, end_s)
    pending: dict[str, float] = {}  # key_name → start time

    for evt in events:
        if evt.pressed:
            if evt.key_name not in pending:
                pending[evt.key_name] = evt.timestamp
        else:
            if evt.key_name in pending:
                start = pending.pop(evt.key_name)
                pairs.append((evt.key_name, start, evt.timestamp))

    # Close any still-pending keys (held at recording end)
    end_time = events[-1].timestamp if events else 0.0
    for key, start in pending.items():
        pairs.append((key, start, end_time))

    if not pairs:
        return []

    # Sort by start time
    pairs.sort(key=lambda p: p[1])

    # Build steps with real timing
    steps: list[CompiledStep] = []

    for i, (key_name, start, end) in enumerate(pairs):
        hold_duration = end - start

        if hold_duration >= _HOLD_THRESHOLD:
            step = CompiledStep(
                action="hold", key=key_name, duration=hold_duration,
            )
        else:
            step = CompiledStep(action="press", key=key_name)

        # Compute interval = gap from this action's end to the next action's start
        if i < len(pairs) - 1:
            next_start = pairs[i + 1][1]
            gap = next_start - end
            if gap > _LONG_GAP:
                # Large gap: set a small interval on this step, then add explicit wait
                step.interval = 0.05
                steps.append(step)
                steps.append(CompiledStep(action="wait", duration=gap))
            else:
                # Normal gap: store as interval (minimum 0.02s for safety)
                step.interval = max(0.02, gap)
                steps.append(step)
        else:
            # Last step: no interval needed
            step.interval = 0.05
            steps.append(step)

    # Strip trailing waits
    while steps and steps[-1].action == "wait":
        steps.pop()

    return steps


def steps_to_yaml(
    name: str,
    startup: list[CompiledStep],
    loop: list[CompiledStep],
    description: str = "",
    interval: float = 0.12,
) -> str:
    """Build a complete combat script YAML string."""
    import yaml

    data: dict[str, Any] = {"name": name}
    if description:
        data["description"] = description
    if interval != 0.12:
        data["interval"] = interval
    if startup:
        data["startup"] = [s.to_yaml_dict() for s in startup]
    data["loop"] = [s.to_yaml_dict() for s in loop] if loop else [{"press": "j"}]

    return yaml.dump(
        data, default_flow_style=False,
        allow_unicode=True, sort_keys=False,
    )
