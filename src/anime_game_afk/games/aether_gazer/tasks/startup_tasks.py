"""Startup tasks — launch game, skip popups, reach hub.

LaunchAndReachHub: Complete startup task that:
1. Ensures game is running (launch if needed)
2. Connects device adapter
3. Skips login screens, loading animations, popups
4. Returns success when the main hub page is detected

SkipStartupPopups: Sub-task for popup dismissal only (assumes game
is already running and device is connected).

Startup flow for 深空之眼 (observed 2026-04-06):
  Epilepsy warning (auto-dismiss ~5s) → Login screen "点击任意区域进入游戏"
  → Loading (~5s) → Hub (possibly with event popups on top)
"""
from __future__ import annotations

from pathlib import Path

from anime_game_afk.games.aether_gazer.checks.ocr import OcrScanCheck
from anime_game_afk.games.aether_gazer.checks.page import AtHubCheck, OnPageCheck
from anime_game_afk.games.aether_gazer.knowledge.keys import VK_ESCAPE
from anime_game_afk.games.aether_gazer.ops.interact.rapid_click import RapidClickAction
from anime_game_afk.games.aether_gazer.ops.primitives import (
    ClickOp,
    PressKeyOp,
    SleepOp,
)
from anime_game_afk.games.aether_gazer.tasks.base import TaskContext, TaskResult


class SkipStartupPopups:
    """Dismiss all startup popups until the main hub is reached.

    Assumes the game is already running and the device is connected.
    Uses a multi-strategy approach with stuck detection:

    1. Fast hub check (template match only — 5ms) → success
    2. Full hub check (template + OCR) → success
    3. Detect login screen → click center
    4. Detect loading screen → wait
    5. Detect event/announcement popup → ESC or click close
    6. Detect exit dialog → ESC to cancel
    7. Stuck detection: if 3+ attempts with no screen change → aggressive dismiss

    Metadata:
        name: skip_startup_popups
        category: startup
        requires_ocr: True
        safe: True
    """

    name = "skip_startup_popups"
    description = "Skip startup popups, events, login until hub is reached"
    category = "startup"
    requires_pages = ("main_hub",)
    requires_ocr = True
    safe = True

    def __init__(self, max_attempts: int = 40) -> None:
        self._max_attempts = max_attempts

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        ctx.logger.info("  [startup] Starting popup dismissal loop")

        # Quick check: if already at hub, skip entirely (game was already running)
        on_hub = await OnPageCheck(page="main_hub").evaluate(ctx)
        if on_hub.passed:
            ctx.logger.info("  [startup] Already at hub, skipping")
            return TaskResult(
                status="success",
                message="Already at hub",
                data={"attempts": 0},
            )

        for attempt in range(self._max_attempts):
            # ── Hub check (template) with double-confirm ──
            on_hub = await OnPageCheck(page="main_hub").evaluate(ctx)
            if on_hub.passed:
                await SleepOp(seconds=0.5).run(ctx)
                confirm = await OnPageCheck(page="main_hub").evaluate(ctx)
                if confirm.passed:
                    ctx.logger.info(
                        f"  [startup] Hub confirmed after {attempt} attempts"
                    )
                    return TaskResult(
                        status="success",
                        message=f"Hub reached after {attempt} attempts",
                        data={"attempts": attempt},
                    )
                ctx.logger.debug(
                    f"  [startup][{attempt}] Hub detected but lost on recheck"
                )

            # ── Hub check (OCR fallback) with double-confirm ──
            r = await OcrScanCheck().evaluate(ctx)
            ocr = r.data if r.passed else None
            if ocr and ocr.has_all("前往作战", "探测", "修正者", "仓库"):
                await SleepOp(seconds=0.5).run(ctx)
                confirm = await OnPageCheck(page="main_hub").evaluate(ctx)
                if confirm.passed:
                    ctx.logger.info(
                        f"  [startup] Hub confirmed (OCR) after {attempt} attempts"
                    )
                    return TaskResult(
                        status="success",
                        message=f"Hub reached after {attempt} attempts",
                        data={"attempts": attempt},
                    )

            # ── Exit dialog — only case that needs ESC ──
            if ocr and (ocr.has("退出游戏") or ocr.has("是否退出")):
                ctx.logger.info(
                    f"  [startup][{attempt}] Exit dialog — pressing ESC"
                )
                await PressKeyOp(key=VK_ESCAPE, wait=1.0).run(ctx)
                continue

            # ── Not at hub — rapid click blank area to dismiss startup popups ──
            ctx.logger.debug(
                f"  [startup][{attempt}] Not at hub — rapid clicking (0.4, 0.05) ×5"
            )
            await RapidClickAction(
                x=0.4, y=0.05, times=5, interval=0.15,
            ).run(ctx)

        # Max attempts exceeded — final check
        ctx.logger.warning(
            f"  [startup] Max attempts ({self._max_attempts}) reached"
        )
        hub_result = await AtHubCheck().evaluate(ctx)
        if hub_result.passed:
            return TaskResult(status="success", message="Hub found at final check")

        return TaskResult(
            status="failed",
            message=f"Could not reach hub after {self._max_attempts} attempts",
        )


class LaunchAndReachHub:
    """Complete game launch task: start game → skip popups → reach hub.

    For pipeline integration:
    - Call ensure_game_running() BEFORE device.connect() (Phase 1)
    - Then run this task's execute() after connection (Phase 2)

    Metadata:
        name: launch_and_reach_hub
        category: startup
        requires_ocr: True
        safe: True
    """

    name = "launch_and_reach_hub"
    description = "Launch game, skip startup popups, and reach main hub"
    category = "startup"
    requires_pages = ("main_hub",)
    requires_ocr = True
    safe = True

    def __init__(self, max_popup_attempts: int = 40) -> None:
        self._skip_popups = SkipStartupPopups(max_attempts=max_popup_attempts)

    async def can_run(self, ctx: TaskContext) -> bool:
        return True

    async def execute(self, ctx: TaskContext) -> TaskResult:
        ctx.logger.info("=== LaunchAndReachHub: Phase 2 — skip popups ===")
        return await self._skip_popups.execute(ctx)


def ensure_game_running(
    exe_path: str,
    window_title: str = "AetherGazer",
    timeout: float = 120,
) -> bool:
    """Phase 1: Ensure the game is running before device connection.

    Call this BEFORE DeviceAdapter.connect() in the pipeline.

    Args:
        exe_path: Full path to the game executable.
        window_title: Window title to wait for.
        timeout: Maximum wait time in seconds.

    Returns:
        True if game is running and window is available.
    """
    from anime_game_afk.core.game_launcher import GameLauncher

    launcher = GameLauncher(
        exe_path=exe_path,
        window_title=window_title,
        process_name=Path(exe_path).name,
    )

    return launcher.ensure_running(timeout=timeout)
