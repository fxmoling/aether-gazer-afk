"""Tests for combat runner — execute_cycle and CombatRunner."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import numpy as np
import pytest

from anime_game_afk.games.aether_gazer.combat.runner import (
    CombatRunner,
    execute_cycle,
    execute_loop,
    execute_startup,
    execute_steps,
)
from anime_game_afk.games.aether_gazer.combat.script import CombatScript, CombatStep
from anime_game_afk.games.aether_gazer.ops.base import OpContext


@dataclass
class MockDevice:
    """Records key presses and holds for assertions."""
    pressed: list = field(default_factory=list)
    held: list = field(default_factory=list)

    def screenshot(self) -> np.ndarray:
        return np.zeros((720, 1280, 3), dtype=np.uint8)

    def click(self, fx: float, fy: float) -> None:
        pass

    def press_key(self, vk_code: int) -> None:
        self.pressed.append(vk_code)

    def hold_key(self, vk_code: int, duration_s: float) -> None:
        self.held.append((vk_code, duration_s))


def _make_script(steps: list[CombatStep], name: str = "test") -> CombatScript:
    return CombatScript(name=name, description="", startup_steps=(), loop_steps=tuple(steps))


def _press(key: str, vk: int, interval: float = 0.12) -> CombatStep:
    return CombatStep(action="press", key=key, vk_code=vk, duration=0.0, interval=interval)


def _hold(key: str, vk: int, duration: float, interval: float = 0.12) -> CombatStep:
    return CombatStep(action="hold", key=key, vk_code=vk, duration=duration, interval=interval)


def _wait(seconds: float) -> CombatStep:
    return CombatStep(action="wait", key=None, vk_code=None, duration=seconds, interval=0.0)


class TestExecuteCycle:
    def test_press_keys_in_order(self):
        dev = MockDevice()
        ctx = OpContext(device=dev)
        script = _make_script([
            _press("j", 0x4A),
            _press("u", 0x55),
            _press("i", 0x49),
        ])
        asyncio.run(execute_cycle(ctx, script))
        assert dev.pressed == [0x4A, 0x55, 0x49]

    def test_hold_key(self):
        dev = MockDevice()
        ctx = OpContext(device=dev)
        script = _make_script([
            _hold("u", 0x55, duration=1.5),
            _press("j", 0x4A),
        ])
        asyncio.run(execute_cycle(ctx, script))
        assert dev.held == [(0x55, 1.5)]
        assert dev.pressed == [0x4A]

    def test_wait_step_no_keys(self):
        dev = MockDevice()
        ctx = OpContext(device=dev)
        script = _make_script([
            _press("j", 0x4A),
            _wait(0.5),
            _press("u", 0x55),
        ])
        asyncio.run(execute_cycle(ctx, script))
        assert dev.pressed == [0x4A, 0x55]
        assert dev.held == []

    def test_empty_script_noop(self):
        dev = MockDevice()
        ctx = OpContext(device=dev)
        script = CombatScript(name="empty", description="", startup_steps=(), loop_steps=())
        asyncio.run(execute_cycle(ctx, script))
        assert dev.pressed == []


class TestCombatRunner:
    def test_runner_stops_when_active_cleared(self):
        dev = MockDevice()
        ctx = OpContext(device=dev)
        script = _make_script([_press("j", 0x4A)])
        runner = CombatRunner(script)
        runner.active = True

        # Stop the runner after a few key presses via device callback
        def _press_and_count(vk_code: int) -> None:
            dev.pressed.append(vk_code)
            if len(dev.pressed) >= 3:
                runner.stop()
        dev.press_key = _press_and_count

        asyncio.run(runner.run(ctx))
        # Runner should have pressed keys then stopped
        assert len(dev.pressed) >= 3
        assert all(vk == 0x4A for vk in dev.pressed)

    def test_runner_idles_when_not_active(self, monkeypatch):
        dev = MockDevice()
        ctx = OpContext(device=dev)
        script = _make_script([_press("j", 0x4A)])
        runner = CombatRunner(script)
        runner.active = False

        # Count idle sleep calls and stop after a few iterations
        idle_count = [0]

        async def _sleep_and_stop(seconds: float) -> None:
            idle_count[0] += 1
            if idle_count[0] >= 3:
                runner.stop()

        monkeypatch.setattr("asyncio.sleep", _sleep_and_stop)
        asyncio.run(runner.run(ctx))
        assert dev.pressed == []  # Never active, no keys pressed


class TestExecuteStartupLoop:
    """Tests for execute_startup, execute_loop, and execute_steps."""

    def test_execute_startup(self):
        dev = MockDevice()
        ctx = OpContext(device=dev)
        script = CombatScript(
            name="test", description="",
            startup_steps=(_press("u", 0x55), _press("i", 0x49)),
            loop_steps=(_press("j", 0x4A),),
        )
        asyncio.run(execute_startup(ctx, script))
        assert dev.pressed == [0x55, 0x49]

    def test_execute_loop(self):
        dev = MockDevice()
        ctx = OpContext(device=dev)
        script = CombatScript(
            name="test", description="",
            startup_steps=(_press("u", 0x55),),
            loop_steps=(_press("j", 0x4A), _press("i", 0x49)),
        )
        asyncio.run(execute_loop(ctx, script))
        assert dev.pressed == [0x4A, 0x49]

    def test_execute_steps_directly(self):
        dev = MockDevice()
        ctx = OpContext(device=dev)
        steps = [_press("j", 0x4A), _hold("u", 0x55, 1.0), _wait(0.1)]
        asyncio.run(execute_steps(ctx, steps))
        assert dev.pressed == [0x4A]
        assert dev.held == [(0x55, 1.0)]
