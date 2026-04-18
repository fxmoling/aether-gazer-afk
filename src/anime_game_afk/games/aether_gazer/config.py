"""深空之眼游戏配置"""

import sys
from pathlib import Path

from maa.define import MaaWin32InputMethodEnum, MaaWin32ScreencapMethodEnum

from anime_game_afk.config.models import GameConfig

if getattr(sys, "frozen", False):
    _BASE = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    # config.py -> aether_gazer/ -> games/ -> anime_game_afk/ -> src/ -> project_root
    _BASE = Path(__file__).resolve().parents[4]

AETHER_GAZER_CONFIG = GameConfig(
    name="深空之眼",
    window_title="AetherGazer",
    resource_path=_BASE / "assets" / "aether_gazer",  # placeholder; resource/ removed (unused)
    # FramePool: DXGI 帧池捕获，不发送窗口消息，游戏无法检测
    screencap_method=MaaWin32ScreencapMethodEnum.FramePool,
    # SendMessageWithCursorPos: 光标会瞬间闪动+BlockInput，但是Unity唯一有效输入方式
    # PostMessageWithWindowPos 会导致窗口跳变+画面闪烁，体验更差
    # TODO: 探索 CreateDesktopW / Android 模拟器方案彻底解决后台操作
    mouse_method=MaaWin32InputMethodEnum.SendMessageWithCursorPos,
    keyboard_method=MaaWin32InputMethodEnum.SendMessageWithCursorPos,
)
