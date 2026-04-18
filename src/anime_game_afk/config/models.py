"""配置数据模型"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from maa.define import MaaWin32InputMethodEnum, MaaWin32ScreencapMethodEnum

from anime_game_afk.core.types import DeviceConfig


@dataclass(frozen=True)
class GameConfig:
    """游戏配置"""

    name: str
    window_title: str
    resource_path: Path
    screencap_method: int = MaaWin32ScreencapMethodEnum.Background
    mouse_method: int = MaaWin32InputMethodEnum.SendMessage
    keyboard_method: int = MaaWin32InputMethodEnum.SendMessage

    def to_device_config(self) -> DeviceConfig:
        """Convert to a :class:`DeviceConfig` for :class:`DeviceAdapter`."""
        return DeviceConfig(
            window_title=self.window_title,
            screencap_method=self.screencap_method,
            mouse_method=self.mouse_method,
            keyboard_method=self.keyboard_method,
        )
