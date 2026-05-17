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
    # 鼠标用纯 SendMessage（不带 CursorPos 后缀）：MaaFw 源码确认此路径
    # `block_input=false`，完全不调用 BlockInput → 没有卡 Ctrl 风险。
    # Unity 在处理消息时读取 GetCursorPos()，所以 DeviceAdapter.click()
    # 自己用 SetCursorPos 把光标短暂放到目标位置；同时 InputGuard
    # (WH_MOUSE_LL 钩子) 在那 ~20ms 窗口里吸收用户的真实鼠标事件，
    # 保证用户即使快速移动鼠标也无法干扰点击落点。
    # 参见: MaaWin32ControlUnit/Manager/Win32ControlUnitMgr.cpp make_input
    mouse_method=MaaWin32InputMethodEnum.SendMessage,
    # 键盘用同样的纯 SendMessage：源码确认 block_input=false。
    keyboard_method=MaaWin32InputMethodEnum.SendMessage,
)
