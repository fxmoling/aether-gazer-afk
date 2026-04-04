# Python 企业级代码规范与最佳实践

## 概述

本文档汇集了Python开发中的行业优秀标准和最佳实践，作为项目开发的强制性技术规范。所有代码必须严格遵循这些标准。

## 代码质量标准

### 1. 类型系统 (Type System)

**参考标准**: PEP 484, 585, 586, 612, 613
**工具**: mypy, pyright, pyre

```python
# ✅ 正确：详尽的类型标注
from typing import Protocol, TypeVar, Generic, Optional, Union, Literal
from collections.abc import Sequence, Mapping

T = TypeVar('T')
P = TypeVar('P', bound='Processable')

class Repository(Generic[T]):
    def get_by_id(self, id: int) -> Optional[T]: ...
    def save(self, entity: T) -> T: ...

class Processable(Protocol):
    def process(self) -> bool: ...

# ❌ 错误：缺少类型标注
def process_data(data):
    return data.transform()
```

**强制要求**:
- 使用 `mypy --strict --disallow-any-generics` 检查
- 所有公共API必须有完整类型标注
- 使用 `typing_extensions` 获得最新类型特性
- 优先使用标准库类型（如 `list[T]` 而非 `List[T]`）

### 2. 错误处理 (Error Handling)

**参考标准**: PEP 654 (Exception Groups), Railway Pattern
**最佳实践**: Result类型、异常链、结构化错误

```python
# ✅ 正确：Result模式错误处理
from typing import Union, Generic, TypeVar
from dataclasses import dataclass
from enum import Enum

T = TypeVar('T')
E = TypeVar('E')

@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T

@dataclass(frozen=True) 
class Err(Generic[E]):
    error: E

Result = Union[Ok[T], Err[E]]

class VisionError(Enum):
    TEMPLATE_NOT_FOUND = "template_not_found"
    MATCHING_FAILED = "matching_failed"
    INVALID_IMAGE = "invalid_image"

def match_template(image: np.ndarray, template: str) -> Result[MatchResult, VisionError]:
    try:
        if not Path(template).exists():
            return Err(VisionError.TEMPLATE_NOT_FOUND)
        # ... matching logic
        return Ok(match_result)
    except Exception as e:
        logger.exception("Template matching failed")
        return Err(VisionError.MATCHING_FAILED)

# ❌ 错误：裸露的异常传播
def match_template(image, template):
    result = cv2.matchTemplate(image, template)  # 可能抛出任何异常
    return result
```

### 3. 数据类和不可变性 (Data Classes & Immutability)

**参考标准**: PEP 557 (Data Classes), PEP 622 (Structural Pattern Matching)

```python
# ✅ 正确：不可变数据类
from dataclasses import dataclass, field
from typing import FrozenSet

@dataclass(frozen=True, slots=True)
class GameConfig:
    name: str
    window_title: str
    resolution: tuple[int, int]
    templates: FrozenSet[str] = field(default_factory=frozenset)
    
    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Game name cannot be empty")
        if self.resolution[0] <= 0 or self.resolution[1] <= 0:
            raise ValueError("Resolution must be positive")

# ✅ 正确：使用模式匹配
def handle_result(result: Result[str, VisionError]) -> str:
    match result:
        case Ok(value):
            return f"Success: {value}"
        case Err(VisionError.TEMPLATE_NOT_FOUND):
            return "Template file not found"
        case Err(error):
            return f"Error: {error.value}"
```

### 4. 异步编程 (Async Programming)

**参考标准**: PEP 492, 525, 530
**最佳实践**: asyncio, 结构化并发

```python
# ✅ 正确：结构化异步代码
import asyncio
from typing import AsyncContextManager
from contextlib import asynccontextmanager

class AsyncVisionEngine:
    @asynccontextmanager
    async def capture_session(self, hwnd: WindowHandle) -> AsyncContextManager[CaptureSession]:
        session = await CaptureSession.create(hwnd)
        try:
            yield session
        finally:
            await session.cleanup()
    
    async def batch_recognize(self, tasks: list[RecognitionTask]) -> list[RecognitionResult]:
        async with asyncio.TaskGroup() as tg:  # PEP 654
            task_futures = [tg.create_task(self._recognize_single(task)) for task in tasks]
        
        return [future.result() for future in task_futures]
```

### 5. 依赖注入与接口设计 (DI & Interface Design)

**参考标准**: PEP 544 (Protocols), SOLID原则
**最佳实践**: Protocol-based design, Dependency Inversion

```python
# ✅ 正确：协议定义接口
from typing import Protocol, runtime_checkable

@runtime_checkable
class ImageRecognizer(Protocol):
    async def recognize(self, image: np.ndarray, config: RecognitionConfig) -> RecognitionResult: ...

@runtime_checkable  
class InputSimulator(Protocol):
    async def execute_action(self, action: InputAction, target: WindowHandle) -> ActionResult: ...

# ✅ 正确：依赖注入
@dataclass
class GameAutomationEngine:
    recognizer: ImageRecognizer
    input_sim: InputSimulator
    logger: logging.Logger
    
    @classmethod
    def create(
        cls,
        recognizer: ImageRecognizer,
        input_sim: InputSimulator,
        config: EngineConfig
    ) -> 'GameAutomationEngine':
        logger = get_logger(f"{cls.__name__}")
        return cls(recognizer, input_sim, logger)
```

## 架构模式最佳实践

### 1. 六边形架构 (Hexagonal Architecture)

```python
# 核心业务逻辑不依赖外部实现
class GameAutomationService:
    def __init__(
        self,
        vision_port: VisionPort,
        input_port: InputPort,
        storage_port: StoragePort
    ):
        self._vision = vision_port
        self._input = input_port
        self._storage = storage_port

# 适配器实现具体技术
class OpenCVVisionAdapter(VisionPort):
    def recognize(self, image: np.ndarray) -> RecognitionResult:
        # OpenCV specific implementation
        pass

class Win32InputAdapter(InputPort):
    def execute_action(self, action: InputAction) -> ActionResult:
        # Win32 specific implementation  
        pass
```

### 2. CQRS模式 (Command Query Responsibility Segregation)

```python
# 命令和查询分离
@dataclass(frozen=True)
class ExecuteTaskCommand:
    task_name: str
    target_window: WindowHandle
    parameters: dict[str, Any]

@dataclass(frozen=True)
class GetTaskStatusQuery:
    task_id: str

class TaskCommandHandler:
    async def handle(self, command: ExecuteTaskCommand) -> TaskExecutionResult: ...

class TaskQueryHandler:
    async def handle(self, query: GetTaskStatusQuery) -> TaskStatus: ...
```

### 3. Event Sourcing模式

```python
@dataclass(frozen=True)
class TaskStartedEvent:
    task_id: str
    task_name: str
    timestamp: datetime
    window_handle: WindowHandle

@dataclass(frozen=True)
class RecognitionCompletedEvent:
    task_id: str
    result: RecognitionResult
    timestamp: datetime

class EventStore:
    async def append_events(self, stream_id: str, events: list[Event]) -> None: ...
    async def get_events(self, stream_id: str) -> list[Event]: ...
```

## 性能优化最佳实践

### 1. 内存管理

```python
# ✅ 正确：使用slots节省内存
@dataclass
class Point:
    __slots__ = ('x', 'y')
    x: int
    y: int

# ✅ 正确：对象池模式
from queue import Queue
from contextlib import contextmanager

class ImagePool:
    def __init__(self, pool_size: int = 10):
        self._pool: Queue[np.ndarray] = Queue(maxsize=pool_size)
        self._create_initial_images(pool_size)
    
    @contextmanager
    def get_image(self, shape: tuple[int, int, int]) -> np.ndarray:
        try:
            image = self._pool.get_nowait()
        except:
            image = np.zeros(shape, dtype=np.uint8)
        
        try:
            yield image
        finally:
            if not self._pool.full():
                self._pool.put(image)
```

### 2. 并发控制

```python
# ✅ 正确：信号量控制并发
import asyncio
from typing import AsyncGenerator

class ConcurrentVisionEngine:
    def __init__(self, max_concurrent: int = 4):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
    async def recognize_batch(
        self, 
        tasks: list[RecognitionTask]
    ) -> AsyncGenerator[RecognitionResult, None]:
        async def process_task(task: RecognitionTask) -> RecognitionResult:
            async with self._semaphore:
                return await self._process_single(task)
        
        tasks_futures = [asyncio.create_task(process_task(task)) for task in tasks]
        
        for future in asyncio.as_completed(tasks_futures):
            result = await future
            yield result
```

### 3. 缓存策略

```python
# ✅ 正确：LRU缓存和过期策略  
from functools import lru_cache
from threading import RLock
import time

class TimedLRUCache(Generic[K, V]):
    def __init__(self, maxsize: int = 128, ttl: float = 300.0):
        self._cache: dict[K, tuple[V, float]] = {}
        self._maxsize = maxsize
        self._ttl = ttl
        self._lock = RLock()
        
    def get(self, key: K) -> Optional[V]:
        with self._lock:
            if key not in self._cache:
                return None
                
            value, timestamp = self._cache[key]
            if time.time() - timestamp > self._ttl:
                del self._cache[key]
                return None
                
            return value
    
    def put(self, key: K, value: V) -> None:
        with self._lock:
            # LRU eviction logic
            if len(self._cache) >= self._maxsize:
                oldest_key = min(self._cache.keys(), 
                               key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
                
            self._cache[key] = (value, time.time())
```

## 测试最佳实践

### 1. 测试金字塔

```python
# 单元测试 - 快速、隔离
class TestVisionEngine:
    @pytest.fixture
    def mock_image(self) -> np.ndarray:
        return np.zeros((600, 800, 3), dtype=np.uint8)
    
    def test_template_matching_success(self, vision_engine, mock_image):
        # Given
        template = np.ones((50, 50, 3), dtype=np.uint8)
        config = TemplateMatchConfig(threshold=0.8)
        
        # When  
        result = vision_engine.match_template(mock_image, template, config)
        
        # Then
        assert result.success is True
        assert result.confidence >= config.threshold

# 集成测试 - 验证组件交互
class TestGameAutomationIntegration:
    async def test_full_recognition_pipeline(self, automation_engine):
        # Given: 真实游戏窗口
        hwnd = await automation_engine.find_game_window("Test Game")
        task = RecognitionTask(template="login_button.png")
        
        # When: 执行完整识别流程
        result = await automation_engine.execute_recognition(hwnd, task)
        
        # Then: 验证端到端结果
        assert result.success
        assert result.execution_time < 1.0
```

### 2. 属性测试 (Property Testing)

```python
from hypothesis import given, strategies as st

class TestGeometryTypes:
    @given(
        x=st.integers(min_value=0, max_value=1920),
        y=st.integers(min_value=0, max_value=1080),
        w=st.integers(min_value=1, max_value=1920),
        h=st.integers(min_value=1, max_value=1080)
    )
    def test_rect_center_property(self, x: int, y: int, w: int, h: int):
        """矩形的中心点应该在矩形内。"""
        rect = Rect(x, y, w, h)
        center = rect.center
        assert rect.contains(center)
```

### 3. 快照测试 (Snapshot Testing)

```python
def test_recognition_result_serialization(snapshot):
    """确保识别结果序列化格式稳定。"""
    result = RecognitionResult(
        success=True,
        matches=[MatchResult(True, 0.95, Point(100, 200), Rect(90, 190, 20, 20))],
        execution_time=0.05
    )
    
    serialized = result.to_dict()
    snapshot.assert_match(serialized, "recognition_result.json")
```

## 安全性最佳实践

### 1. 输入验证

```python
from typing import NewType
import re

# 类型安全的ID
WindowHandle = NewType('WindowHandle', int)
TaskId = NewType('TaskId', str)

def validate_task_id(task_id: str) -> TaskId:
    """验证任务ID格式。"""
    if not re.match(r'^[a-zA-Z0-9_-]+$', task_id):
        raise ValueError(f"Invalid task ID format: {task_id}")
    if len(task_id) > 64:
        raise ValueError(f"Task ID too long: {len(task_id)}")
    return TaskId(task_id)

# 路径遍历防护
def safe_template_path(template_name: str, base_dir: Path) -> Path:
    """安全的模板路径构造。"""
    # 防止路径遍历攻击
    safe_name = Path(template_name).name
    if '..' in safe_name or '/' in template_name or '\\' in template_name:
        raise ValueError(f"Invalid template name: {template_name}")
    
    full_path = base_dir / safe_name
    return full_path.resolve()
```

### 2. 权限控制

```python
import ctypes
from ctypes import wintypes

def check_admin_privileges() -> bool:
    """检查是否具有管理员权限。"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def require_privileges(required: bool = True):
    """装饰器：要求特定权限。"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if required and not check_admin_privileges():
                raise PermissionError("This operation requires administrator privileges")
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

## 监控和可观测性

### 1. 结构化日志

```python
import json
from typing import Any
from datetime import datetime

class StructuredLogger:
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    
    def info(self, message: str, **context: Any) -> None:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': 'INFO',
            'message': message,
            'context': context
        }
        self._logger.info(json.dumps(log_data))
    
    def error(self, message: str, error: Exception, **context: Any) -> None:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': 'ERROR', 
            'message': message,
            'error': {
                'type': type(error).__name__,
                'message': str(error),
                'traceback': traceback.format_exc()
            },
            'context': context
        }
        self._logger.error(json.dumps(log_data))
```

### 2. 指标收集

```python
from dataclasses import dataclass, field
from typing import Counter
import time

@dataclass
class PerformanceMetrics:
    operation_counts: Counter[str] = field(default_factory=Counter)
    execution_times: list[tuple[str, float]] = field(default_factory=list)
    error_counts: Counter[str] = field(default_factory=Counter)
    
    def record_operation(self, name: str, duration: float) -> None:
        self.operation_counts[name] += 1
        self.execution_times.append((name, duration))
        
    def record_error(self, error_type: str) -> None:
        self.error_counts[error_type] += 1
        
    def get_average_time(self, operation: str) -> float:
        times = [t for op, t in self.execution_times if op == operation]
        return sum(times) / len(times) if times else 0.0

def measure_performance(operation_name: str):
    """装饰器：测量函数执行时间。"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                metrics.record_operation(operation_name, duration)
                return result
            except Exception as e:
                metrics.record_error(type(e).__name__)
                raise
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                metrics.record_operation(operation_name, duration)
                return result
            except Exception as e:
                metrics.record_error(type(e).__name__)
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
```

## 部署和CI/CD最佳实践

### 1. 配置管理

```python
from pathlib import Path
import os
from typing import Optional

@dataclass(frozen=True)
class AppConfig:
    # 从环境变量读取配置
    debug: bool = field(default_factory=lambda: os.getenv('DEBUG', 'false').lower() == 'true')
    log_level: str = field(default_factory=lambda: os.getenv('LOG_LEVEL', 'INFO'))
    max_workers: int = field(default_factory=lambda: int(os.getenv('MAX_WORKERS', '4')))
    
    # 敏感配置从文件或密钥管理系统读取
    @classmethod
    def from_file(cls, config_path: Path) -> 'AppConfig':
        if not config_path.exists():
            return cls()  # 使用默认值
        
        with open(config_path) as f:
            config_data = json.load(f)
        
        return cls(**config_data)
```

### 2. 健康检查

```python
from enum import Enum
from typing import Dict, List

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    UNHEALTHY = "unhealthy"

@dataclass
class HealthCheck:
    name: str
    status: HealthStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

class HealthChecker:
    def __init__(self):
        self._checks: List[Callable[[], HealthCheck]] = []
    
    def register_check(self, check_func: Callable[[], HealthCheck]) -> None:
        self._checks.append(check_func)
    
    async def run_all_checks(self) -> Dict[str, HealthCheck]:
        results = {}
        for check_func in self._checks:
            try:
                result = await check_func()
                results[result.name] = result
            except Exception as e:
                results[check_func.__name__] = HealthCheck(
                    name=check_func.__name__,
                    status=HealthStatus.UNHEALTHY,
                    message=str(e)
                )
        return results
```

这些标准和最佳实践确保代码质量、性能、安全性和可维护性达到企业级水准。