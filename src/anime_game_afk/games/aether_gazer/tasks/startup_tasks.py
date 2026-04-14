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

import numpy as np

from anime_game_afk.games.aether_gazer.checks.ocr import OcrScanCheck
from anime_game_afk.games.aether_gazer.checks.page import AtHubCheck, OnPageCheck
from anime_game_afk.games.aether_gazer.checks.state import ScreenUnchangedCheck
from anime_game_afk.games.aether_gazer.knowledge.keys import (
    VK_ENTER,
    VK_ESCAPE,
    VK_SPACE,
)
from anime_game_afk.games.aether_gazer.ops.primitives import (
    ClickOp,
    PressKeyOp,
    ScreenshotOp,
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

        prev_img: np.ndarray | None = None
        unchanged_count = 0
        last_action = ""

        for attempt in range(self._max_attempts):
            # ── Fast hub check (template only, 5ms) ──
            on_hub = await OnPageCheck(page="main_hub").evaluate(ctx)
            if on_hub.passed:
                # Verify with OCR to be sure
                r = await OcrScanCheck().evaluate(ctx)
                ocr = r.data if r.passed else None
                if ocr and ocr.has_all("前往作战", "探测", "修正者", "仓库"):
                    ctx.logger.info(
                        f"  [startup] Hub reached after {attempt} attempts"
                    )
                    return TaskResult(
                        status="success",
                        message=f"Hub reached after {attempt} attempts",
                        data={"attempts": attempt},
                    )
                # Template matched but OCR didn't — might be exit dialog on top
                if ocr and (ocr.has("退出游戏") or ocr.has("是否退出")):
                    ctx.logger.info(
                        f"  [startup][{attempt}] Exit dialog on hub — cancelling"
                    )
                    await PressKeyOp(key=VK_ESCAPE, wait=1.0).run(ctx)
                    continue

            # ── OCR the screen ──
            r = await OcrScanCheck().evaluate(ctx)
            ocr = r.data if r.passed else None

            # ── Hub check via OCR alone ──
            if ocr and ocr.has_all("前往作战", "探测", "修正者", "仓库"):
                ctx.logger.info(
                    f"  [startup] Hub reached (OCR) after {attempt} attempts"
                )
                return TaskResult(
                    status="success",
                    message=f"Hub reached after {attempt} attempts",
                    data={"attempts": attempt},
                )

            # ── Login screen: "点击任意区域进入游戏" or game title ──
            if ocr and (ocr.has("进入游戏") or ocr.has("点击任意")
                    or ocr.has("点击屏幕") or ocr.has("开始游戏")
                    or ocr.has("触摸开始") or ocr.has("深空之眼")):
                ctx.logger.info(
                    f"  [startup][{attempt}] Login screen — clicking center"
                )
                await ClickOp(x=0.5, y=0.5, wait=3.0).run(ctx)  # center (800,450 @ 1600x900)
                last_action = "login_click"
                # Capture for stuck detection
                snap = await ScreenshotOp().run(ctx)
                prev_img = snap.data if snap.success else None
                unchanged_count = 0
                continue

            # ── Loading screen ──
            if ocr and (ocr.has("加载") or ocr.has("loading") or ocr.has("检查更新")
                    or ocr.has("下载") or ocr.has("解压")):
                ctx.logger.debug(
                    f"  [startup][{attempt}] Loading screen, waiting..."
                )
                await SleepOp(seconds=3.0).run(ctx)
                last_action = "wait_loading"
                snap = await ScreenshotOp().run(ctx)
                prev_img = snap.data if snap.success else None
                unchanged_count = 0
                continue

            # ── Idle/screensaver ──
            if ocr and ocr.has("正在播放"):
                ctx.logger.info(
                    f"  [startup][{attempt}] Idle screen — clicking to wake"
                )
                await ClickOp(x=0.5, y=0.444, wait=1.5).run(ctx)  # (800,400 @ 1600x900)
                last_action = "wake_idle"
                snap = await ScreenshotOp().run(ctx)
                prev_img = snap.data if snap.success else None
                unchanged_count = 0
                continue

            # ── Exit game dialog ──
            if ocr and (ocr.has("退出游戏") or ocr.has("是否退出")):
                ctx.logger.info(
                    f"  [startup][{attempt}] Exit dialog — pressing ESC"
                )
                await PressKeyOp(key=VK_ESCAPE, wait=1.0).run(ctx)
                last_action = "cancel_exit"
                snap = await ScreenshotOp().run(ctx)
                prev_img = snap.data if snap.success else None
                unchanged_count = 0
                continue

            # ── Event/announcement popup (try close button) ──
            if ocr and (ocr.has("活动") or ocr.has("公告") or ocr.has("通知")
                    or ocr.has("版本更新") or ocr.has("新赛季") or ocr.has("限时")):
                # Try X button in top-right
                ctx.logger.info(
                    f"  [startup][{attempt}] Event popup — clicking top-right close"
                )
                await ClickOp(x=0.963, y=0.056, wait=1.5).run(ctx)  # top-right close (1540,50 @ 1600x900)
                last_action = "close_event"
                snap = await ScreenshotOp().run(ctx)
                prev_img = snap.data if snap.success else None
                unchanged_count = 0
                continue

            # ── Clickable dismiss buttons (conservative list) ──
            # Only match specific button-like keywords, NOT "确认/确定" in body text
            handled = False
            if ocr:
                for kw in ["关闭", "知道了", "已知晓", "明天再来", "稍后再说"]:
                    match = ocr.find(kw)
                    if match:
                        cx = match.region.x + match.region.w // 2
                        cy = match.region.y + match.region.h // 2
                        ctx.logger.info(
                            f"  [startup][{attempt}] Clicking '{kw}' at ({cx},{cy})"
                        )
                        await ClickOp(x=cx / 1600, y=cy / 900, wait=1.5).run(ctx)
                        last_action = f"click_{kw}"
                        snap = await ScreenshotOp().run(ctx)
                        prev_img = snap.data if snap.success else None
                        unchanged_count = 0
                        handled = True
                        break

            if not handled:
                # No specific keyword found — check if screen is stuck
                if prev_img is not None:
                    unchanged_check = await ScreenUnchangedCheck(
                        prev_image=prev_img,
                    ).evaluate(ctx)
                    if unchanged_check.passed:
                        unchanged_count += 1
                    else:
                        unchanged_count = 0
                else:
                    unchanged_count = 0

                if unchanged_count >= 3:
                    # Screen stuck — aggressive dismiss
                    ctx.logger.info(
                        f"  [startup][{attempt}] Screen stuck "
                        f"({unchanged_count} unchanged) — aggressive dismiss"
                    )
                    await self._aggressive_dismiss(ctx)
                    unchanged_count = 0
                    last_action = "aggressive"
                else:
                    # Default: try ESC then click center
                    ctx.logger.debug(
                        f"  [startup][{attempt}] Unknown screen — ESC + click center"
                    )
                    await PressKeyOp(key=VK_ESCAPE, wait=1.0).run(ctx)
                    await ClickOp(x=0.5, y=0.5, wait=1.5).run(ctx)  # center (800,450 @ 1600x900)
                    last_action = "esc_click"

                # Capture current screen for next iteration's stuck detection
                snap = await ScreenshotOp().run(ctx)
                prev_img = snap.data if snap.success else None

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

    async def _aggressive_dismiss(self, ctx: TaskContext) -> None:
        """Try multiple strategies when screen is stuck."""
        # Try keys
        for key, name in [(VK_ESCAPE, "ESC"), (VK_ENTER, "Enter"), (VK_SPACE, "Space")]:
            await PressKeyOp(key=key, wait=0.5).run(ctx)

        # Try common close button positions (fractional coords)
        for x, y in [(0.963, 0.056), (0.5, 0.778), (0.5, 0.5)]:  # (1540,50), (800,700), (800,450) @ 1600x900
            await ClickOp(x=x, y=y, wait=0.8).run(ctx)

            hub_result = await AtHubCheck().evaluate(ctx)
            if hub_result.passed:
                return


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
