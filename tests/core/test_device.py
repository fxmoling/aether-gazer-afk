"""Unit tests for DeviceAdapter.

All MaaFramework dependencies are fully mocked — no real game window
or MaaFw installation required to run these tests.
"""
from __future__ import annotations

import ctypes
from typing import Any
from unittest.mock import MagicMock, call, patch

import numpy as np
import pytest

from anime_game_afk.core.device import DeviceAdapter
from anime_game_afk.core.errors import (
    DeviceConnectionError,
    ScreenshotError,
    WindowNotFoundError,
)
from anime_game_afk.core.types import DeviceConfig, Resolution


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_config(
    *,
    window_title: str = "TestWindow",
) -> DeviceConfig:
    """Build a DeviceConfig for testing."""
    return DeviceConfig(
        window_title=window_title,
        screencap_method=4,   # FramePool
        mouse_method=256,     # SendMessageWithCursorPos
        keyboard_method=256,  # SendMessageWithCursorPos
    )


def _fake_window(name: str, hwnd: int = 1, class_name: str = "FakeClass") -> MagicMock:
    """Return a mock desktop-window object."""
    w = MagicMock()
    w.window_name = name
    w.hwnd = ctypes.c_void_p(hwnd)
    w.class_name = class_name
    return w


def _make_controller_mock(
    *,
    resolution: tuple[int, int] = (1600, 900),
    screencap_img: np.ndarray | None = None,
) -> MagicMock:
    """Return a fully-stubbed Win32Controller mock."""
    ctrl = MagicMock()

    # post_connection().wait() chain
    ctrl.post_connection.return_value = MagicMock(
        wait=MagicMock(return_value=None)
    )
    # set_screenshot_use_raw_size is a plain call
    ctrl.set_screenshot_use_raw_size.return_value = None

    # resolution property
    type(ctrl).resolution = property(lambda self: resolution)

    # screencap chain: post_screencap().wait().get()
    if screencap_img is None:
        screencap_img = np.zeros(
            (resolution[1], resolution[0], 3), dtype=np.uint8
        )
    screencap_job = MagicMock()
    screencap_job.wait.return_value = screencap_job
    screencap_job.get.return_value = screencap_img
    ctrl.post_screencap.return_value = screencap_job

    # click / swipe / press_key chains
    action_job = MagicMock()
    action_job.wait.return_value = action_job
    ctrl.post_click.return_value = action_job
    ctrl.post_swipe.return_value = action_job
    ctrl.post_press_key.return_value = action_job

    return ctrl


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_initial_state_not_connected() -> None:
    """A freshly created adapter must not be connected."""
    cfg = _make_config()
    adapter = DeviceAdapter(cfg)
    assert not adapter.connected


def test_config_property() -> None:
    cfg = _make_config()
    adapter = DeviceAdapter(cfg)
    assert adapter.config is cfg


# ---------------------------------------------------------------------------
# find_window
# ---------------------------------------------------------------------------


def test_find_window_success() -> None:
    """find_window must return the HWND when a matching window exists."""
    cfg = _make_config(window_title="TestWindow")
    adapter = DeviceAdapter(cfg)

    windows = [
        _fake_window("OtherApp", hwnd=10),
        _fake_window("TestWindow - Level 1", hwnd=42, class_name="UnityWndClass"),
    ]
    with patch("anime_game_afk.core.device.Toolkit") as mock_toolkit:
        mock_toolkit.find_desktop_windows.return_value = windows
        hwnd = adapter.find_window()

    # ctypes.c_void_p does not implement __eq__ by value; compare .value
    assert hwnd.value == ctypes.c_void_p(42).value  # type: ignore[union-attr]


def test_find_window_not_found() -> None:
    """find_window must raise WindowNotFoundError when no window matches."""
    cfg = _make_config(window_title="MissingGame")
    adapter = DeviceAdapter(cfg)

    with patch("anime_game_afk.core.device.Toolkit") as mock_toolkit:
        mock_toolkit.find_desktop_windows.return_value = [
            _fake_window("SomeOtherApp")
        ]
        with pytest.raises(WindowNotFoundError, match="MissingGame"):
            adapter.find_window()


def test_find_window_empty_list() -> None:
    cfg = _make_config(window_title="Game")
    adapter = DeviceAdapter(cfg)

    with patch("anime_game_afk.core.device.Toolkit") as mock_toolkit:
        mock_toolkit.find_desktop_windows.return_value = []
        with pytest.raises(WindowNotFoundError):
            adapter.find_window()


# ---------------------------------------------------------------------------
# connect / disconnect state transitions
# ---------------------------------------------------------------------------


@pytest.fixture()
def connected_adapter() -> DeviceAdapter:
    """Return a DeviceAdapter that has been successfully connected."""
    cfg = _make_config()
    adapter = DeviceAdapter(cfg)
    ctrl_mock = _make_controller_mock(resolution=(1600, 900))

    with (
        patch("anime_game_afk.core.device.Toolkit") as mock_toolkit,
        patch(
            "anime_game_afk.core.device.Win32Controller",
            return_value=ctrl_mock,
        ),
    ):
        mock_toolkit.find_desktop_windows.return_value = [
            _fake_window("TestWindow")
        ]
        adapter.connect()

    # Store the mock for assertion convenience
    adapter._ctrl_mock = ctrl_mock  # type: ignore[attr-defined]
    return adapter


def test_connect_sets_connected_true(connected_adapter: DeviceAdapter) -> None:
    assert connected_adapter.connected


def test_connect_stores_actual_resolution(
    connected_adapter: DeviceAdapter,
) -> None:
    """actual_resolution must be populated from the controller after connect."""
    assert connected_adapter.actual_resolution == Resolution(1600, 900)


def test_disconnect_sets_connected_false(
    connected_adapter: DeviceAdapter,
) -> None:
    connected_adapter.disconnect()
    assert not connected_adapter.connected


def test_disconnect_resets_state(
    connected_adapter: DeviceAdapter,
) -> None:
    """After disconnect, actual_resolution must raise DeviceConnectionError."""
    connected_adapter.disconnect()
    with pytest.raises(DeviceConnectionError):
        _ = connected_adapter.actual_resolution


def test_connect_raises_when_window_missing() -> None:
    cfg = _make_config(window_title="Ghost")
    adapter = DeviceAdapter(cfg)

    with patch("anime_game_afk.core.device.Toolkit") as mock_toolkit:
        mock_toolkit.find_desktop_windows.return_value = []
        with pytest.raises(WindowNotFoundError):
            adapter.connect()


def test_connect_raises_connection_error_on_controller_failure() -> None:
    cfg = _make_config()
    adapter = DeviceAdapter(cfg)

    with (
        patch("anime_game_afk.core.device.Toolkit") as mock_toolkit,
        patch(
            "anime_game_afk.core.device.Win32Controller",
            side_effect=RuntimeError("driver error"),
        ),
    ):
        mock_toolkit.find_desktop_windows.return_value = [
            _fake_window("TestWindow")
        ]
        with pytest.raises(DeviceConnectionError, match="driver error"):
            adapter.connect()


# ---------------------------------------------------------------------------
# Coordinate scaling
# ---------------------------------------------------------------------------


def test_click_fractional_coords() -> None:
    """click(fx, fy) must convert fractional coords to actual pixels."""
    cfg = _make_config()
    adapter = DeviceAdapter(cfg)
    ctrl_mock = _make_controller_mock(resolution=(1600, 900))

    with (
        patch("anime_game_afk.core.device.Toolkit") as mock_toolkit,
        patch(
            "anime_game_afk.core.device.Win32Controller",
            return_value=ctrl_mock,
        ),
    ):
        mock_toolkit.find_desktop_windows.return_value = [
            _fake_window("TestWindow")
        ]
        adapter.connect()
        adapter.click(0.25, 0.5)

    # 0.25 * 1600 = 400, 0.5 * 900 = 450
    ctrl_mock.post_click.assert_called_once_with(400, 450)


def test_click_center() -> None:
    """click(0.5, 0.5) must map to the center of the actual resolution."""
    cfg = _make_config()
    adapter = DeviceAdapter(cfg)
    ctrl_mock = _make_controller_mock(resolution=(1920, 1080))

    with (
        patch("anime_game_afk.core.device.Toolkit") as mock_toolkit,
        patch(
            "anime_game_afk.core.device.Win32Controller",
            return_value=ctrl_mock,
        ),
    ):
        mock_toolkit.find_desktop_windows.return_value = [
            _fake_window("TestWindow")
        ]
        adapter.connect()
        adapter.click(0.5, 0.5)

    # 0.5 * 1920 = 960, 0.5 * 1080 = 540
    ctrl_mock.post_click.assert_called_once_with(960, 540)


def test_swipe_fractional_coords() -> None:
    """Swipe endpoints must be converted from fractional to actual pixels."""
    cfg = _make_config()
    adapter = DeviceAdapter(cfg)
    ctrl_mock = _make_controller_mock(resolution=(1600, 900))

    with (
        patch("anime_game_afk.core.device.Toolkit") as mock_toolkit,
        patch(
            "anime_game_afk.core.device.Win32Controller",
            return_value=ctrl_mock,
        ),
    ):
        mock_toolkit.find_desktop_windows.return_value = [
            _fake_window("TestWindow")
        ]
        adapter.connect()
        adapter.swipe(0.0, 0.0, 0.5, 0.25, duration=300)

    # 0*1600=0, 0*900=0, 0.5*1600=800, 0.25*900=225
    ctrl_mock.post_swipe.assert_called_once_with(0, 0, 800, 225, 300)


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------


def test_screenshot_scales_down_to_max_height() -> None:
    """screenshot() must scale down proportionally when height > MAX_HEIGHT (720)."""
    actual_w, actual_h = 3200, 1800  # taller than 720

    actual_img = np.zeros((actual_h, actual_w, 3), dtype=np.uint8)
    cfg = _make_config()
    adapter = DeviceAdapter(cfg)
    ctrl_mock = _make_controller_mock(
        resolution=(actual_w, actual_h), screencap_img=actual_img
    )

    with (
        patch("anime_game_afk.core.device.Toolkit") as mock_toolkit,
        patch(
            "anime_game_afk.core.device.Win32Controller",
            return_value=ctrl_mock,
        ),
    ):
        mock_toolkit.find_desktop_windows.return_value = [
            _fake_window("TestWindow")
        ]
        adapter.connect()
        img = adapter.screenshot()

    # scale = 720 / 1800 = 0.4, new_w = int(3200 * 0.4) = 1280
    assert img.shape == (720, 1280, 3)


def test_screenshot_no_resize_when_height_within_max() -> None:
    """screenshot() must NOT resize when height ≤ MAX_HEIGHT (720)."""
    img_data = np.ones((720, 1280, 3), dtype=np.uint8) * 127
    cfg = _make_config()
    adapter = DeviceAdapter(cfg)
    ctrl_mock = _make_controller_mock(
        resolution=(1280, 720), screencap_img=img_data
    )

    with (
        patch("anime_game_afk.core.device.Toolkit") as mock_toolkit,
        patch(
            "anime_game_afk.core.device.Win32Controller",
            return_value=ctrl_mock,
        ),
    ):
        mock_toolkit.find_desktop_windows.return_value = [
            _fake_window("TestWindow")
        ]
        adapter.connect()
        img = adapter.screenshot()

    assert img.shape == (720, 1280, 3)
    # Pixel values must be preserved (no resize distortion)
    np.testing.assert_array_equal(img, img_data)


def test_screenshot_raw_returns_actual_resolution_image() -> None:
    """screenshot_raw() must return the image without resizing."""
    actual_w, actual_h = 3200, 1800
    actual_img = np.zeros((actual_h, actual_w, 3), dtype=np.uint8)
    cfg = _make_config()
    adapter = DeviceAdapter(cfg)
    ctrl_mock = _make_controller_mock(
        resolution=(actual_w, actual_h), screencap_img=actual_img
    )

    with (
        patch("anime_game_afk.core.device.Toolkit") as mock_toolkit,
        patch(
            "anime_game_afk.core.device.Win32Controller",
            return_value=ctrl_mock,
        ),
    ):
        mock_toolkit.find_desktop_windows.return_value = [
            _fake_window("TestWindow")
        ]
        adapter.connect()
        img = adapter.screenshot_raw()

    assert img.shape == (actual_h, actual_w, 3)


def test_screenshot_raises_when_get_returns_none() -> None:
    cfg = _make_config()
    adapter = DeviceAdapter(cfg)
    ctrl_mock = _make_controller_mock()
    # Override the screencap chain so .get() returns None
    screencap_job = MagicMock()
    screencap_job.wait.return_value = screencap_job
    screencap_job.get.return_value = None
    ctrl_mock.post_screencap.return_value = screencap_job

    with (
        patch("anime_game_afk.core.device.Toolkit") as mock_toolkit,
        patch(
            "anime_game_afk.core.device.Win32Controller",
            return_value=ctrl_mock,
        ),
    ):
        mock_toolkit.find_desktop_windows.return_value = [
            _fake_window("TestWindow")
        ]
        # connect() calls post_screencap internally; give it a valid image
        # by swapping after connect is done
        adapter.connect()
        # Now swap to None-returning mock
        adapter._controller = ctrl_mock  # type: ignore[assignment]
        with pytest.raises(ScreenshotError):
            adapter.screenshot()


# ---------------------------------------------------------------------------
# press_key / hold_key
# ---------------------------------------------------------------------------


def test_press_key_delegation(connected_adapter: DeviceAdapter) -> None:
    """press_key must forward the vk_code to the controller."""
    connected_adapter.press_key(0x0D)  # VK_RETURN
    connected_adapter._ctrl_mock.post_press_key.assert_called_once_with(0x0D)  # type: ignore[attr-defined]


def test_hold_key_presses_repeatedly(
    connected_adapter: DeviceAdapter,
) -> None:
    """hold_key must press the key multiple times over the duration."""
    with patch("anime_game_afk.core.device.time") as mock_time:
        # Simulate time passing: first call returns 0, then increments
        call_count = 0
        def fake_monotonic() -> float:
            nonlocal call_count
            call_count += 1
            # First few calls return 0 (before end_time), then exceed it
            if call_count <= 3:
                return 0.0
            return 1.0  # exceeds any reasonable duration

        mock_time.monotonic = fake_monotonic
        mock_time.sleep = MagicMock()
        connected_adapter.hold_key(0x57, 0.3)  # VK_W, 0.3s

    # Should have pressed the key at least once
    assert connected_adapter._ctrl_mock.post_press_key.call_count >= 1  # type: ignore[attr-defined]
    # All presses should be the same key
    for c in connected_adapter._ctrl_mock.post_press_key.call_args_list:  # type: ignore[attr-defined]
        assert c == call(0x57)


# ---------------------------------------------------------------------------
# _ensure_connected guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method_call",
    [
        lambda d: d.screenshot(),
        lambda d: d.screenshot_raw(),
        lambda d: d.click(0, 0),
        lambda d: d.swipe(0, 0, 1, 1),
        lambda d: d.press_key(0),
        lambda d: d.hold_key(0, 0.1),
    ],
)
def test_operations_raise_when_not_connected(
    method_call: Any,
) -> None:
    """All I/O methods must raise DeviceConnectionError when not connected."""
    cfg = _make_config()
    adapter = DeviceAdapter(cfg)
    with pytest.raises(DeviceConnectionError):
        method_call(adapter)
