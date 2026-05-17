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
    # Mouse: plain SendMessage (block_input=false, MaaFw posts only window
    # messages and does NOT move the OS cursor).  DeviceAdapter.click()
    # spins up a short-lived CursorPin thread that spams SetCursorPos to
    # the target so Unity's GetCursorPos() reads the right point during
    # WM_LBUTTONDOWN/UP.  DeviceAdapter.swipe() uses a CursorWalk thread
    # that linearly interpolates from start→end at our own (fast) pace.
    # This avoids MaaFw's SendMessageWithCursorPos slow internal
    # interpolation (~8x slower than the requested swipe duration).
    mouse_method=MaaWin32InputMethodEnum.SendMessage,
    # Keyboard stays plain SendMessage (block_input=false, no stuck-key risk).
    keyboard_method=MaaWin32InputMethodEnum.SendMessage,
)
