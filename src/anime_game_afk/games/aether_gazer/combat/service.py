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
from anime_game_afk.games.aether_gazer.combat.runner import CombatRunner, execute_cycle
from anime_game_afk.games.aether_gazer.combat.script import CombatScript
from anime_game_afk.games.aether_gazer.ops.base import OpContext


class AutoBattleService:
    """Toggle-based auto-battle: monitor battle state + run combat script."""

    def __init__(self, script: CombatScript, check_interval: float = 2.0) -> None:
        self._script = script
        self._check_interval = check_interval
        self._runner = CombatRunner(script)
        self._enabled = False

    # ── Public API ──

    async def start(self, ctx: OpContext) -> None:
        """Start monitor + combat loops. Blocks until ``stop()`` called."""
        self._enabled = True
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
        logger.info("AutoBattle stopped")

    async def run_until_battle_ends(self, ctx: OpContext) -> None:
        """Start, wait for battle to begin and end, then auto-stop.

        For task-driven usage: call this after entering a battle screen.
        It fights until InBattleCheck goes False, then returns.
        """
        self._enabled = True
        monitor = asyncio.create_task(self._monitor_loop(ctx))
        combat = asyncio.create_task(self._combat_loop(ctx))
        try:
            # Wait for battle to start
            while self._enabled and not self._runner.active:
                await asyncio.sleep(0.5)
            # Wait for battle to end
            while self._enabled and self._runner.active:
                await asyncio.sleep(0.5)
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
        while self._enabled:
            result = await check.evaluate(ctx)
            was_active = self._runner.active
            self._runner.active = result.passed
            if result.passed and not was_active:
                logger.info("AutoBattle: battle detected — fighting")
            elif not result.passed and was_active:
                logger.info("AutoBattle: battle ended — idling")
            await asyncio.sleep(self._check_interval)

    async def _combat_loop(self, ctx: OpContext) -> None:
        while self._enabled:
            if self._runner.active:
                await execute_cycle(ctx, self._script)
            else:
                await asyncio.sleep(0.5)
