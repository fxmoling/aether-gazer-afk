# Wave 3: Composable Tasks & Processes (Layers 6-7)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement task-by-task.

**Goal:** Build composable tasks from Layer 5 ops, and complete user-visible processes from tasks. This is where `ch6_battle.py` logic gets properly decomposed.

**Dependencies:** Wave 2 complete (knowledge/ and ops/ layers exist).

---

## Task 1: Tasks — base.py (Task protocol)

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/tasks_v2/__init__.py`
- Create: `src/anime_game_afk/games/aether_gazer/tasks_v2/base.py`
- Create: `src/anime_game_afk/games/aether_gazer/tasks_v2/README.md`
- Test: `tests/games/aether_gazer/tasks_v2/test_base.py`

**Purpose:** Task protocol, TaskResult, TaskContext. Note: using `tasks_v2/` to avoid conflict with existing `tasks/` during migration. Rename after cleanup in Wave 4.

- [ ] Step 1: Create `tasks_v2/` directory with `__init__.py`
- [ ] Step 2: Create `base.py` with TaskResult, TaskContext, Task protocol
- [ ] Step 3: Create README.md
- [ ] Step 4: Write test with a mock task
- [ ] Step 5: Run tests, commit

**base.py content:**
```python
"""Base types for composable tasks.

Tasks compose atomic ops (Layer 5) with control flow.
Each task does one logical thing: clear a stage, buy items, collect mail.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

from anime_game_afk.games.aether_gazer.ops.base import OpContext


@dataclass
class TaskResult:
    """Result of a composable task."""
    status: Literal["success", "failed", "skipped"]
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class TaskContext(OpContext):
    """Extended context for tasks. Inherits device/logger from OpContext.

    Tasks may add task-level state (e.g. stages_cleared counter).
    """
    pass


@runtime_checkable
class Task(Protocol):
    """Protocol for composable tasks."""
    name: str

    async def execute(self, ctx: TaskContext) -> TaskResult: ...

    async def can_run(self, ctx: TaskContext) -> bool: ...
```

---

## Task 2: Tasks — combat_tasks.py (combat state machine)

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/tasks_v2/combat_tasks.py`
- Test: `tests/games/aether_gazer/tasks_v2/test_combat_tasks.py`

**Purpose:** The core combat state machine that replaces ch6_battle.py. Composes perception ops (detect_game_state) with combat/interact ops.

- [ ] Step 1: Create `combat_tasks.py` with CombatStateMachine class
- [ ] Step 2: Implement state detection loop using ops.perception.detect_game_state
- [ ] Step 3: Implement unknown state rotation strategy (Space→attack→walk→ESC+Enter)
- [ ] Step 4: Write test with mocked state sequence
- [ ] Step 5: Run tests, commit

**combat_tasks.py content:**
```python
"""Combat tasks — battle state machine and stage clearing.

CombatStateMachine replaces the monolithic ch6_battle.py with
a clean state machine built from atomic ops.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.keys import (
    ATTACK_KEYS, VK_ENTER, VK_ESCAPE, VK_SPACE, VK_W,
)
from anime_game_afk.games.aether_gazer.knowledge.constants import (
    UNKNOWN_ROTATION_PHASES,
)
from anime_game_afk.games.aether_gazer.ops.perception.detect_game_state import (
    DetectGameState, GameState,
)
from anime_game_afk.games.aether_gazer.ops.combat.attack_cycle import AttackCycle
from anime_game_afk.games.aether_gazer.ops.combat.handle_revive import HandleRevive
from anime_game_afk.games.aether_gazer.ops.interact.skip_cutscene import SkipCutscene
from anime_game_afk.games.aether_gazer.ops.interact.advance_dialogue import AdvanceDialogue
from anime_game_afk.games.aether_gazer.tasks_v2.base import Task, TaskContext, TaskResult


class CombatStateMachine:
    """Run a single battle from start to completion.

    State loop: screenshot → detect state → dispatch handler → repeat.
    Exits when battle completes (stage_map detected or results screen).
    """
    name = "combat_state_machine"

    def __init__(self) -> None:
        self._detect = DetectGameState()
        self._attack = AttackCycle()
        self._revive = HandleRevive()
        self._skip = SkipCutscene()
        self._dialogue = AdvanceDialogue()
        self._unknown_count = 0

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        self._unknown_count = 0
        max_cycles = 500

        for cycle in range(max_cycles):
            result = await self._detect.run(ctx)
            state: GameState = result.data

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
        phases = UNKNOWN_ROTATION_PHASES
        n = self._unknown_count

        if n <= phases["space"][1]:
            ctx.device.press_key(VK_SPACE)
        elif n <= phases["attack"][1]:
            for vk in ATTACK_KEYS[:3]:
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
    """Clear one stage: prep → combat → handle result."""
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
```

---

## Task 3: Tasks — navigation_tasks.py

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/tasks_v2/navigation_tasks.py`
- Test: `tests/games/aether_gazer/tasks_v2/test_navigation_tasks.py`

**Purpose:** Multi-step navigation sequences: enter main story, return to hub with verification.

- [ ] Step 1: Create `navigation_tasks.py` with ReturnToHub, EnterMainStory tasks
- [ ] Step 2: Write test
- [ ] Step 3: Run tests, commit

**navigation_tasks.py content:**
```python
"""Navigation tasks — multi-step page navigation.

Composes navigate ops with verification and retry logic.
"""
from __future__ import annotations

import asyncio

from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ESCAPE
from anime_game_afk.games.aether_gazer.ops.navigate.return_to_hub import ReturnToHub as ReturnToHubOp
from anime_game_afk.games.aether_gazer.ops.navigate.goto_page import GotoPage
from anime_game_afk.games.aether_gazer.tasks_v2.base import Task, TaskContext, TaskResult


class ReturnToHub:
    """Ensure we are at the main hub."""
    name = "return_to_hub"

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        op = ReturnToHubOp()
        result = await op.run(ctx)
        if result.success:
            return TaskResult(status="success")
        return TaskResult(status="failed", message="Could not return to hub")


class EnterMainStory:
    """Navigate from hub to main story stage map."""
    name = "enter_main_story"

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        # Hub → Battle Select
        goto = GotoPage(target="battle_select")
        result = await goto.run(ctx)
        if not result.success:
            return TaskResult(status="failed", message="Cannot reach battle_select")

        # Click main story entry (情报 tab → 主线入口)
        ctx.device.click(160, 860)   # 情报 tab
        await asyncio.sleep(1.5)
        ctx.device.click(533, 450)   # Main story entry
        await asyncio.sleep(2.0)

        return TaskResult(status="success")
```

---

## Task 4: Tasks — shop_tasks.py, mail_tasks.py, stamina_tasks.py

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/tasks_v2/shop_tasks.py`
- Create: `src/anime_game_afk/games/aether_gazer/tasks_v2/mail_tasks.py`
- Create: `src/anime_game_afk/games/aether_gazer/tasks_v2/stamina_tasks.py`
- Test: `tests/games/aether_gazer/tasks_v2/test_shop_tasks.py`

**Purpose:** Daily shop, mail collection, stamina management tasks.

- [ ] Step 1: Create `shop_tasks.py` with ClaimFreeStamina task
- [ ] Step 2: Create `mail_tasks.py` with CollectAllMail task
- [ ] Step 3: Create `stamina_tasks.py` with CheckAndRefillStamina task
- [ ] Step 4: Write tests
- [ ] Step 5: Run tests, commit

---

## Task 5: Tasks — story_tasks.py

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/tasks_v2/story_tasks.py`
- Test: `tests/games/aether_gazer/tasks_v2/test_story_tasks.py`

**Purpose:** Chapter navigation, stage selection tasks.

- [ ] Step 1: Create `story_tasks.py` with NavigateToChapter, SelectLatestStage
- [ ] Step 2: Write tests
- [ ] Step 3: Run tests, commit

---

## Task 6: Processes — base.py (Process protocol)

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/processes/__init__.py`
- Create: `src/anime_game_afk/games/aether_gazer/processes/base.py`
- Create: `src/anime_game_afk/games/aether_gazer/processes/README.md`
- Test: `tests/games/aether_gazer/processes/test_base.py`

**Purpose:** Process protocol — complete user-visible features. Final classes.

- [ ] Step 1: Create `processes/` directory with `__init__.py`
- [ ] Step 2: Create `base.py` with ProcessResult, ProcessContext, Process protocol
- [ ] Step 3: Create README.md
- [ ] Step 4: Write test
- [ ] Step 5: Run tests, commit

**base.py content:**
```python
"""Base types for processes (complete user-visible features).

Processes are the top-level units users see and enable.
They compose Layer 6 tasks and are NOT composable by each other.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

from anime_game_afk.games.aether_gazer.tasks_v2.base import TaskContext


@dataclass
class ProcessResult:
    """Result of a complete process."""
    status: Literal["success", "failed", "skipped"]
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class ProcessContext(TaskContext):
    """Extended context for processes. Adds process-level config."""
    config: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Process(Protocol):
    """Protocol for user-visible processes."""
    name: str
    description: str

    async def execute(self, ctx: ProcessContext) -> ProcessResult: ...
```

---

## Task 7: Processes — push_main_story.py

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/processes/push_main_story.py`
- Test: `tests/games/aether_gazer/processes/test_push_main_story.py`

**Purpose:** "Push main story" — the first real process. Replaces ch6_battle.py completely.

- [ ] Step 1: Create `push_main_story.py` — hub → story → loop clear stages
- [ ] Step 2: Write test with mocked tasks
- [ ] Step 3: Run tests, commit

**push_main_story.py content:**
```python
"""Push main story process.

Navigates to story mode and clears stages until done or out of stamina.
This replaces the monolithic scripts/ch6_battle.py.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.tasks_v2.navigation_tasks import (
    ReturnToHub, EnterMainStory,
)
from anime_game_afk.games.aether_gazer.tasks_v2.combat_tasks import ClearSingleStage
from anime_game_afk.games.aether_gazer.processes.base import (
    Process, ProcessContext, ProcessResult,
)


class PushMainStory:
    """Push main story from current progress."""
    name = "push_main_story"
    description = "Clear main story stages sequentially"

    async def execute(self, ctx: ProcessContext) -> ProcessResult:
        max_stages = ctx.config.get("max_stages", 20)
        stages_cleared = 0

        # Step 1: Return to hub
        hub = ReturnToHub()
        result = await hub.execute(ctx)
        if result.status != "success":
            return ProcessResult(status="failed", message="Cannot reach hub")

        # Step 2: Enter main story
        enter = EnterMainStory()
        result = await enter.execute(ctx)
        if result.status != "success":
            return ProcessResult(status="failed", message="Cannot enter story")

        # Step 3: Clear stages in loop
        while stages_cleared < max_stages:
            stage = ClearSingleStage()
            result = await stage.execute(ctx)

            if result.status == "success":
                stages_cleared += 1
                ctx.logger.info("Stage cleared: {}/{}", stages_cleared, max_stages)
            else:
                ctx.logger.warning("Stage failed, stopping: {}", result.message)
                break

        # Step 4: Return to hub
        await hub.execute(ctx)

        return ProcessResult(
            status="success",
            data={"stages_cleared": stages_cleared},
        )
```

---

## Task 8: Processes — daily_routine.py

**Files:**
- Create: `src/anime_game_afk/games/aether_gazer/processes/daily_routine.py`
- Test: `tests/games/aether_gazer/processes/test_daily_routine.py`

**Purpose:** "Complete daily tasks" process — mail, shop, daily missions.

- [ ] Step 1: Create `daily_routine.py` — compose mail, shop, daily claim tasks
- [ ] Step 2: Write test
- [ ] Step 3: Run tests, commit

**daily_routine.py content:**
```python
"""Daily routine process.

Collects mail, claims free stamina, completes daily checklist.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.tasks_v2.navigation_tasks import ReturnToHub
from anime_game_afk.games.aether_gazer.tasks_v2.mail_tasks import CollectAllMail
from anime_game_afk.games.aether_gazer.tasks_v2.shop_tasks import ClaimFreeStamina
from anime_game_afk.games.aether_gazer.processes.base import (
    Process, ProcessContext, ProcessResult,
)


class DailyRoutine:
    """Complete all daily tasks and claim rewards."""
    name = "daily_routine"
    description = "Collect mail, claim free stamina, do daily tasks"

    async def execute(self, ctx: ProcessContext) -> ProcessResult:
        hub = ReturnToHub()
        completed = []

        await hub.execute(ctx)

        # Collect mail
        mail = CollectAllMail()
        if await mail.can_run(ctx):
            result = await mail.execute(ctx)
            if result.status == "success":
                completed.append("mail")

        await hub.execute(ctx)

        # Claim free stamina
        stamina = ClaimFreeStamina()
        if await stamina.can_run(ctx):
            result = await stamina.execute(ctx)
            if result.status == "success":
                completed.append("free_stamina")

        await hub.execute(ctx)

        return ProcessResult(
            status="success",
            data={"completed": completed},
        )
```
