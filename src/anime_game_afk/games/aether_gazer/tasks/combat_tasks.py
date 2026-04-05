"""Combat tasks — battle state machine and stage clearing.

CombatStateMachine replaces the monolithic ch6_battle.py with
a clean state machine built from atomic ops.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.keys import (
    ATTACK_CYCLE_KEYS,
    VK_ENTER,
    VK_ESCAPE,
    VK_SPACE,
    VK_W,
)
from anime_game_afk.games.aether_gazer.knowledge.constants import (
    UNKNOWN_ROTATION,
)
from anime_game_afk.games.aether_gazer.ops.base import GameState
from anime_game_afk.games.aether_gazer.ops.perception.detect_game_state import (
    DetectGameStateOp,
)
from anime_game_afk.games.aether_gazer.ops.combat.attack_cycle import (
    AttackCycleOp,
)
from anime_game_afk.games.aether_gazer.ops.combat.handle_revive import (
    HandleReviveOp,
)
from anime_game_afk.games.aether_gazer.ops.interact.skip_cutscene import (
    SkipCutsceneOp,
)
from anime_game_afk.games.aether_gazer.ops.interact.advance_dialogue import (
    AdvanceDialogueOp,
)
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext, TaskResult


class CombatStateMachine:
    """Run a single battle from start to completion.

    State loop: screenshot -> detect state -> dispatch handler -> repeat.
    Exits when battle completes (stage_map detected or results screen).
    """
    name = "combat_state_machine"

    def __init__(self) -> None:
        self._detect = DetectGameStateOp()
        self._attack = AttackCycleOp()
        self._revive = HandleReviveOp()
        self._skip = SkipCutsceneOp()
        self._dialogue = AdvanceDialogueOp()
        self._unknown_count = 0

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        self._unknown_count = 0
        max_cycles = 500

        for _ in range(max_cycles):
            result = await self._detect.run(ctx)
            state: GameState = result.data["state"]

            if state == GameState.BATTLE:
                self._unknown_count = 0
                await self._attack.run(ctx)

            elif state == GameState.REVIVE_PROMPT:
                self._unknown_count = 0
                await self._revive.run(ctx)

            elif state == GameState.CUTSCENE:
                self._unknown_count = 0
                await self._skip.run(ctx)

            elif state == GameState.DIALOGUE:
                self._unknown_count = 0
                await self._dialogue.run(ctx)

            elif state == GameState.SKIP_STORY_CONFIRM:
                self._unknown_count = 0
                ctx.device.press_key(VK_ENTER)
                await asyncio.sleep(1.0)

            elif state == GameState.CONTINUOUS_BATTLE:
                self._unknown_count = 0
                ctx.device.press_key(VK_ENTER)
                await asyncio.sleep(2.0)

            elif state == GameState.MISSION_FAILED:
                ctx.logger.warning("Mission failed detected")
                ctx.device.press_key(VK_ESCAPE)
                await asyncio.sleep(1.0)
                return TaskResult(status="failed", message="Mission failed")

            elif state == GameState.STAGE_MAP:
                ctx.logger.info("Back to stage map — battle complete")
                return TaskResult(status="success")

            elif state == GameState.LOADING:
                await asyncio.sleep(1.0)

            else:
                await self._handle_unknown(ctx)

            await asyncio.sleep(0.5)

        return TaskResult(status="failed", message="Max cycles reached")

    async def _handle_unknown(self, ctx: TaskContext) -> None:
        """Unknown state rotation strategy."""
        self._unknown_count += 1
        phases = UNKNOWN_ROTATION
        n = self._unknown_count

        # Each phase is (start, end); n <= end means still in that phase
        if n <= phases["space"][1]:
            ctx.device.press_key(VK_SPACE)
        elif n <= phases["attack"][1]:
            for vk in ATTACK_CYCLE_KEYS[:3]:
                ctx.device.press_key(vk)
                await asyncio.sleep(0.2)
        elif n <= phases["walk"][1]:
            ctx.device.press_key(VK_W)
        elif n <= phases["esc_enter"][1]:
            ctx.device.press_key(VK_ESCAPE)
            await asyncio.sleep(0.5)
            ctx.device.press_key(VK_ENTER)
        else:
            self._unknown_count = 0


class ClearSingleStage:
    """Clear one stage: prep -> combat -> handle result."""
    name = "clear_single_stage"

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        # Press Enter to start battle from prep screen
        ctx.device.press_key(VK_ENTER)
        await asyncio.sleep(3.0)

        # Run combat state machine
        combat = CombatStateMachine()
        return await combat.execute(ctx)
