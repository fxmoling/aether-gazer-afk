"""Auto-battle service — monitor battle state + execute combat script.

Two usage patterns:

Pattern A — Toggle (user-driven)::

    service = AutoBattleService(script)
    task = asyncio.create_task(service.start(ctx))
    ...
    service.stop()
    await task

Pattern B — Run-once (task-driven)::

    service = AutoBattleService(script)
    await service.run_until_battle_ends(ctx)
"""
from __future__ import annotations

import asyncio

from loguru import logger

from anime_game_afk.games.aether_gazer.checks.battle import InBattleCheck
from anime_game_afk.games.aether_gazer.combat.runner import (
    CombatRunner,
    execute_loop,
    execute_startup,
)
from anime_game_afk.games.aether_gazer.combat.script import CombatScript
from anime_game_afk.games.aether_gazer.ops.base import OpContext

# After this many consecutive idle checks, consider the battle truly ended
# and allow startup to re-run for the next encounter.
_IDLE_CONFIRM_COUNT = 3


class AutoBattleService:
    """Toggle-based auto-battle: monitor battle state + run combat script."""

    def __init__(self, script: CombatScript, check_interval: float = 2.0) -> None:
        self._script = script
        self._check_interval = check_interval
        self._runner = CombatRunner(script)
        self._enabled = False
        self._startup_done = False

    # ── Public API ──

    async def start(self, ctx: OpContext) -> None:
        """Start monitor + combat loops. Blocks until ``stop()`` called."""
        self._enabled = True
        self._startup_done = False
        logger.info(
            "AutoBattle started: script={!r} check_interval={:.1f}s",
            self._script.name, self._check_interval,
        )
        await asyncio.gather(
            self._monitor_loop(ctx),
            self._combat_loop(ctx),
        )

    def stop(self) -> None:
        """Signal both loops to exit."""
        self._enabled = False
        self._runner.stop()
        self._startup_done = False
        logger.info("AutoBattle stopped")

    async def run_until_battle_ends(
        self, ctx: OpContext, extra_confirms: int = 1,
    ) -> None:
        """Start, wait for battle to begin and end, then auto-stop.

        For task-driven usage: call this after entering a battle screen.

        Args:
            extra_confirms: after first False, recheck at 1s intervals
                this many extra times. All must be False to confirm end.
                If any recheck is True, resume normal monitoring.
                Default 1 (quick confirm). Use 3+ for VFX-heavy scenes.
        """
        self._enabled = True
        self._startup_done = False
        monitor = asyncio.create_task(self._monitor_loop(ctx))
        combat = asyncio.create_task(self._combat_loop(ctx))
        check = InBattleCheck()
        try:
            # Wait for battle to start
            while self._enabled and not self._runner.active:
                await asyncio.sleep(0.5)
            # Wait for battle to end with debounce
            while self._enabled:
                await asyncio.sleep(self._check_interval)
                if not self._runner.active:
                    # First False detected — run extra confirms at 1s intervals
                    confirmed = True
                    for i in range(extra_confirms):
                        await asyncio.sleep(1.0)
                        result = await check.evaluate(ctx)
                        if result.passed:
                            # Still in battle — false alarm
                            logger.debug(
                                "run_until_battle_ends: recheck {}/{} = True, resuming",
                                i + 1, extra_confirms,
                            )
                            self._runner.active = True
                            confirmed = False
                            break
                        logger.debug(
                            "run_until_battle_ends: recheck {}/{} = False",
                            i + 1, extra_confirms,
                        )
                    if confirmed:
                        logger.info("run_until_battle_ends: battle ended (confirmed)")
                        break
        finally:
            self.stop()
            await asyncio.gather(monitor, combat, return_exceptions=True)

    @property
    def in_battle(self) -> bool:
        """Current battle state."""
        return self._runner.active

    # ── Internal loops ──

    async def _monitor_loop(self, ctx: OpContext) -> None:
        check = InBattleCheck()
        idle_count = 0
        while self._enabled:
            result = await check.evaluate(ctx)
            was_active = self._runner.active
            self._runner.active = result.passed
            if result.passed:
                idle_count = 0
                if not was_active:
                    logger.info("AutoBattle: battle detected — fighting")
            else:
                if was_active:
                    idle_count = 1
                    logger.info("AutoBattle: battle ended — idling")
                elif idle_count > 0:
                    idle_count += 1
                    if idle_count >= _IDLE_CONFIRM_COUNT and self._startup_done:
                        self._startup_done = False
                        idle_count = 0
                        logger.info(
                            "AutoBattle: battle end confirmed, startup reset"
                        )
            await asyncio.sleep(self._check_interval)

    async def _combat_loop(self, ctx: OpContext) -> None:
        while self._enabled:
            if self._runner.active:
                if not self._startup_done:
                    await execute_startup(ctx, self._script)
                    self._startup_done = True
                await execute_loop(ctx, self._script)
            else:
                await asyncio.sleep(0.5)
