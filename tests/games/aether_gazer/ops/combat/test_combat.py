"""Tests for combat ops."""
import asyncio
from dataclasses import dataclass, field

import numpy as np

from anime_game_afk.games.aether_gazer.knowledge.keys import (
    ATTACK_CYCLE_KEYS,
    VK_ENTER,
    VK_W,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.games.aether_gazer.ops.combat.attack_cycle import (
    AttackCycleAction,
)
from anime_game_afk.games.aether_gazer.ops.combat.handle_revive import (
    HandleReviveAction,
)
from anime_game_afk.games.aether_gazer.ops.combat.walk_forward import (
    WalkForwardAction,
)


@dataclass
class MockDevice:
    click_log: list = field(default_factory=list)
    key_log: list = field(default_factory=list)
    hold_log: list = field(default_factory=list)

    def screenshot(self) -> np.ndarray:
        return np.zeros((900, 1600, 3), dtype=np.uint8)
    def click(self, x: int, y: int) -> None:
        self.click_log.append((x, y))
    def press_key(self, vk_code: int) -> None:
        self.key_log.append(vk_code)
    def hold_key(self, vk_code: int, duration_s: float) -> None:
        self.hold_log.append((vk_code, duration_s))


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_attack_cycle_presses_all_keys():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = AttackCycleAction(interval=0.0)
    result = _run(op.run(ctx))
    assert result.success
    assert len(device.key_log) == len(ATTACK_CYCLE_KEYS)
    assert device.key_log == list(ATTACK_CYCLE_KEYS)
    assert result.data["keys_pressed"] == 10


def test_attack_cycle_order():
    """Keys are in correct order: J J U J I J O R 1 2."""
    device = MockDevice()
    ctx = OpContext(device=device)
    _run(AttackCycleAction(interval=0.0).run(ctx))
    assert device.key_log[0] == 0x4A  # J
    assert device.key_log[2] == 0x55  # U
    assert device.key_log[4] == 0x49  # I
    assert device.key_log[6] == 0x4F  # O
    assert device.key_log[7] == 0x52  # R
    assert device.key_log[8] == 0x31  # 1
    assert device.key_log[9] == 0x32  # 2


def test_handle_revive():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = HandleReviveAction(wait_after=0.0)
    result = _run(op.run(ctx))
    assert result.success
    assert VK_ENTER in device.key_log
    assert result.data["action"] == "revive_accepted"


def test_walk_forward():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = WalkForwardAction(duration=1.5)
    result = _run(op.run(ctx))
    assert result.success
    assert (VK_W, 1.5) in device.hold_log
    assert result.data["duration"] == 1.5


def test_walk_forward_default_duration():
    device = MockDevice()
    ctx = OpContext(device=device)
    op = WalkForwardAction()
    result = _run(op.run(ctx))
    assert result.success
    assert result.data["duration"] == 2.0
