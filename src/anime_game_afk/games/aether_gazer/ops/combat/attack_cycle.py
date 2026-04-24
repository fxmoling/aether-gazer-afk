"""One round of battle attack keys.

Presses the full attack rotation: J J U J I J O R 1 2
with configurable interval between keys. Takes ~2.5s at
default interval (0.25s * 10 keys).

Composite Action: uses PressKeyOp primitives internally.
"""
from __future__ import annotations

import time

from anime_game_afk.games.aether_gazer.knowledge.constants import (
    BATTLE_KEY_INTERVAL,
)
from anime_game_afk.games.aether_gazer.knowledge.keys import (
    ATTACK_CYCLE_KEYS,
    key_name,
)
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.primitives import PressKeyOp


class AttackCycleAction:
    """Execute one full attack key rotation."""

    def __init__(self, interval: float = BATTLE_KEY_INTERVAL) -> None:
        self._interval = interval

    async def run(self, ctx: OpContext) -> OpResult:
        ctx.logger.info(
            f"[attack_cycle] Starting: {len(ATTACK_CYCLE_KEYS)} keys "
            f"@{self._interval}s interval"
        )
        t0 = time.perf_counter()
        for i, vk in enumerate(ATTACK_CYCLE_KEYS):
            if i % 5 == 0:
                ctx.logger.debug(
                    f"Attack key {i}/{len(ATTACK_CYCLE_KEYS)}: "
                    f"{key_name(vk)}"
                )
            await PressKeyOp(key=vk, wait=self._interval).run(ctx)

        elapsed = time.perf_counter() - t0
        ctx.logger.debug(
            f"[attack_cycle] Completed {len(ATTACK_CYCLE_KEYS)} keys "
            f"in {elapsed:.3f}s"
        )
        return OpResult(
            success=True,
            data={"keys_pressed": len(ATTACK_CYCLE_KEYS)},
        )
