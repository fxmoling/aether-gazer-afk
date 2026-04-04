# 混合渐进式游戏自动化平台 - 产品规格

## 产品定位

**深度自动化游戏助手**，采用混合渐进模式：先深度支持单个游戏建立技术基础，再逐步扩展为通用多游戏自动化平台。

## 核心差异化能力

### 1. 完全后台无感运行 🎯 **核心能力**

**技术要求**：
- 游戏窗口可在后台、最小化状态下正常运行
- 绝不出现可见的鼠标移动或抢夺焦点
- 用户可正常使用电脑进行其他工作

**技术实现策略**：
- **核心引擎**：基于MaaFramework，工业级图像识别和输入模拟
- **输入模拟**：MaaFramework PostMessage后台输入，支持最小化窗口
- **截图获取**：MaaFramework多策略截图（DXGI、BitBlt、GDI回退）
- **窗口管理**：通过窗口句柄操作，完全不影响用户操作
- **任务编排**：JSON声明式管线 + Python业务逻辑扩展

### 2. 智能定时任务系统 🕒 **重要能力**

**功能描述**：
- 支持Windows任务计划程序集成
- 可实现电脑自动开机 + 无头显示器模拟
- 定时执行复杂的游戏任务流程

**技术调研需求**：
- Windows Task Scheduler API集成
- 虚拟显示器驱动研究
- 系统服务模式运行
- 电源管理和唤醒机制

### 3. 跨游戏任务编排 🔄 **扩展能力**

**功能描述**：
- 用户可自定义跨游戏的任务执行序列
- 例如：游戏A (A1→A2→A3) → 游戏B (B1→B3) → 游戏C (C2)
- 支持条件分支、错误处理、资源管理

**设计要求**：
- 游戏间资源隔离和状态管理
- 统一的任务调度和监控界面
- 灵活的任务编排DSL或可视化编辑器

## 产品架构设计

### 分层架构

```
┌─────────────────────────────────────────┐
│         Python 应用层                    │
│  (GUI, 任务编排, 游戏适配, 扩展功能)      │
├─────────────────────────────────────────┤
│       Python 业务逻辑层                  │
│ (定时任务, 多游戏编排, 系统服务集成)      │
├─────────────────────────────────────────┤
│      MaaFramework 绑定层                 │
│    (Python API封装, 数据转换)            │
├─────────────────────────────────────────┤
│      MaaFramework 核心引擎               │
│ (图像识别, 输入模拟, 任务管线, 错误恢复)  │
├─────────────────────────────────────────┤
│         系统抽象层                        │
│  (Win32 API, 硬件驱动, 系统服务)         │
└─────────────────────────────────────────┘
```

### 核心组件设计

#### 1. MaaFramework 集成引擎

```python
from maa.framework import Controller, Resource, Instance

class MaaBackgroundEngine:
    def __init__(self):
        self.controller = Controller()
        self.resource = Resource() 
        self.instance = Instance()
    
    def setup_background_mode(self, hwnd: int) -> bool
    def execute_pipeline(self, pipeline: str, params: dict) -> TaskResult
    def capture_window_background(self, hwnd: int) -> np.ndarray
    def send_input_background(self, hwnd: int, action: dict) -> bool
```

**关键特性**：
- 基于MaaFramework工业级引擎
- 多策略图像识别（模板匹配+特征匹配+OCR）
- PostMessage后台输入，支持最小化窗口
- JSON声明式任务管线，错误恢复机制
- 完全不影响前台用户操作

#### 2. 定时任务管理器 (ScheduleManager)

```python
class ScheduleManager:
    def create_system_task(self, name, schedule, command) -> bool
    def setup_virtual_display(self) -> DisplayContext
    def execute_scheduled_workflow(self, workflow_id) -> TaskResult
    def manage_power_state(self, action) -> bool
```

**集成点**：
- Windows Task Scheduler
- 虚拟显示器驱动
- 系统服务注册
- 电源管理API

#### 3. 跨游戏编排器 (WorkflowOrchestrator)

```python
class WorkflowOrchestrator:
    def load_workflow(self, config) -> Workflow
    def execute_cross_game_sequence(self, sequence) -> WorkflowResult
    def manage_game_resources(self, games) -> ResourceContext
    def handle_game_transitions(self, from_game, to_game) -> bool
```

**工作流定义格式**：
```yaml
workflow:
  name: "multi_game_daily"
  schedule: "0 3 * * *"  # 每天凌晨3点
  steps:
    - game: "game_a"
      tasks: ["daily_login", "collect_rewards", "battle_auto"]
    - game: "game_b" 
      tasks: ["guild_donate", "arena_fight"]
      conditions:
        - game_a.status == "success"
```

## 渐进开发路线

### Phase 1: 后台运行基础 (优先级最高)

**目标**：建立完全后台运行的技术基础
**交付物**：
- 后台截图和输入模拟引擎
- 单个游戏的深度自动化验证
- 窗口状态管理和错误恢复

**成功标准**：
- 游戏可在最小化状态下稳定运行
- 用户可同时进行其他电脑操作
- 识别和操作准确率 > 95%

### Phase 2: 定时任务系统

**目标**：实现智能定时执行能力
**交付物**：
- Windows任务调度集成
- 虚拟显示器支持
- 系统服务模式运行

**技术调研重点**：
- Virtual Display Driver开发或集成
- 无人值守模式的稳定性保障
- 系统权限和安全策略

### Phase 3: 多游戏编排

**目标**：支持跨游戏任务序列执行
**交付物**：
- 跨游戏工作流引擎
- 可视化任务编排界面
- 多游戏资源管理

## 技术挑战与解决方案

### 挑战1: 后台截图的兼容性

**问题**：不同游戏的渲染方式可能影响后台截图效果
**解决方案**：
- 多种截图API的回退机制 (WGC → BitBlt → GDI)
- 游戏特定的截图策略配置
- 硬件加速渲染的特殊处理

### 挑战2: 定时任务的可靠性

**问题**：系统重启、驱动更新、权限变化等可能影响定时任务
**解决方案**：
- 自修复机制和健康检查
- 多重调度策略 (系统任务 + 内部守护进程)
- 详细的执行日志和异常报告

### 挑战3: 跨游戏状态管理

**问题**：不同游戏间的状态隔离和资源竞争
**解决方案**：
- 游戏进程管理和资源锁定
- 状态持久化和恢复机制
- 智能的游戏切换和启动策略

## 用户体验目标

1. **零干扰体验**：用户感知不到自动化程序的存在
2. **一键设置**：定时任务设置简单直观
3. **可视化监控**：实时查看执行状态和结果
4. **灵活配置**：支持个性化的任务组合和调度
5. **稳定可靠**：长期无人值守运行的稳定性

这个产品规格是否符合你的设想？特别是第1点的后台运行能力设计？

## 技术实现约束

### 代码质量标准

**Python类型系统**：
- 必须使用详尽的类型标注，当做强类型语言使用
- 所有函数参数、返回值、类属性都要有类型标注
- 使用 `mypy --strict` 进行类型检查
- 复杂类型使用 `typing` 和 `typing_extensions`

```python
from typing import Dict, List, Optional, Protocol, TypeVar, Generic
from dataclasses import dataclass

@dataclass
class MatchResult:
    success: bool
    confidence: float
    position: tuple[int, int]
    region: tuple[int, int, int, int]

class VisionEngine:
    def __init__(self, config: VisionConfig) -> None: ...
    
    def match_template(
        self, 
        image: np.ndarray, 
        template: str | np.ndarray,
        threshold: float = 0.8,
        roi: Optional[tuple[int, int, int, int]] = None
    ) -> MatchResult: ...
```

**模块化架构**：
- `src/` 目录下每个子目录代表一个独立模块
- 每个模块必须有 `README.md` 说明职责和接口
- 模块间依赖方向严格控制，避免循环依赖
- 每个文件专注单一职责，通常一个类一个文件

**代码规模控制**：
- 单个函数不超过30行（复杂业务逻辑除外）
- 单个类不超过200行，超过则拆分
- 单个文件不超过500行，优先拆分为多个文件
- 复杂逻辑通过组合模式而非继承实现

### 项目结构规范

```
src/anime_game_afk/
├── __init__.py                 # 包入口和版本信息
├── types/                      # 类型定义模块
│   ├── __init__.py
│   ├── README.md              # 类型系统说明
│   ├── base.py               # 基础数据类型
│   ├── vision.py             # 视觉相关类型
│   ├── input.py              # 输入相关类型
│   └── task.py               # 任务相关类型
├── core/                       # 核心引擎模块
│   ├── __init__.py
│   ├── README.md              # 核心功能说明
│   ├── vision_engine.py       # 图像识别引擎
│   ├── input_engine.py        # 输入模拟引擎
│   ├── background_engine.py   # 后台运行引擎
│   └── window_manager.py      # 窗口管理器
├── task/                       # 任务编排模块
│   ├── __init__.py
│   ├── README.md              # 任务系统说明
│   ├── scheduler.py           # 任务调度器
│   ├── pipeline.py            # 管线执行器
│   ├── workflow.py            # 工作流编排
│   └── actions/               # 动作定义子模块
│       ├── __init__.py
│       ├── base.py           # 基础动作类
│       ├── click.py          # 点击动作
│       └── wait.py           # 等待动作
├── game/                       # 游戏适配模块
│   ├── __init__.py
│   ├── README.md              # 游戏适配说明
│   ├── adapter_base.py        # 适配器基类
│   ├── detector.py            # 游戏检测器
│   └── adapters/              # 具体游戏适配器
│       ├── __init__.py
│       └── example_game/      # 示例游戏适配
│           ├── __init__.py
│           ├── adapter.py
│           └── config.py
├── system/                     # 系统集成模块
│   ├── __init__.py
│   ├── README.md              # 系统功能说明
│   ├── scheduler.py           # 系统任务调度
│   ├── service.py             # 系统服务管理
│   ├── display.py             # 虚拟显示器
│   └── power.py               # 电源管理
├── config/                     # 配置管理模块
│   ├── __init__.py
│   ├── README.md              # 配置系统说明
│   ├── loader.py              # 配置加载器
│   ├── validator.py           # 配置验证器
│   └── models.py              # 配置数据模型
├── utils/                      # 工具函数模块
│   ├── __init__.py
│   ├── README.md              # 工具函数说明
│   ├── logger.py              # 日志工具
│   ├── file.py                # 文件操作
│   └── time.py                # 时间处理
└── ui/                         # 用户界面模块（可选）
    ├── __init__.py
    ├── README.md              # 界面设计说明
    ├── main_window.py         # 主窗口
    ├── task_editor.py         # 任务编辑器
    └── monitor.py             # 监控面板
```

### 依赖关系约束

**严格的依赖方向**：
```
ui → task → game → core → types
     ↓       ↓       ↓
   system → config → utils
```

**禁止的依赖关系**：
- `core` 模块不得依赖 `game`、`task`、`system`、`ui`
- `types` 模块不得依赖任何其他业务模块
- `utils` 模块不得依赖任何业务模块
- 同层模块间应尽量避免直接依赖

### 接口设计原则

**协议优于继承**：
```python
from typing import Protocol

class Recognizable(Protocol):
    def recognize(self, image: np.ndarray) -> MatchResult: ...

class Actionable(Protocol):  
    def execute(self, params: dict[str, Any]) -> ActionResult: ...
```

**依赖注入**：
```python
class TaskEngine:
    def __init__(
        self,
        vision: Recognizable,
        input_device: Actionable,
        config: TaskConfig
    ) -> None:
        self._vision = vision
        self._input = input_device
        self._config = config
```

### 质量保障工具

**必需工具配置**：
```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

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
addopts = "--cov=src --cov-report=html --cov-report=term"
```

**预提交检查**：
- `mypy` 类型检查必须通过
- `black` + `isort` 代码格式化
- `flake8` 代码风格检查  
- `pytest` 单元测试覆盖率 > 80%

这些严格的代码质量标准将确保项目的长期可维护性和扩展性。