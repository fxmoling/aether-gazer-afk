"""One round of battle attack keys.

Presses the full attack rotation: J J U J I J O R 1 2
with configurable interval between keys. Takes ~2.5s at
default interval (0.25s * 10 keys).
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.constants import (
    BATTLE_KEY_INTERVAL,
)
from anime_game_afk.games.aether_gazer.knowledge.keys import (
    ATTACK_CYCLE_KEYS,
    key_name,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult


class AttackCycleOp:
    """Execute one full attack key rotation."""

    def __init__(self, interval: float = BATTLE_KEY_INTERVAL) -> None:
        self._interval = interval

    async def run(self, ctx: OpContext) -> OpResult:
        for i, vk in enumerate(ATTACK_CYCLE_KEYS):
            ctx.device.press_key(vk)
            if i % 5 == 0:
                ctx.logger.debug(
                    f"Attack key {i}/{len(ATTACK_CYCLE_KEYS)}: "
                    f"{key_name(vk)}"
                )
            await asyncio.sleep(self._interval)

        return OpResult(
            success=True,
            data={"keys_pressed": len(ATTACK_CYCLE_KEYS)},
        )
