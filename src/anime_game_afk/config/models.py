"""配置数据模型"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from maa.define import MaaWin32InputMethodEnum, MaaWin32ScreencapMethodEnum


@dataclass(frozen=True)
class GameConfig:
    """游戏配置"""

    name: str
    window_title: str
    resource_path: Path
    screencap_method: int = MaaWin32ScreencapMethodEnum.Background
    mouse_method: int = MaaWin32InputMethodEnum.SendMessage
    keyboard_method: int = MaaWin32InputMethodEnum.SendMessage
    # 设计分辨率 — 所有坐标以此为基准存储
    # 运行时自动缩放到实际窗口分辨率
    design_resolution: tuple[int, int] = (1600, 900)


@dataclass(frozen=True)
class StaminaConfig:
    """体力消耗配置"""

    auto_use_potion: bool = False
    max_potions: int = 0
    target_stage: str = ""


@dataclass
class TaskResult:
    """任务执行结果"""

    success: bool
    task_name: str
    message: str = ""
    duration: float = 0.0
    screenshots: list[Path] = field(default_factory=list)
