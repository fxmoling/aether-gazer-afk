"""深空之眼游戏配置"""

from pathlib import Path

from maa.define import MaaWin32InputMethodEnum, MaaWin32ScreencapMethodEnum

from anime_game_afk.config.models import GameConfig

AETHER_GAZER_CONFIG = GameConfig(
    name="深空之眼",
    window_title="AetherGazer",
    resource_path=Path("assets/aether_gazer/resource"),
    screencap_method=MaaWin32ScreencapMethodEnum.Background,
    # SendMessageWithCursorPos: 先移动物理光标再发消息，Unity 游戏兼容性更好
    # M9A (重返未来1999) 也使用此方法
    mouse_method=MaaWin32InputMethodEnum.SendMessageWithCursorPos,
    keyboard_method=MaaWin32InputMethodEnum.SendMessageWithCursorPos,
)
