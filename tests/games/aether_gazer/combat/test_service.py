"""Tests for AutoBattleService.

Note: The global conftest patches asyncio.sleep to a no-op coroutine.
That works for single-task tests but breaks concurrent tasks (they never
yield to the event loop).  Tests here override the patch with a
``_yield_sleep`` that resolves instantly but properly yields, allowing
asyncio.gather / create_task to interleave coroutines.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from unittest.mock import patch

import numpy as np
import pytest

from anime_game_afk.games.aether_gazer.checks.base import CheckResult
from anime_game_afk.games.aether_gazer.combat.script import CombatScript, CombatStep
from anime_game_afk.games.aether_gazer.combat.service import AutoBattleService
from anime_game_afk.games.aether_gazer.ops.base import OpContext


@dataclass
class MockDevice:
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


def _simple_script() -> CombatScript:
    return CombatScript(
        name="test",
        description="",
        steps=(
            CombatStep(action="press", key="j", vk_code=0x4A, duration=0.0, interval=0.12),
        ),
    )


async def _yield_sleep(seconds: float) -> None:
    """Instant sleep that actually yields to the event loop.

    Unlike the conftest no-op (``async def: pass``), this schedules a
    callback via ``call_soon`` so other tasks get a chance to run.
    """
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    loop.call_soon(future.set_result, None)
    await future


class TestAutoBattleServiceToggle:
    """Test the start() + stop() (toggle) pattern."""

    def test_start_stop_basic(self, monkeypatch):
        """Service starts, monitor detects battle, combat runs, then stop."""
        monkeypatch.setattr("asyncio.sleep", _yield_sleep)
        dev = MockDevice()
        ctx = OpContext(device=dev)
        service = AutoBattleService(_simple_script(), check_interval=0.1)

        call_count = [0]

        async def mock_evaluate(self_check, ctx_arg):
            call_count[0] += 1
            if call_count[0] <= 5:
                return CheckResult(passed=True)
            service.stop()
            return CheckResult(passed=False)

        async def _run():
            await asyncio.wait_for(service.start(ctx), timeout=5.0)

        with patch(
            "anime_game_afk.games.aether_gazer.combat.service.InBattleCheck.evaluate",
            mock_evaluate,
        ):
            asyncio.run(_run())

        assert len(dev.pressed) > 0
        assert all(vk == 0x4A for vk in dev.pressed)

    def test_stop_before_battle_detected(self, monkeypatch):
        """Stop immediately — no keys should be pressed."""
        monkeypatch.setattr("asyncio.sleep", _yield_sleep)
        dev = MockDevice()
        ctx = OpContext(device=dev)
        service = AutoBattleService(_simple_script(), check_interval=0.1)

        call_count = [0]

        async def mock_evaluate(self_check, ctx_arg):
            call_count[0] += 1
            if call_count[0] >= 3:
                service.stop()
            return CheckResult(passed=False)

        async def _run():
            await asyncio.wait_for(service.start(ctx), timeout=5.0)

        with patch(
            "anime_game_afk.games.aether_gazer.combat.service.InBattleCheck.evaluate",
            mock_evaluate,
        ):
            asyncio.run(_run())

        assert dev.pressed == []

    def test_in_battle_property_reflects_state(self):
        """in_battle property tracks the runner active state."""
        service = AutoBattleService(_simple_script())
        assert service.in_battle is False

        service._runner.active = True
        assert service.in_battle is True

        service._runner.active = False
        assert service.in_battle is False

    def test_battle_transitions(self, monkeypatch):
        """Battle starts, keys pressed, battle ends, keys stop, then exit."""
        monkeypatch.setattr("asyncio.sleep", _yield_sleep)
        dev = MockDevice()
        ctx = OpContext(device=dev)
        service = AutoBattleService(_simple_script(), check_interval=0.1)

        call_count = [0]
        keys_at_battle_end = [0]

        async def mock_evaluate(self_check, ctx_arg):
            call_count[0] += 1
            if call_count[0] <= 2:
                return CheckResult(passed=False)
            elif call_count[0] <= 6:
                return CheckResult(passed=True)
            else:
                keys_at_battle_end[0] = len(dev.pressed)
                service.stop()
                return CheckResult(passed=False)

        async def _run():
            await asyncio.wait_for(service.start(ctx), timeout=5.0)

        with patch(
            "anime_game_afk.games.aether_gazer.combat.service.InBattleCheck.evaluate",
            mock_evaluate,
        ):
            asyncio.run(_run())

        assert keys_at_battle_end[0] > 0
        assert all(vk == 0x4A for vk in dev.pressed)


class TestAutoBattleServiceRunOnce:
    """Test the run_until_battle_ends() (run-once) pattern."""

    def test_run_until_battle_ends_basic(self, monkeypatch):
        """False → True → False sequence: service runs then auto-returns."""
        monkeypatch.setattr("asyncio.sleep", _yield_sleep)
        dev = MockDevice()
        ctx = OpContext(device=dev)
        service = AutoBattleService(_simple_script(), check_interval=0.1)

        call_count = [0]

        async def mock_evaluate(self_check, ctx_arg):
            call_count[0] += 1
            if call_count[0] <= 3:
                return CheckResult(passed=False)
            elif call_count[0] <= 8:
                return CheckResult(passed=True)
            else:
                return CheckResult(passed=False)

        async def _run():
            await asyncio.wait_for(
                service.run_until_battle_ends(ctx), timeout=5.0,
            )

        with patch(
            "anime_game_afk.games.aether_gazer.combat.service.InBattleCheck.evaluate",
            mock_evaluate,
        ):
            asyncio.run(_run())

        assert len(dev.pressed) > 0
        assert all(vk == 0x4A for vk in dev.pressed)
        assert service._enabled is False

    def test_run_until_battle_ends_immediate_battle(self, monkeypatch):
        """Battle starts immediately, then ends."""
        monkeypatch.setattr("asyncio.sleep", _yield_sleep)
        dev = MockDevice()
        ctx = OpContext(device=dev)
        service = AutoBattleService(_simple_script(), check_interval=0.1)

        call_count = [0]

        async def mock_evaluate(self_check, ctx_arg):
            call_count[0] += 1
            if call_count[0] <= 5:
                return CheckResult(passed=True)
            else:
                return CheckResult(passed=False)

        async def _run():
            await asyncio.wait_for(
                service.run_until_battle_ends(ctx), timeout=5.0,
            )

        with patch(
            "anime_game_afk.games.aether_gazer.combat.service.InBattleCheck.evaluate",
            mock_evaluate,
        ):
            asyncio.run(_run())

        assert len(dev.pressed) > 0
        assert service._enabled is False
        assert service.in_battle is False

    def test_run_until_no_keys_before_battle(self, monkeypatch):
        """No keys pressed during the pre-battle waiting phase."""
        monkeypatch.setattr("asyncio.sleep", _yield_sleep)
        dev = MockDevice()
        ctx = OpContext(device=dev)
        service = AutoBattleService(_simple_script(), check_interval=0.1)

        call_count = [0]
        keys_when_battle_starts = [None]

        async def mock_evaluate(self_check, ctx_arg):
            call_count[0] += 1
            if call_count[0] <= 4:
                return CheckResult(passed=False)
            elif call_count[0] == 5:
                keys_when_battle_starts[0] = len(dev.pressed)
                return CheckResult(passed=True)
            elif call_count[0] <= 8:
                return CheckResult(passed=True)
            else:
                return CheckResult(passed=False)

        async def _run():
            await asyncio.wait_for(
                service.run_until_battle_ends(ctx), timeout=5.0,
            )

        with patch(
            "anime_game_afk.games.aether_gazer.combat.service.InBattleCheck.evaluate",
            mock_evaluate,
        ):
            asyncio.run(_run())

        assert keys_when_battle_starts[0] == 0
        assert len(dev.pressed) > 0
