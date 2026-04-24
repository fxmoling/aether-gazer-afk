"""Combat tasks — battle state machine and stage clearing.

CombatStateMachine replaces the monolithic ch6_battle.py with
a clean state machine built from atomic ops.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.checks.state import (
    DetectGameStateCheck,
)
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
from anime_game_afk.games.aether_gazer.ops.combat.attack_cycle import (
    AttackCycleAction,
)
from anime_game_afk.games.aether_gazer.ops.combat.handle_revive import (
    HandleReviveAction,
)
from anime_game_afk.games.aether_gazer.ops.interact.skip_cutscene import (
    SkipCutsceneAction,
)
from anime_game_afk.games.aether_gazer.ops.interact.advance_dialogue import (
    AdvanceDialogueAction,
)
from anime_game_afk.games.aether_gazer.ops.primitives import (
    PressKeyOp,
    SleepOp,
)
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext, TaskResult


class CombatStateMachine:
    """Run a single battle from start to completion.

    State loop: screenshot -> detect state -> dispatch handler -> repeat.
    Exits when battle completes (stage_map detected or results screen).
    """
    name = "combat_state_machine"
    description = "Run a single battle via state machine loop"
    category = "combat"
    requires_pages = ()
    requires_ocr = False
    safe = True

    def __init__(self) -> None:
        self._detect = DetectGameStateCheck()
        self._attack = AttackCycleAction()
        self._revive = HandleReviveAction()
        self._skip = SkipCutsceneAction()
        self._dialogue = AdvanceDialogueAction()
        self._unknown_count = 0

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        ctx.logger.info("=== CombatStateMachine: starting ===")
        self._unknown_count = 0
        max_cycles = 500

        try:
            for cycle in range(max_cycles):
                if cycle > 0 and cycle % 50 == 0:
                    ctx.logger.info(f"[combat] cycle {cycle}/{max_cycles}")

                check_result = await self._detect.evaluate(ctx)
                state: GameState = check_result.data["state"]

                if state == GameState.BATTLE:
                    self._unknown_count = 0
                    ctx.logger.debug("[combat] state=BATTLE → attack cycle")
                    await self._attack.run(ctx)

                elif state == GameState.REVIVE_PROMPT:
                    self._unknown_count = 0
                    ctx.logger.info("[combat] state=REVIVE_PROMPT → handling revive")
                    await self._revive.run(ctx)

                elif state == GameState.CUTSCENE:
                    self._unknown_count = 0
                    ctx.logger.debug("[combat] state=CUTSCENE → skip")
                    await self._skip.run(ctx)

                elif state == GameState.DIALOGUE:
                    self._unknown_count = 0
                    ctx.logger.debug("[combat] state=DIALOGUE → advance")
                    await self._dialogue.run(ctx)

                elif state == GameState.SKIP_STORY_CONFIRM:
                    self._unknown_count = 0
                    ctx.logger.debug("[combat] state=SKIP_STORY_CONFIRM → Enter")
                    await PressKeyOp(key=VK_ENTER, wait=1.0).run(ctx)

                elif state == GameState.CONTINUOUS_BATTLE:
                    self._unknown_count = 0
                    ctx.logger.info("[combat] state=CONTINUOUS_BATTLE → Enter")
                    await PressKeyOp(key=VK_ENTER, wait=2.0).run(ctx)

                elif state == GameState.MISSION_FAILED:
                    ctx.logger.warning("Mission failed detected")
                    await PressKeyOp(key=VK_ESCAPE, wait=1.0).run(ctx)
                    ctx.logger.info("=== CombatStateMachine: finished (mission failed) ===")
                    return TaskResult(status="failed", message="Mission failed")

                elif state == GameState.STAGE_MAP:
                    ctx.logger.info("Back to stage map — battle complete")
                    ctx.logger.info("=== CombatStateMachine: completed successfully ===")
                    return TaskResult(status="success")

                elif state == GameState.LOADING:
                    ctx.logger.debug("[combat] state=LOADING → wait")
                    await SleepOp(seconds=1.0).run(ctx)

                else:
                    await self._handle_unknown(ctx)

                await SleepOp(seconds=0.5).run(ctx)

            ctx.logger.error(f"[combat] max cycles ({max_cycles}) reached")
            return TaskResult(status="failed", message="Max cycles reached")
        except Exception as exc:
            ctx.logger.error(f"=== CombatStateMachine: failed — {exc} ===")
            raise

    async def _handle_unknown(self, ctx: TaskContext) -> None:
        """Unknown state rotation strategy."""
        self._unknown_count += 1
        phases = UNKNOWN_ROTATION
        n = self._unknown_count

        # Each phase is (start, end); n <= end means still in that phase
        if n <= phases["space"][1]:
            ctx.logger.debug(f"[combat] unknown state #{n} → space phase")
            await PressKeyOp(key=VK_SPACE, wait=0.5).run(ctx)
        elif n <= phases["attack"][1]:
            ctx.logger.debug(f"[combat] unknown state #{n} → attack phase")
            for vk in ATTACK_CYCLE_KEYS[:3]:
                await PressKeyOp(key=vk, wait=0.2).run(ctx)
        elif n <= phases["walk"][1]:
            ctx.logger.debug(f"[combat] unknown state #{n} → walk phase")
            await PressKeyOp(key=VK_W, wait=0.5).run(ctx)
        elif n <= phases["esc_enter"][1]:
            ctx.logger.debug(f"[combat] unknown state #{n} → esc_enter phase")
            await PressKeyOp(key=VK_ESCAPE, wait=0.5).run(ctx)
            await PressKeyOp(key=VK_ENTER, wait=0.5).run(ctx)
        else:
            ctx.logger.debug(f"[combat] unknown state #{n} → reset rotation")
            self._unknown_count = 0


class ClearSingleStage:
    """Clear one stage: prep -> combat -> handle result."""
    name = "clear_single_stage"
    description = "Clear one battle stage from prep to completion"
    category = "combat"
    requires_pages = ()
    requires_ocr = False
    safe = True

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        ctx.logger.info("=== ClearSingleStage: starting ===")
        try:
            # Press Enter to start battle from prep screen
            ctx.logger.info("[step] Pressing Enter to start battle from prep screen")
            await PressKeyOp(key=VK_ENTER, wait=3.0).run(ctx)

            # Run combat state machine
            ctx.logger.info("[step] Entering combat state machine")
            combat = CombatStateMachine()
            result = await combat.execute(ctx)
            ctx.logger.info(f"=== ClearSingleStage: finished (status={result.status}) ===")
            return result
        except Exception as exc:
            ctx.logger.error(f"=== ClearSingleStage: failed — {exc} ===")
            raise
