"""Cross-process infrastructure recovery.

Handles ONLY infrastructure-level failures that no single process can handle:
- device_disconnected: MaaFw controller lost connection
- window_lost: Game window closed or minimized
- screenshot_timeout: Screenshot capture fails repeatedly
- game_crash: Game process exited unexpectedly
- session_expired: Login session timed out (game kicked to title screen)

Game-level failures (battle failed, stamina empty, wrong page) are handled
within processes (Layer 7) and tasks (Layer 6).
"""
from __future__ import annotations

import asyncio
from enum import Enum
from typing import Protocol

from anime_game_afk.runtime.logger import get_logger

logger = get_logger("orchestrator.recovery")


class InfraFailure(Enum):
    """Infrastructure failure types that recovery can handle."""
    DEVICE_DISCONNECTED = "device_disconnected"
    WINDOW_LOST = "window_lost"
    SCREENSHOT_TIMEOUT = "screenshot_timeout"
    GAME_CRASH = "game_crash"
    SESSION_EXPIRED = "session_expired"


class DeviceHandle(Protocol):
    """Minimal device interface needed by recovery.

    Matches DeviceAdapter but only requires the methods recovery uses.
    Allows easy mocking in tests.
    """

    @property
    def connected(self) -> bool: ...
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def screenshot(self) -> object: ...
    def click(self, x: float, y: float) -> None: ...
    def press_key(self, vk_code: int) -> None: ...


class RecoveryManager:
    """Attempt to recover from infrastructure failures.

    Usage::

        recovery = RecoveryManager(device=device_adapter)
        recovered = await recovery.handle(InfraFailure.WINDOW_LOST)
        if not recovered:
            # pipeline should abort
    """

    # Maximum retries per recovery attempt before giving up
    MAX_RETRIES: int = 3
    # Delay between retry attempts in seconds
    RETRY_DELAY_S: float = 5.0
    # Delay after game crash before reconnect attempt
    CRASH_WAIT_S: float = 15.0

    def __init__(self, device: DeviceHandle) -> None:
        self._device = device
        self._strategies = {
            InfraFailure.DEVICE_DISCONNECTED: self._recover_device_disconnected,
            InfraFailure.WINDOW_LOST: self._recover_window_lost,
            InfraFailure.SCREENSHOT_TIMEOUT: self._recover_screenshot_timeout,
            InfraFailure.GAME_CRASH: self._recover_game_crash,
            InfraFailure.SESSION_EXPIRED: self._recover_session_expired,
        }

    async def handle(self, failure: InfraFailure) -> bool:
        """Attempt to recover from the given infrastructure failure.

        Args:
            failure: The type of infrastructure failure that occurred.

        Returns:
            True if recovery succeeded and pipeline can continue.
            False if recovery failed and pipeline should abort.
        """
        strategy = self._strategies.get(failure)
        if strategy is None:
            logger.error("No recovery strategy for {failure}", failure=failure.value)
            return False

        logger.warning(
            "Infrastructure failure detected: {failure}. Attempting recovery...",
            failure=failure.value,
        )

        for attempt in range(1, self.MAX_RETRIES + 1):
            logger.info(
                "Recovery attempt {attempt}/{max} for {failure}",
                attempt=attempt,
                max=self.MAX_RETRIES,
                failure=failure.value,
            )
            try:
                success = await strategy()
                if success:
                    logger.info(
                        "Recovery succeeded for {failure} on attempt {attempt}",
                        failure=failure.value,
                        attempt=attempt,
                    )
                    return True
            except Exception as e:
                logger.error(
                    "Recovery attempt {attempt} raised exception: {err}",
                    attempt=attempt,
                    err=str(e),
                )

            if attempt < self.MAX_RETRIES:
                logger.info(
                    "Waiting {delay}s before next attempt...",
                    delay=self.RETRY_DELAY_S,
                )
                await asyncio.sleep(self.RETRY_DELAY_S)

        logger.error(
            "Recovery FAILED for {failure} after {max} attempts",
            failure=failure.value,
            max=self.MAX_RETRIES,
        )
        return False

    async def _recover_device_disconnected(self) -> bool:
        """Reconnect MaaFw controller to the game window.

        Strategy: disconnect cleanly, wait briefly, reconnect.
        """
        try:
            self._device.disconnect()
        except Exception:
            pass  # Already disconnected, ignore

        await asyncio.sleep(2.0)

        try:
            self._device.connect()
            return self._device.connected
        except Exception as e:
            logger.error("Reconnect failed: {err}", err=str(e))
            return False

    async def _recover_window_lost(self) -> bool:
        """Recover from game window lost (closed, minimized, moved offscreen).

        Strategy: disconnect, wait for window to reappear, reconnect.
        If the game window was merely minimized, MaaFw reconnect will find it.
        """
        try:
            self._device.disconnect()
        except Exception:
            pass

        await asyncio.sleep(3.0)

        try:
            self._device.connect()
            if not self._device.connected:
                return False
            # Verify we can actually capture a screenshot
            self._device.screenshot()
            return True
        except Exception as e:
            logger.error("Window recovery failed: {err}", err=str(e))
            return False

    async def _recover_screenshot_timeout(self) -> bool:
        """Recover from repeated screenshot capture failures.

        Strategy: try taking a screenshot directly. If that fails,
        full reconnect cycle.
        """
        try:
            self._device.screenshot()
            return True
        except Exception:
            pass

        # Full reconnect
        try:
            self._device.disconnect()
        except Exception:
            pass

        await asyncio.sleep(2.0)

        try:
            self._device.connect()
            self._device.screenshot()
            return True
        except Exception as e:
            logger.error("Screenshot recovery failed: {err}", err=str(e))
            return False

    async def _recover_game_crash(self) -> bool:
        """Recover from game process crash / unexpected exit.

        Strategy: wait for game to potentially auto-restart or for the
        user to manually restart it, then reconnect. This is the most
        severe failure — we wait longer before attempting reconnect.
        """
        logger.warning(
            "Game crash detected. Waiting {wait}s for restart...",
            wait=self.CRASH_WAIT_S,
        )
        await asyncio.sleep(self.CRASH_WAIT_S)

        try:
            self._device.disconnect()
        except Exception:
            pass

        try:
            self._device.connect()
            if not self._device.connected:
                return False
            # Verify screenshot works after reconnect
            self._device.screenshot()
            return True
        except Exception as e:
            logger.error("Game crash recovery failed: {err}", err=str(e))
            return False

    async def _recover_session_expired(self) -> bool:
        """Recover from login session expiry (kicked to title screen).

        Strategy: reconnect to device, then simulate clicking through
        the title screen to re-enter the game. The title screen typically
        has a "tap to start" prompt followed by server select / login.

        VK_RETURN (0x0D) is used to confirm prompts.
        """
        # Ensure device is connected
        if not self._device.connected:
            try:
                self._device.connect()
            except Exception as e:
                logger.error(
                    "Cannot reconnect for session recovery: {err}", err=str(e)
                )
                return False

        # Click center of screen to dismiss "tap to start"
        self._device.click(0.5, 0.5)
        await asyncio.sleep(3.0)

        # Press Enter to confirm any login prompts
        self._device.press_key(0x0D)  # VK_RETURN
        await asyncio.sleep(5.0)

        # Press Enter again for server select / announcements
        self._device.press_key(0x0D)
        await asyncio.sleep(3.0)

        # Verify we can screenshot (proves we're connected and in-game)
        try:
            self._device.screenshot()
            return True
        except Exception as e:
            logger.error("Session recovery failed: {err}", err=str(e))
            return False
