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
    # 鼠标必须用 SendMessageWithCursorPos：Unity 引擎读光标位置而非鼠标消息坐标，
    # 不带 CursorPos 的方式点击会落在屏幕中心（光标不动）。代价是它会调用
    # BlockInput(TRUE/FALSE) 阻塞用户键鼠输入约 1ms/click。
    mouse_method=MaaWin32InputMethodEnum.SendMessageWithCursorPos,
    # 键盘用 *纯* SendMessage：MaaFw 源码确认 keyboard 路径完全不调用 BlockInput
    # 且不需要光标位置。这样脚本运行时频繁的 press_key/hold_key 完全不会
    # 影响用户的键鼠输入。当 mouse/keyboard method 不同时 MaaFw 会创建两个
    # 独立的 Input 实例（见 Win32ControlUnitMgr.cpp L69-76）。
    keyboard_method=MaaWin32InputMethodEnum.SendMessage,
)
