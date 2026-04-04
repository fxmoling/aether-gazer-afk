"""深空之眼游戏配置"""

from pathlib import Path

from maa.define import MaaWin32InputMethodEnum, MaaWin32ScreencapMethodEnum

from anime_game_afk.config.models import GameConfig

AETHER_GAZER_CONFIG = GameConfig(
    name="深空之眼",
    window_title="AetherGazer",
    resource_path=Path("assets/aether_gazer/resource"),
    screencap_method=MaaWin32ScreencapMethodEnum.Background,
    mouse_method=MaaWin32InputMethodEnum.SendMessage,
    keyboard_method=MaaWin32InputMethodEnum.SendMessage,
)
