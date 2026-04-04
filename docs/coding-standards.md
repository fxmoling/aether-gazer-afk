# Python 编码规范

本项目的编码规范。务实优先，不搞花架子。

## 1. 类型标注

**强制**: 所有公共函数、类属性必须有类型标注。用 `mypy --strict` 检查。

```python
# ✅ 
def match_template(
    image: np.ndarray,
    template: str,
    threshold: float = 0.8,
    roi: tuple[int, int, int, int] | None = None,
) -> MatchResult: ...

# ✅ 用标准库类型，不用 typing.List/Dict
def get_tasks(names: list[str]) -> dict[str, Task]: ...

# ❌ 
def match_template(image, template, threshold=0.8):
    ...
```

**要点**:
- Python 3.11+，用 `list[T]` 不用 `List[T]`，用 `X | None` 不用 `Optional[X]`
- 内部小函数、lambda 可以省略标注，mypy 能推断的不强求
- `TypeVar` 和 `Generic` 按需使用，不为泛型而泛型

## 2. 错误处理

**原则**: 用异常，不用 Result 模式。Python 社区惯例就是异常，不要对抗语言。

```python
# ✅ 自定义异常层次
class AutomationError(Exception):
    """所有自动化错误的基类"""

class RecognitionError(AutomationError):
    """图像识别失败"""

class WindowNotFoundError(AutomationError):
    """找不到游戏窗口"""

class PipelineError(AutomationError):
    """管线执行错误"""

# ✅ 捕获具体异常，包装后抛出
def find_game_window(title: str) -> int:
    try:
        hwnd = win32gui.FindWindow(None, title)
    except Exception as e:
        raise WindowNotFoundError(f"查找窗口失败: {title}") from e
    if hwnd == 0:
        raise WindowNotFoundError(f"窗口不存在: {title}")
    return hwnd

# ❌ 裸 except
try:
    do_something()
except:
    pass

# ❌ 吞掉异常信息
except Exception:
    raise RuntimeError("failed")  # 丢失了原始异常链
```

**要点**:
- 每个模块定义自己的异常类，继承 `AutomationError`
- 用 `raise ... from e` 保留异常链
- 只在最顶层（入口/调度器）做兜底 `except Exception`
- 不要用 `assert` 做业务校验，`assert` 只用于开发期不变量检查

## 3. 数据类

```python
from dataclasses import dataclass

# ✅ 配置类用 frozen，运行时数据不用
@dataclass(frozen=True)
class GameConfig:
    name: str
    window_title: str
    resolution: tuple[int, int] = (1280, 720)

# ✅ 运行时状态用普通 dataclass
@dataclass
class TaskState:
    current_step: str = ""
    retry_count: int = 0
    started_at: float = 0.0
```

**要点**:
- 配置/值对象用 `@dataclass(frozen=True)`
- 可变状态用普通 `@dataclass`
- 不需要 `slots=True` 除非有性能瓶颈的实测数据
- 简单数据传递用 `dataclass`，不用 `dict`，不用 `Pydantic`（除非需要复杂校验）

## 4. 接口与依赖注入

**Protocol 用于需要可替换的组件**，不是所有东西都要抽接口。

```python
from typing import Protocol

# ✅ MaaFramework 绑定层需要可替换（测试 mock、未来换引擎）
class ScreenCapture(Protocol):
    def capture(self, hwnd: int) -> np.ndarray: ...

class InputSender(Protocol):
    def click(self, hwnd: int, x: int, y: int) -> None: ...
    def key_press(self, hwnd: int, key: int) -> None: ...

# ✅ 构造函数注入，不需要框架
class TaskRunner:
    def __init__(self, capture: ScreenCapture, input: InputSender) -> None:
        self._capture = capture
        self._input = input

# ❌ 不需要 Protocol 的场景：内部工具函数、只有一个实现的类
```

**什么时候用 Protocol**:
- 核心引擎接口（截图、输入、识别）→ 用，因为要 mock 测试和未来替换
- 游戏适配器基类 → 用 `ABC`，因为是同一体系的继承
- 其他 → 不用，直接依赖具体类

## 5. 异步

**原则**: 不急着上 async。MaaFramework 本身是同步回调模型，Python 层按需异步。

```python
# ✅ IO 密集操作用 async
async def wait_for_window(title: str, timeout: float = 10.0) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        hwnd = find_game_window_optional(title)
        if hwnd:
            return hwnd
        await asyncio.sleep(0.5)
    raise WindowNotFoundError(f"等待窗口超时: {title}")

# ✅ CPU 密集操作保持同步，需要时用 run_in_executor
def match_template_sync(image: np.ndarray, template: np.ndarray) -> MatchResult:
    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    ...
```

**要点**:
- 任务调度、窗口轮询、多游戏编排 → async
- 图像处理、MaaFramework 调用 → sync（必要时 executor）
- 不要 async 传染：不是所有函数都要 async，只在需要并发的地方用

## 6. 代码组织

**文件大小**:
- 单个文件不超过 **300 行**（超了就拆）
- 单个函数不超过 **40 行**（过长说明该提取子函数）
- 单个类不超过 **150 行**（过大说明职责过多）

**模块依赖方向**（严格单向）:
```
ui → task → game → core → types
            ↓       ↓
          config → utils
```
- `types` 和 `utils` 不依赖任何业务模块
- `core` 不依赖 `game`、`task`、`ui`
- 违反方向 = 架构问题，必须重构

**导入规范**:
```python
# 标准库
import asyncio
from pathlib import Path

# 第三方
import numpy as np
import cv2

# 本项目
from anime_game_afk.core.capture import ScreenCapture
from anime_game_afk.types.base import MatchResult
```

## 7. 日志

用 `loguru`，直接用，不封装。

```python
from loguru import logger

# ✅
logger.info("开始识别: task={}", task_name)
logger.debug("匹配结果: confidence={:.2f}, pos=({}, {})", conf, x, y)
logger.error("管线执行失败: {}", e)

# ❌ 不要自己包装 logger
# ❌ 不要 JSON 结构化日志（不是微服务）
# ❌ 不要每个类都创建自己的 logger 实例
```

## 8. 测试

```python
import pytest
from unittest.mock import Mock

# ✅ 简单直接的单元测试
def test_find_window_returns_handle():
    with mock_win32_api(FindWindow=lambda _, t: 12345):
        hwnd = find_game_window("深空之眼")
        assert hwnd == 12345

def test_find_window_raises_on_not_found():
    with mock_win32_api(FindWindow=lambda _, t: 0):
        with pytest.raises(WindowNotFoundError):
            find_game_window("不存在的游戏")

# ✅ fixture 用于共享的测试资源
@pytest.fixture
def sample_screenshot() -> np.ndarray:
    return np.zeros((720, 1280, 3), dtype=np.uint8)
```

**要点**:
- 覆盖率目标: **核心模块 70%+**，整体不强求
- 优先测试：错误路径、边界条件、核心业务逻辑
- 不测试：简单的 getter/setter、纯委托调用、第三方库行为
- Mock：只 mock 外部依赖（Win32 API、MaaFramework），不 mock 内部类

## 9. 命名

```python
# 模块名: snake_case
window_manager.py
task_runner.py

# 类名: PascalCase
class GameAdapter: ...
class TaskRunner: ...

# 函数/变量: snake_case  
def find_game_window(title: str) -> int: ...
current_step = "login"

# 常量: UPPER_SNAKE_CASE
DEFAULT_THRESHOLD = 0.8
MAX_RETRY_COUNT = 3

# 私有: 单下划线前缀
def _parse_result(raw: dict) -> MatchResult: ...
self._connected = False
```

## 10. 不做的事

以下模式在本项目中**不使用**，不要引入：

- ❌ CQRS / Event Sourcing — 不是分布式系统
- ❌ 六边形架构术语（Port/Adapter） — Protocol + DI 够了
- ❌ 手写缓存/对象池 — 用标准库或第三方库
- ❌ 健康检查系统 — 不是微服务
- ❌ Result/Either 单子 — Python 用异常
- ❌ 过度抽象（接口只有一个实现）— YAGNI
- ❌ `Pydantic` 做内部数据类 — `dataclass` 够用
- ❌ `hypothesis` 属性测试 — 优先级极低
- ❌ 预提交钩子 — 开发初期不需要，CI 检查就够

## 工具配置

```toml
# pyproject.toml 相关配置

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
disallow_untyped_defs = true

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

**工具选择**:
- 格式化 + lint: `ruff`（替代 black + isort + flake8，更快更统一）
- 类型检查: `mypy --strict`
- 测试: `pytest` + `pytest-asyncio`
- 日志: `loguru`
