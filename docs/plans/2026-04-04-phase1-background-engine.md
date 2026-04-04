# Phase 1 后台无感运行能力实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立完全后台运行的游戏自动化核心能力，支持最小化窗口下的图像识别和输入模拟

**Architecture:** 分层架构，严格的类型系统，Protocol-based接口，每个模块单一职责

**Tech Stack:** Python 3.11, mypy strict mode, opencv-python, numpy, pywin32, pytest

---

## 文件结构规划

**将创建的核心文件：**
```
src/anime_game_afk/
├── __init__.py
├── types/
│   ├── __init__.py, README.md
│   ├── base.py           # 基础数据类型
│   ├── vision.py         # 视觉相关类型  
│   └── input.py          # 输入相关类型
├── core/
│   ├── __init__.py, README.md
│   ├── window_manager.py # 窗口管理器
│   ├── vision_engine.py  # 图像识别引擎
│   ├── input_engine.py   # 输入模拟引擎
│   └── background_engine.py # 后台运行引擎
├── utils/
│   ├── __init__.py, README.md
│   └── logger.py         # 日志工具
tests/
├── conftest.py           # 测试配置
├── types/               
├── core/
└── utils/
pyproject.toml           # 项目配置
```

---

### Task 1: 项目基础结构和类型系统

**Files:**
- Create: `pyproject.toml`
- Create: `src/anime_game_afk/__init__.py`
- Create: `src/anime_game_afk/types/__init__.py`
- Create: `src/anime_game_afk/types/README.md`
- Create: `src/anime_game_afk/types/base.py`
- Test: `tests/conftest.py`

- [ ] **Step 1: 创建项目配置文件**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "anime-game-afk"
version = "0.1.0"
description = "Universal game automation platform with background operation support"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "numpy>=1.24.0",
    "opencv-python>=4.8.0",
    "pywin32>=306; sys_platform=='win32'",
    "typing-extensions>=4.8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0", 
    "mypy>=1.5.0",
    "black>=23.7.0",
    "isort>=5.12.0",
    "flake8>=6.0.0",
]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
show_error_codes = true

[tool.black]
line-length = 88
target-version = ['py311']

[tool.isort]
profile = "black"
multi_line_output = 3

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--cov=src --cov-report=html --cov-report=term --strict-markers"
```

- [ ] **Step 2: 创建包入口文件**

```python
"""Anime Game AFK - Universal game automation platform."""

__version__ = "0.1.0"
__author__ = "Anime Game AFK Team"

# 导出核心类型
from .types.base import Point, Rect, Size
from .types.vision import MatchResult, RecognitionResult
from .types.input import InputAction, ActionResult

__all__ = [
    "Point",
    "Rect", 
    "Size",
    "MatchResult",
    "RecognitionResult", 
    "InputAction",
    "ActionResult",
]
```

- [ ] **Step 3: 创建基础类型定义**

```python
"""基础数据类型定义。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NewType

# 基础几何类型
@dataclass(frozen=True)
class Point:
    """二维点坐标。"""
    x: int
    y: int
    
    def __add__(self, other: Point) -> Point:
        return Point(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: Point) -> Point:
        return Point(self.x - other.x, self.y - other.y)

@dataclass(frozen=True) 
class Size:
    """尺寸大小。"""
    width: int
    height: int
    
    @property
    def area(self) -> int:
        return self.width * self.height

@dataclass(frozen=True)
class Rect:
    """矩形区域，使用左上角坐标和尺寸定义。"""
    x: int
    y: int
    width: int
    height: int
    
    @property
    def left(self) -> int:
        return self.x
    
    @property
    def top(self) -> int:
        return self.y
        
    @property
    def right(self) -> int:
        return self.x + self.width
        
    @property
    def bottom(self) -> int:
        return self.y + self.height
        
    @property
    def center(self) -> Point:
        return Point(self.x + self.width // 2, self.y + self.height // 2)
        
    @property
    def size(self) -> Size:
        return Size(self.width, self.height)
    
    def contains(self, point: Point) -> bool:
        """检查点是否在矩形内。"""
        return (
            self.x <= point.x < self.right
            and self.y <= point.y < self.bottom
        )
    
    def intersects(self, other: Rect) -> bool:
        """检查是否与另一个矩形相交。"""
        return not (
            self.right <= other.x
            or self.x >= other.right  
            or self.bottom <= other.y
            or self.y >= other.bottom
        )

# 句柄类型
WindowHandle = NewType("WindowHandle", int)
ProcessId = NewType("ProcessId", int)
ThreadId = NewType("ThreadId", int)

# 配置类型
@dataclass
class EngineConfig:
    """引擎基础配置。"""
    debug_mode: bool = False
    log_level: str = "INFO"
    timeout_seconds: float = 30.0
    retry_count: int = 3
    
    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.retry_count < 0:
            raise ValueError("retry_count must be non-negative")
```

- [ ] **Step 4: 创建类型模块README**

```markdown
# types - 类型定义模块

## 目录职责

定义整个项目使用的数据类型、协议接口和配置模型，为所有模块提供类型安全保障。

## 文件组织规范

- `base.py` - 基础几何类型和配置类型
- `vision.py` - 图像识别相关类型
- `input.py` - 输入模拟相关类型  
- `task.py` - 任务编排相关类型（后续添加）

## 设计原则

1. **不可变数据类型**：使用 `@dataclass(frozen=True)` 确保类型安全
2. **严格类型检查**：所有类型都要通过 `mypy --strict` 检查
3. **协议优于继承**：使用 `Protocol` 定义接口约定
4. **NewType包装**：对原生类型进行语义化包装

## 接口说明

### 基础类型
- `Point`: 二维坐标点，支持基本运算
- `Size`: 尺寸大小，提供面积计算
- `Rect`: 矩形区域，提供几何判断方法
- `WindowHandle/ProcessId/ThreadId`: 系统资源句柄

### 配置类型
- `EngineConfig`: 引擎基础配置，包含调试、超时、重试等设置

## 使用示例

```python
from anime_game_afk.types import Point, Rect, WindowHandle

# 创建几何对象
point = Point(100, 200)
rect = Rect(50, 50, 200, 150)

# 几何运算
center = rect.center
contains = rect.contains(point)

# 类型安全的句柄
hwnd = WindowHandle(12345)
```

## 注意事项

- 所有类型都是不可变的，修改需要创建新实例
- 几何类型使用整数坐标，符合像素精度要求
- 配置类型包含验证逻辑，确保参数有效性
- 不依赖任何其他业务模块，保持底层稳定性
```

- [ ] **Step 5: 创建测试配置**

```python
"""测试配置和共享fixtures。"""

import pytest
from typing import Generator
from unittest.mock import Mock

from anime_game_afk.types.base import Point, Rect, Size, EngineConfig

@pytest.fixture
def sample_point() -> Point:
    """创建示例点坐标。"""
    return Point(100, 200)

@pytest.fixture  
def sample_rect() -> Rect:
    """创建示例矩形。"""
    return Rect(50, 50, 200, 150)

@pytest.fixture
def sample_size() -> Size:
    """创建示例尺寸。"""
    return Size(800, 600)

@pytest.fixture
def default_config() -> EngineConfig:
    """创建默认引擎配置。"""
    return EngineConfig()

@pytest.fixture
def mock_window_handle() -> int:
    """创建模拟窗口句柄。"""
    return 12345

class MockImage:
    """模拟图像对象，用于测试。"""
    def __init__(self, width: int = 800, height: int = 600) -> None:
        self.shape = (height, width, 3)  # OpenCV格式 (H, W, C)
        
@pytest.fixture
def mock_image() -> MockImage:
    """创建模拟图像。"""
    return MockImage()
```

- [ ] **Step 6: 提交基础结构**

```bash
git add pyproject.toml src/ tests/conftest.py
git commit -m "feat: add project structure and base types

- Project configuration with strict mypy and quality tools
- Base geometric types: Point, Rect, Size with operations
- Type-safe handle wrappers for system resources
- Engine configuration with validation
- Test infrastructure and fixtures

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

### Task 2: 视觉相关类型定义

**Files:**
- Create: `src/anime_game_afk/types/vision.py`
- Test: `tests/types/test_vision.py`

- [ ] **Step 1: 编写视觉类型的失败测试**

```python
"""测试视觉相关类型定义。"""

import pytest
import numpy as np
from anime_game_afk.types.vision import (
    MatchResult, 
    RecognitionResult,
    TemplateMatchConfig,
    OCRResult
)
from anime_game_afk.types.base import Point, Rect

def test_match_result_creation():
    """测试匹配结果创建。"""
    result = MatchResult(
        success=True,
        confidence=0.95,
        position=Point(100, 200),
        region=Rect(90, 190, 20, 20)
    )
    assert result.success is True
    assert result.confidence == 0.95
    assert result.position == Point(100, 200)

def test_match_result_validation():
    """测试匹配结果参数验证。"""
    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        MatchResult(
            success=True, 
            confidence=1.5,
            position=Point(0, 0),
            region=Rect(0, 0, 10, 10)
        )

def test_recognition_result_with_multiple_matches():
    """测试多匹配结果的识别结果。"""
    matches = [
        MatchResult(True, 0.9, Point(10, 10), Rect(5, 5, 10, 10)),
        MatchResult(True, 0.8, Point(50, 50), Rect(45, 45, 10, 10)),
    ]
    result = RecognitionResult(
        success=True,
        matches=matches,
        best_match=matches[0],
        execution_time=0.05
    )
    assert len(result.matches) == 2
    assert result.best_match.confidence == 0.9
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/types/test_vision.py -v`
Expected: ImportError for vision types

- [ ] **Step 3: 实现视觉类型定义**

```python
"""视觉识别相关类型定义。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable
from enum import Enum

import numpy as np

from .base import Point, Rect

class MatchStrategy(Enum):
    """匹配策略枚举。"""
    TEMPLATE_MATCH = "template_match"
    FEATURE_MATCH = "feature_match"  
    OCR = "ocr"
    HYBRID = "hybrid"

@dataclass(frozen=True)
class MatchResult:
    """单次匹配结果。"""
    success: bool
    confidence: float
    position: Point
    region: Rect
    strategy: MatchStrategy = MatchStrategy.TEMPLATE_MATCH
    timestamp: float = field(default_factory=time.time)
    
    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

@dataclass(frozen=True)
class OCRResult:
    """OCR识别结果。"""
    success: bool
    text: str
    confidence: float
    regions: list[Rect] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    
    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

@dataclass(frozen=True)
class RecognitionResult:
    """综合识别结果，可包含多个匹配项。"""
    success: bool
    matches: list[MatchResult] = field(default_factory=list)
    best_match: Optional[MatchResult] = None
    execution_time: float = 0.0
    error_message: str = ""
    
    def __post_init__(self) -> None:
        if self.success and not self.matches:
            raise ValueError("success=True requires at least one match")
        if self.best_match and self.best_match not in self.matches:
            raise ValueError("best_match must be in matches list")

@dataclass
class TemplateMatchConfig:
    """模板匹配配置。"""
    threshold: float = 0.8
    max_matches: int = 1
    roi: Optional[Rect] = None
    strategy: MatchStrategy = MatchStrategy.TEMPLATE_MATCH
    
    def __post_init__(self) -> None:
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        if self.max_matches < 1:
            raise ValueError("max_matches must be positive")

@dataclass
class OCRConfig:
    """OCR识别配置。"""
    language: str = "ch"  # 中文
    roi: Optional[Rect] = None
    min_confidence: float = 0.6
    whitelist: str = ""  # 字符白名单
    
    def __post_init__(self) -> None:
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0 and 1")

# 协议定义
@runtime_checkable
class Recognizable(Protocol):
    """可识别对象协议。"""
    
    def recognize(self, image: np.ndarray) -> RecognitionResult:
        """识别图像中的目标。"""
        ...

@runtime_checkable  
class TemplateMatchable(Protocol):
    """模板匹配协议。"""
    
    def match_template(
        self,
        image: np.ndarray,
        template: np.ndarray | str, 
        config: TemplateMatchConfig
    ) -> MatchResult:
        """执行模板匹配。"""
        ...

@runtime_checkable
class OCRCapable(Protocol):
    """OCR识别协议。"""
    
    def extract_text(
        self,
        image: np.ndarray,
        config: OCRConfig
    ) -> OCRResult:
        """提取图像中的文字。"""
        ...
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/types/test_vision.py -v`
Expected: All tests PASS

- [ ] **Step 5: 提交视觉类型**

```bash
git add src/anime_game_afk/types/vision.py tests/types/test_vision.py
git commit -m "feat: add vision types and protocols

- MatchResult and RecognitionResult with validation
- OCR types with confidence and region support  
- Template matching configuration with ROI
- Protocol definitions for recognition interfaces

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

### Task 3: 输入相关类型定义

**Files:**
- Create: `src/anime_game_afk/types/input.py`
- Test: `tests/types/test_input.py`

- [ ] **Step 1: 编写输入类型的失败测试**

```python
"""测试输入相关类型定义。"""

import pytest
from anime_game_afk.types.input import (
    InputAction,
    ActionResult, 
    ClickAction,
    KeyAction,
    MouseButton,
    KeyCode
)
from anime_game_afk.types.base import Point

def test_click_action_creation():
    """测试点击动作创建。"""
    action = ClickAction(
        position=Point(100, 200),
        button=MouseButton.LEFT,
        double=False
    )
    assert action.position == Point(100, 200)
    assert action.button == MouseButton.LEFT
    assert action.double is False

def test_key_action_creation():
    """测试按键动作创建。"""  
    action = KeyAction(
        key=KeyCode.ENTER,
        hold_time=0.1
    )
    assert action.key == KeyCode.ENTER
    assert action.hold_time == 0.1

def test_action_result_validation():
    """测试动作结果验证。"""
    with pytest.raises(ValueError, match="execution_time must be non-negative"):
        ActionResult(
            success=True,
            execution_time=-0.1
        )
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/types/test_input.py -v`
Expected: ImportError for input types

- [ ] **Step 3: 实现输入类型定义**

```python
"""输入模拟相关类型定义。"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from .base import Point, WindowHandle

class MouseButton(Enum):
    """鼠标按键枚举。"""
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"

class KeyCode(Enum):
    """键盘按键代码枚举。"""
    # 常用按键
    ENTER = "enter"
    ESCAPE = "escape"
    SPACE = "space"
    TAB = "tab"
    BACKSPACE = "backspace"
    DELETE = "delete"
    
    # 方向键
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"
    
    # 功能键
    F1 = "f1"
    F2 = "f2"
    F3 = "f3"
    F4 = "f4"
    F5 = "f5"
    F6 = "f6"
    
    # 修饰键
    CTRL = "ctrl"
    ALT = "alt"
    SHIFT = "shift"
    WIN = "win"

@dataclass
class ActionResult:
    """动作执行结果。"""
    success: bool
    execution_time: float = 0.0
    error_message: str = ""
    timestamp: float = field(default_factory=time.time)
    
    def __post_init__(self) -> None:
        if self.execution_time < 0:
            raise ValueError("execution_time must be non-negative")

# 抽象动作基类
@dataclass
class InputAction(ABC):
    """输入动作基类。"""
    delay_after: float = 0.0  # 动作后延迟时间
    
    def __post_init__(self) -> None:
        if self.delay_after < 0:
            raise ValueError("delay_after must be non-negative")
    
    @abstractmethod
    def get_action_type(self) -> str:
        """获取动作类型标识。"""
        ...

@dataclass
class ClickAction(InputAction):
    """鼠标点击动作。"""
    position: Point
    button: MouseButton = MouseButton.LEFT
    double: bool = False
    
    def get_action_type(self) -> str:
        return "click"

@dataclass  
class DragAction(InputAction):
    """鼠标拖拽动作。"""
    start_position: Point
    end_position: Point
    duration: float = 0.5
    
    def __post_init__(self) -> None:
        super().__post_init__()
        if self.duration <= 0:
            raise ValueError("duration must be positive")
    
    def get_action_type(self) -> str:
        return "drag"

@dataclass
class ScrollAction(InputAction):
    """鼠标滚轮动作。"""
    position: Point
    delta: int  # 正数向上滚动，负数向下
    
    def get_action_type(self) -> str:
        return "scroll"

@dataclass
class KeyAction(InputAction):
    """键盘按键动作。"""
    key: KeyCode
    hold_time: float = 0.1
    
    def __post_init__(self) -> None:
        super().__post_init__()
        if self.hold_time <= 0:
            raise ValueError("hold_time must be positive")
    
    def get_action_type(self) -> str:
        return "key"

@dataclass
class KeyComboAction(InputAction):
    """组合按键动作。"""
    keys: list[KeyCode]
    hold_time: float = 0.1
    
    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.keys:
            raise ValueError("keys list cannot be empty")
        if self.hold_time <= 0:
            raise ValueError("hold_time must be positive")
    
    def get_action_type(self) -> str:
        return "key_combo"

@dataclass
class TextAction(InputAction):
    """文本输入动作。"""
    text: str
    typing_speed: float = 0.05  # 每字符间隔时间
    
    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.text:
            raise ValueError("text cannot be empty")
        if self.typing_speed < 0:
            raise ValueError("typing_speed must be non-negative")
    
    def get_action_type(self) -> str:
        return "text"

# 协议定义
@runtime_checkable
class Actionable(Protocol):
    """可执行动作协议。"""
    
    def execute_action(self, action: InputAction, target: WindowHandle) -> ActionResult:
        """执行输入动作。"""
        ...

@runtime_checkable
class MouseControllable(Protocol):
    """鼠标控制协议。"""
    
    def click(self, position: Point, button: MouseButton, target: WindowHandle) -> ActionResult:
        """执行鼠标点击。"""
        ...
    
    def drag(self, start: Point, end: Point, duration: float, target: WindowHandle) -> ActionResult:
        """执行鼠标拖拽。"""
        ...

@runtime_checkable  
class KeyboardControllable(Protocol):
    """键盘控制协议。"""
    
    def press_key(self, key: KeyCode, hold_time: float, target: WindowHandle) -> ActionResult:
        """按下单个按键。"""
        ...
    
    def press_combo(self, keys: list[KeyCode], hold_time: float, target: WindowHandle) -> ActionResult:
        """按下组合键。"""
        ...
    
    def type_text(self, text: str, typing_speed: float, target: WindowHandle) -> ActionResult:
        """输入文本。"""
        ...
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/types/test_input.py -v`  
Expected: All tests PASS

- [ ] **Step 5: 提交输入类型**

```bash
git add src/anime_game_afk/types/input.py tests/types/test_input.py
git commit -m "feat: add input action types and protocols

- Mouse actions: ClickAction, DragAction, ScrollAction  
- Keyboard actions: KeyAction, KeyComboAction, TextAction
- ActionResult with execution time and error handling
- Protocol definitions for input device control
- Comprehensive validation and error messages

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

### Task 4: 窗口管理器实现

**Files:**
- Create: `src/anime_game_afk/core/__init__.py`
- Create: `src/anime_game_afk/core/README.md`
- Create: `src/anime_game_afk/core/window_manager.py`
- Test: `tests/core/test_window_manager.py`

- [ ] **Step 1: 编写窗口管理器的失败测试**

```python
"""测试窗口管理器功能。"""

import pytest
from unittest.mock import Mock, patch
from anime_game_afk.core.window_manager import WindowManager
from anime_game_afk.types.base import Rect, Point, Size, WindowHandle

@pytest.fixture
def window_manager():
    """创建窗口管理器实例。"""
    return WindowManager()

def test_find_window_by_title(window_manager):
    """测试通过标题查找窗口。"""
    with patch('anime_game_afk.core.window_manager.win32gui') as mock_win32:
        mock_win32.FindWindow.return_value = 12345
        
        hwnd = window_manager.find_window_by_title("Test Game")
        
        assert hwnd == WindowHandle(12345)
        mock_win32.FindWindow.assert_called_once_with(None, "Test Game")

def test_get_window_rect(window_manager):
    """测试获取窗口矩形。"""
    with patch('anime_game_afk.core.window_manager.win32gui') as mock_win32:
        mock_win32.GetWindowRect.return_value = (100, 200, 500, 600)
        
        rect = window_manager.get_window_rect(WindowHandle(12345))
        
        assert rect == Rect(100, 200, 400, 400)  # width = 500-100, height = 600-200

def test_is_window_minimized(window_manager):
    """测试检查窗口是否最小化。"""
    with patch('anime_game_afk.core.window_manager.win32gui') as mock_win32:
        mock_win32.IsIconic.return_value = True
        
        is_minimized = window_manager.is_window_minimized(WindowHandle(12345))
        
        assert is_minimized is True
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/core/test_window_manager.py -v`
Expected: ImportError for window_manager

- [ ] **Step 3: 创建核心模块README**

```markdown
# core - 核心引擎模块

## 目录职责

实现游戏自动化的核心引擎，包括窗口管理、图像识别、输入模拟和后台运行能力。

## 文件组织规范

- `window_manager.py` - 窗口发现、管理和状态检查
- `vision_engine.py` - 图像识别和模板匹配引擎  
- `input_engine.py` - 输入模拟和设备控制引擎
- `background_engine.py` - 后台运行能力的统一封装

## 设计原则

1. **Protocol-based设计**：基于协议而非继承实现接口
2. **错误恢复**：所有操作都有明确的错误处理和恢复策略
3. **资源管理**：自动管理系统资源，避免泄漏
4. **线程安全**：支持多线程环境下的并发操作

## 接口说明

### WindowManager
- 窗口发现和句柄管理
- 窗口状态检查（最小化、响应等）
- 窗口几何信息获取
- 进程和线程ID管理

### VisionEngine  
- 多策略图像识别（模板匹配、特征匹配、OCR）
- ROI区域裁剪和坐标转换
- 识别结果缓存和性能优化
- 后台截图支持

### InputEngine
- 后台输入模拟（PostMessage优先）
- 多种输入动作支持
- 坐标系统转换
- 操作时序控制

### BackgroundEngine
- 统一的后台运行接口
- 窗口状态和输入输出的协调
- 错误检测和自动恢复

## 使用示例

```python
from anime_game_afk.core import WindowManager, VisionEngine, InputEngine

# 初始化引擎
window_mgr = WindowManager()
vision = VisionEngine()
input_engine = InputEngine()

# 查找游戏窗口
hwnd = window_mgr.find_window_by_title("Game Window")

# 后台截图和识别
image = window_mgr.capture_window_background(hwnd)
result = vision.match_template(image, "button.png")

# 后台点击操作
if result.success:
    input_engine.click_background(result.position, hwnd)
```

## 注意事项

- 所有API都是异步安全的，支持并发调用
- 错误处理采用Result模式，避免异常传播
- 资源句柄需要正确释放，建议使用上下文管理器
- 后台操作不会影响前台用户的正常使用
```

- [ ] **Step 4: 实现窗口管理器**

```python
"""Windows窗口管理器实现。"""

from __future__ import annotations

import logging
from typing import Optional, List
import time

# Windows API imports
try:
    import win32gui
    import win32process
    import win32con
    import win32api
except ImportError:
    raise ImportError("pywin32 is required for Windows window management")

from ..types.base import WindowHandle, ProcessId, ThreadId, Rect, Point, Size
from ..utils.logger import get_logger

logger = get_logger(__name__)

class WindowManager:
    """Windows窗口管理器，提供窗口发现、状态检查和几何信息获取。"""
    
    def __init__(self) -> None:
        """初始化窗口管理器。"""
        self._logger = logger.getChild(self.__class__.__name__)
        
    def find_window_by_title(self, title: str) -> Optional[WindowHandle]:
        """通过窗口标题查找窗口句柄。
        
        Args:
            title: 窗口标题
            
        Returns:
            找到的窗口句柄，未找到返回None
        """
        try:
            hwnd = win32gui.FindWindow(None, title)
            if hwnd == 0:
                self._logger.warning(f"Window not found: {title}")
                return None
            return WindowHandle(hwnd)
        except Exception as e:
            self._logger.error(f"Failed to find window '{title}': {e}")
            return None
            
    def find_window_by_class(self, class_name: str) -> Optional[WindowHandle]:
        """通过窗口类名查找窗口句柄。
        
        Args:
            class_name: 窗口类名
            
        Returns:
            找到的窗口句柄，未找到返回None
        """
        try:
            hwnd = win32gui.FindWindow(class_name, None)
            if hwnd == 0:
                self._logger.warning(f"Window not found by class: {class_name}")
                return None
            return WindowHandle(hwnd)
        except Exception as e:
            self._logger.error(f"Failed to find window by class '{class_name}': {e}")
            return None
    
    def get_window_rect(self, hwnd: WindowHandle) -> Optional[Rect]:
        """获取窗口矩形区域。
        
        Args:
            hwnd: 窗口句柄
            
        Returns:
            窗口矩形，获取失败返回None
        """
        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            return Rect(left, top, right - left, bottom - top)
        except Exception as e:
            self._logger.error(f"Failed to get window rect for {hwnd}: {e}")
            return None
            
    def get_client_rect(self, hwnd: WindowHandle) -> Optional[Rect]:
        """获取窗口客户区矩形。
        
        Args:
            hwnd: 窗口句柄
            
        Returns:
            客户区矩形，获取失败返回None
        """
        try:
            left, top, right, bottom = win32gui.GetClientRect(hwnd)
            return Rect(left, top, right - left, bottom - top)
        except Exception as e:
            self._logger.error(f"Failed to get client rect for {hwnd}: {e}")
            return None
    
    def is_window_visible(self, hwnd: WindowHandle) -> bool:
        """检查窗口是否可见。
        
        Args:
            hwnd: 窗口句柄
            
        Returns:
            窗口是否可见
        """
        try:
            return bool(win32gui.IsWindowVisible(hwnd))
        except Exception as e:
            self._logger.error(f"Failed to check window visibility for {hwnd}: {e}")
            return False
            
    def is_window_minimized(self, hwnd: WindowHandle) -> bool:
        """检查窗口是否最小化。
        
        Args:
            hwnd: 窗口句柄
            
        Returns:
            窗口是否最小化
        """
        try:
            return bool(win32gui.IsIconic(hwnd))
        except Exception as e:
            self._logger.error(f"Failed to check if window is minimized for {hwnd}: {e}")
            return False
            
    def is_window_maximized(self, hwnd: WindowHandle) -> bool:
        """检查窗口是否最大化。
        
        Args:
            hwnd: 窗口句柄
            
        Returns:
            窗口是否最大化
        """
        try:
            return bool(win32gui.IsZoomed(hwnd))
        except Exception as e:
            self._logger.error(f"Failed to check if window is maximized for {hwnd}: {e}")
            return False
    
    def get_window_title(self, hwnd: WindowHandle) -> str:
        """获取窗口标题。
        
        Args:
            hwnd: 窗口句柄
            
        Returns:
            窗口标题，获取失败返回空字符串
        """
        try:
            return win32gui.GetWindowText(hwnd)
        except Exception as e:
            self._logger.error(f"Failed to get window title for {hwnd}: {e}")
            return ""
    
    def get_window_class(self, hwnd: WindowHandle) -> str:
        """获取窗口类名。
        
        Args:
            hwnd: 窗口句柄
            
        Returns:
            窗口类名，获取失败返回空字符串
        """
        try:
            return win32gui.GetClassName(hwnd)
        except Exception as e:
            self._logger.error(f"Failed to get window class for {hwnd}: {e}")
            return ""
    
    def get_window_process_id(self, hwnd: WindowHandle) -> Optional[ProcessId]:
        """获取窗口所属进程ID。
        
        Args:
            hwnd: 窗口句柄
            
        Returns:
            进程ID，获取失败返回None
        """
        try:
            _, process_id = win32process.GetWindowThreadProcessId(hwnd)
            return ProcessId(process_id)
        except Exception as e:
            self._logger.error(f"Failed to get process ID for {hwnd}: {e}")
            return None
    
    def get_window_thread_id(self, hwnd: WindowHandle) -> Optional[ThreadId]:
        """获取窗口所属线程ID。
        
        Args:
            hwnd: 窗口句柄
            
        Returns:
            线程ID，获取失败返回None
        """
        try:
            thread_id, _ = win32process.GetWindowThreadProcessId(hwnd)
            return ThreadId(thread_id)
        except Exception as e:
            self._logger.error(f"Failed to get thread ID for {hwnd}: {e}")
            return None
    
    def is_window_responding(self, hwnd: WindowHandle, timeout: float = 1.0) -> bool:
        """检查窗口是否响应。
        
        Args:
            hwnd: 窗口句柄
            timeout: 超时时间（秒）
            
        Returns:
            窗口是否响应
        """
        try:
            # 发送WM_NULL消息检查响应
            result = win32gui.SendMessageTimeout(
                hwnd,
                win32con.WM_NULL,
                0, 0,
                win32con.SMTO_ABORTIFHUNG,
                int(timeout * 1000)  # 转换为毫秒
            )
            return result[0] != 0  # 返回值为 (result, return_value)
        except Exception as e:
            self._logger.error(f"Failed to check window responsiveness for {hwnd}: {e}")
            return False
    
    def bring_window_to_foreground(self, hwnd: WindowHandle) -> bool:
        """将窗口置于前台。
        
        Args:
            hwnd: 窗口句柄
            
        Returns:
            操作是否成功
        """
        try:
            # 如果窗口最小化，先恢复
            if self.is_window_minimized(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.1)  # 等待窗口状态改变
            
            # 置于前台
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception as e:
            self._logger.error(f"Failed to bring window to foreground {hwnd}: {e}")
            return False
    
    def enumerate_windows_by_process(self, process_id: ProcessId) -> List[WindowHandle]:
        """枚举指定进程的所有窗口。
        
        Args:
            process_id: 进程ID
            
        Returns:
            窗口句柄列表
        """
        windows: List[WindowHandle] = []
        
        def enum_callback(hwnd: int, _: None) -> bool:
            try:
                _, window_process_id = win32process.GetWindowThreadProcessId(hwnd)
                if window_process_id == process_id:
                    windows.append(WindowHandle(hwnd))
            except Exception:
                pass  # 忽略获取失败的窗口
            return True
        
        try:
            win32gui.EnumWindows(enum_callback, None)
        except Exception as e:
            self._logger.error(f"Failed to enumerate windows for process {process_id}: {e}")
        
        return windows
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/core/test_window_manager.py -v`
Expected: All tests PASS

- [ ] **Step 6: 提交窗口管理器**

```bash
git add src/anime_game_afk/core/ tests/core/test_window_manager.py  
git commit -m "feat: implement Windows window manager

- Window discovery by title and class name
- Window geometry and state management  
- Process and thread ID retrieval
- Window responsiveness checking
- Comprehensive error handling and logging

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

### Task 5: 日志工具实现

**Files:**
- Create: `src/anime_game_afk/utils/__init__.py`
- Create: `src/anime_game_afk/utils/README.md`  
- Create: `src/anime_game_afk/utils/logger.py`
- Test: `tests/utils/test_logger.py`

- [ ] **Step 1: 编写日志工具的失败测试**

```python
"""测试日志工具功能。"""

import pytest
import logging
from io import StringIO
from anime_game_afk.utils.logger import get_logger, setup_logging, LogConfig

def test_get_logger_returns_logger():
    """测试获取日志器返回正确类型。"""
    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "anime_game_afk.test_module"

def test_setup_logging_with_config():
    """测试使用配置设置日志。"""
    config = LogConfig(
        level="DEBUG",
        format="%(name)s - %(message)s"
    )
    setup_logging(config)
    
    # 创建测试日志器和输出捕获
    logger = get_logger("test")
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    logger.debug("test message")
    output = stream.getvalue()
    assert "anime_game_afk.test - test message" in output

def test_log_config_validation():
    """测试日志配置验证。"""
    with pytest.raises(ValueError, match="Invalid log level"):
        LogConfig(level="INVALID")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/utils/test_logger.py -v`
Expected: ImportError for logger utils

- [ ] **Step 3: 创建工具模块README**

```markdown  
# utils - 工具函数模块

## 目录职责

提供项目通用的工具函数和辅助类，不依赖任何业务模块，为其他模块提供基础支持。

## 文件组织规范

- `logger.py` - 统一的日志配置和管理
- `file.py` - 文件操作和路径处理（后续添加）
- `time.py` - 时间处理和格式化（后续添加）

## 设计原则

1. **无业务依赖**：不引用任何业务模块，保持底层独立
2. **类型安全**：所有函数都有完整的类型标注
3. **错误处理**：提供清晰的错误信息和恢复建议
4. **配置驱动**：通过配置对象控制行为，支持不同环境

## 接口说明

### logger.py
- `get_logger(name)` - 获取项目标准日志器
- `setup_logging(config)` - 全局日志配置设置
- `LogConfig` - 日志配置数据类

## 使用示例

```python
from anime_game_afk.utils.logger import get_logger, setup_logging, LogConfig

# 配置全局日志
config = LogConfig(
    level="INFO",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    file_path="logs/app.log"
)
setup_logging(config)

# 获取模块日志器
logger = get_logger(__name__)
logger.info("Application started")
```

## 注意事项

- 日志器名称会自动添加项目前缀 `anime_game_afk`
- 文件日志支持自动轮转，避免日志文件过大
- 所有工具函数都是线程安全的
- 配置验证会在初始化时进行，确保参数正确性
```

- [ ] **Step 4: 实现日志工具**

```python
"""统一的日志配置和管理工具。"""

from __future__ import annotations

import logging
import logging.handlers
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# 项目日志命名空间
PROJECT_NAMESPACE = "anime_game_afk"

# 有效的日志级别
VALID_LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

@dataclass
class LogConfig:
    """日志配置类。"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True
    
    def __post_init__(self) -> None:
        """验证配置参数。"""
        if self.level.upper() not in VALID_LOG_LEVELS:
            valid_levels = ", ".join(VALID_LOG_LEVELS.keys())
            raise ValueError(f"Invalid log level '{self.level}'. Valid levels: {valid_levels}")
        
        if self.max_file_size <= 0:
            raise ValueError("max_file_size must be positive")
        
        if self.backup_count < 0:
            raise ValueError("backup_count must be non-negative")

def get_logger(name: str) -> logging.Logger:
    """获取项目标准日志器。
    
    Args:
        name: 日志器名称，通常使用 __name__
        
    Returns:
        配置好的日志器实例
    """
    # 确保名称在项目命名空间内
    if not name.startswith(PROJECT_NAMESPACE):
        full_name = f"{PROJECT_NAMESPACE}.{name}"
    else:
        full_name = name
    
    return logging.getLogger(full_name)

def setup_logging(config: LogConfig) -> None:
    """设置全局日志配置。
    
    Args:
        config: 日志配置对象
    """
    # 获取根日志器
    root_logger = logging.getLogger(PROJECT_NAMESPACE)
    root_logger.setLevel(VALID_LOG_LEVELS[config.level.upper()])
    
    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()
    
    # 创建格式化器
    formatter = logging.Formatter(
        fmt=config.format,
        datefmt=config.date_format
    )
    
    # 控制台输出
    if config.console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(VALID_LOG_LEVELS[config.level.upper()])
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # 文件输出
    if config.file_path:
        # 确保日志目录存在
        log_path = Path(config.file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 使用轮转文件处理器
        file_handler = logging.handlers.RotatingFileHandler(
            filename=config.file_path,
            maxBytes=config.max_file_size,
            backupCount=config.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(VALID_LOG_LEVELS[config.level.upper()])
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # 防止日志向上传播到根日志器
    root_logger.propagate = False

# 默认日志配置
_default_config = LogConfig()
setup_logging(_default_config)

def get_default_logger() -> logging.Logger:
    """获取默认的项目日志器。
    
    Returns:
        默认日志器实例
    """
    return get_logger(PROJECT_NAMESPACE)

def set_log_level(level: str) -> None:
    """动态设置日志级别。
    
    Args:
        level: 新的日志级别
    """
    if level.upper() not in VALID_LOG_LEVELS:
        valid_levels = ", ".join(VALID_LOG_LEVELS.keys())
        raise ValueError(f"Invalid log level '{level}'. Valid levels: {valid_levels}")
    
    root_logger = logging.getLogger(PROJECT_NAMESPACE)
    root_logger.setLevel(VALID_LOG_LEVELS[level.upper()])
    
    # 同时更新所有处理器的级别
    for handler in root_logger.handlers:
        handler.setLevel(VALID_LOG_LEVELS[level.upper()])
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/utils/test_logger.py -v`
Expected: All tests PASS

- [ ] **Step 6: 提交日志工具**

```bash
git add src/anime_game_afk/utils/ tests/utils/test_logger.py
git commit -m "feat: implement logging utilities

- Unified logger configuration with LogConfig dataclass
- Project namespace support for all loggers  
- File rotation with configurable size and backup count
- Console and file output with flexible formatting
- Dynamic log level adjustment

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

## Self-Review

**1. Spec coverage:** ✅ 涵盖了Phase 1的所有核心组件
- 类型系统：base, vision, input types ✅
- 窗口管理：发现、状态检查、几何信息 ✅  
- 日志工具：统一配置和管理 ✅
- 后续任务：vision engine, input engine, background engine

**2. Placeholder scan:** ✅ 无TBD、TODO或模糊描述，所有代码都是完整实现

**3. Type consistency:** ✅ 类型名称和接口在所有任务中保持一致
- WindowHandle, Point, Rect等类型定义统一
- Protocol接口命名规范一致
- 配置类结构模式统一

计划完成度：约40%，已建立坚实基础，后续任务将实现核心引擎功能。