"""Tests for infrastructure recovery strategies."""
from __future__ import annotations

import pytest

from anime_game_afk.games.aether_gazer.orchestrator.recovery import (
    InfraFailure,
    RecoveryManager,
)


class FakeDevice:
    """Mock device for recovery tests."""

    def __init__(self) -> None:
        self._connected = True
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.screenshot_calls = 0
        self.click_calls: list[tuple[int, int]] = []
        self.key_calls: list[int] = []
        # Control behavior
        self.connect_succeeds = True
        self.screenshot_succeeds = True

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        self.connect_calls += 1
        if not self.connect_succeeds:
            raise ConnectionError("Mock connect failed")
        self._connected = True

    def disconnect(self) -> None:
        self.disconnect_calls += 1
        self._connected = False

    def screenshot(self) -> object:
        self.screenshot_calls += 1
        if not self.screenshot_succeeds:
            raise RuntimeError("Mock screenshot failed")
        return object()

    def click(self, x: int, y: int) -> None:
        self.click_calls.append((x, y))

    def press_key(self, vk_code: int) -> None:
        self.key_calls.append(vk_code)


@pytest.fixture
def device() -> FakeDevice:
    return FakeDevice()


@pytest.fixture
def recovery(device: FakeDevice) -> RecoveryManager:
    mgr = RecoveryManager(device=device)
    # Speed up tests by reducing delays
    mgr.RETRY_DELAY_S = 0.01
    mgr.CRASH_WAIT_S = 0.01
    return mgr


class TestRecoveryDeviceDisconnected:
    @pytest.mark.asyncio
    async def test_reconnect_success(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        result = await recovery.handle(InfraFailure.DEVICE_DISCONNECTED)
        assert result is True
        assert device.connect_calls >= 1

    @pytest.mark.asyncio
    async def test_reconnect_failure(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        device.connect_succeeds = False
        result = await recovery.handle(InfraFailure.DEVICE_DISCONNECTED)
        assert result is False


class TestRecoveryWindowLost:
    @pytest.mark.asyncio
    async def test_window_recovery_success(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        result = await recovery.handle(InfraFailure.WINDOW_LOST)
        assert result is True
        assert device.screenshot_calls >= 1

    @pytest.mark.asyncio
    async def test_window_recovery_screenshot_fails(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        device.screenshot_succeeds = False
        result = await recovery.handle(InfraFailure.WINDOW_LOST)
        assert result is False


class TestRecoveryScreenshotTimeout:
    @pytest.mark.asyncio
    async def test_screenshot_works_immediately(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        result = await recovery.handle(InfraFailure.SCREENSHOT_TIMEOUT)
        assert result is True

    @pytest.mark.asyncio
    async def test_screenshot_needs_reconnect(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        call_count = 0
        original_screenshot = device.screenshot

        def flaky_screenshot() -> object:
            nonlocal call_count
            call_count += 1
            # First call fails, subsequent calls succeed
            if call_count == 1:
                raise RuntimeError("timeout")
            return original_screenshot()

        device.screenshot = flaky_screenshot  # type: ignore[method-assign]
        result = await recovery.handle(InfraFailure.SCREENSHOT_TIMEOUT)
        assert result is True


class TestRecoveryGameCrash:
    @pytest.mark.asyncio
    async def test_crash_recovery_success(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        result = await recovery.handle(InfraFailure.GAME_CRASH)
        assert result is True
        assert device.connect_calls >= 1

    @pytest.mark.asyncio
    async def test_crash_recovery_game_not_restarted(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        device.connect_succeeds = False
        result = await recovery.handle(InfraFailure.GAME_CRASH)
        assert result is False


class TestRecoverySessionExpired:
    @pytest.mark.asyncio
    async def test_session_recovery_success(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        result = await recovery.handle(InfraFailure.SESSION_EXPIRED)
        assert result is True
        # Should click center screen + press Enter twice
        assert len(device.click_calls) >= 1
        assert len(device.key_calls) >= 2

    @pytest.mark.asyncio
    async def test_session_recovery_device_dead(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        device._connected = False
        device.connect_succeeds = False
        result = await recovery.handle(InfraFailure.SESSION_EXPIRED)
        assert result is False


class TestRecoveryRetries:
    @pytest.mark.asyncio
    async def test_retries_up_to_max(
        self, recovery: RecoveryManager, device: FakeDevice
    ) -> None:
        device.connect_succeeds = False
        result = await recovery.handle(InfraFailure.DEVICE_DISCONNECTED)
        assert result is False
        # Should have tried MAX_RETRIES times
        assert device.connect_calls == recovery.MAX_RETRIES
