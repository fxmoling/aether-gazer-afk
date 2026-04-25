"""Combat script execution.

``execute_cycle`` runs one pass of all steps in a script.
``CombatRunner`` loops the cycle while its ``active`` flag is True.
"""
from __future__ import annotations

import asyncio

from loguru import logger

from anime_game_afk.games.aether_gazer.combat.script import CombatScript
from anime_game_afk.games.aether_gazer.knowledge.keys import key_name
from anime_game_afk.games.aether_gazer.ops.base import OpContext


async def execute_cycle(ctx: OpContext, script: CombatScript) -> None:
    """Execute one complete cycle of *script* (all steps once)."""
    for step in script.steps:
        if step.action == "press":
            ctx.device.press_key(step.vk_code)
            await asyncio.sleep(step.interval)
        elif step.action == "hold":
            ctx.device.hold_key(step.vk_code, step.duration)
            await asyncio.sleep(step.interval)
        elif step.action == "wait":
            await asyncio.sleep(step.duration)


class CombatRunner:
    """Loops ``execute_cycle`` while ``active`` is True.

    Set ``active = True`` to start pressing keys.
    Set ``active = False`` to pause (runner idles until active again).
    Call ``stop()`` to exit the run loop entirely.
    """

    def __init__(self, script: CombatScript) -> None:
        self._script = script
        self.active: bool = False
        self._running: bool = False

    def stop(self) -> None:
        """Signal the run loop to exit."""
        self._running = False
        self.active = False

    async def run(self, ctx: OpContext) -> None:
        """Loop script steps while active. Exits on ``stop()``."""
        self._running = True
        logger.info("CombatRunner started: script={!r}", self._script.name)
        try:
            while self._running:
                if self.active:
                    await execute_cycle(ctx, self._script)
                else:
                    await asyncio.sleep(0.5)
        finally:
            logger.info("CombatRunner stopped")
