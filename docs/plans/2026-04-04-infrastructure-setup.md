# 项目基础设施搭建实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建完整的项目文档体系和目录结构，建立文档先行的开发规范

**Architecture:** 扁平化docs目录 + 标准化README.md + 增强的CLAUDE.md规则

**Tech Stack:** Markdown文档 + Git版本控制

---

## 文件结构规划

**创建的文件：**
- `docs/requirements.md` - 功能需求和合规要求
- `docs/architecture.md` - 整体架构设计
- `docs/api.md` - 对外接口规范
- `docs/development.md` - 开发规范和工作流
- `docs/deployment.md` - 部署和配置指南
- `docs/compliance.md` - 详细的合规策略
- `README.md` - 项目总览
- `.claude/README.md` - Claude工作区说明
- `.references/README.md` - 参考项目使用指南

**修改的文件：**
- `CLAUDE.md` - 已完成文档规范整合

---

### Task 1: 创建核心需求文档

**Files:**
- Create: `docs/requirements.md`

- [ ] **Step 1: 基于现有memory创建需求文档**

```markdown
# 功能需求规范

## 项目目标

开发一款通用的多游戏自动化平台，支持：
- 日常任务自动完成
- 主线剧情推进辅助  
- 特定玩法自动化处理
- 多游戏适配支持

## 合规要求

### 核心约束
- **输入限制**: 仅允许图像识别（截图分析）作为信息输入源
- **输出限制**: 仅允许鼠标键盘模拟作为操作输出
- **网络限制**: 禁止任何网络抓包、协议分析、API调用
- **行为模拟**: 完全基于"看屏幕+点击操作"的人类行为模式

### 技术合规
- 使用公开的自动化库和框架
- 所有操作都可被游戏官方检测工具识别为正常操作
- 不修改游戏文件或内存
- 不使用任何游戏内部接口

## 功能需求

### 核心功能
1. **图像识别系统**
   - OpenCV模板匹配
   - OCR文字识别
   - 多分辨率适配
   - ROI区域裁剪

2. **输入模拟系统**
   - 鼠标点击、拖拽、滚轮
   - 键盘按键、组合键
   - 后台操作支持
   - 操作时序控制

3. **任务编排系统**
   - JSON声明式任务定义
   - Python脚本复杂逻辑
   - 状态机流程控制
   - 错误恢复机制

4. **多游戏适配**
   - 游戏配置文件系统
   - 模板资源管理
   - 分辨率自动适配
   - 游戏特定逻辑扩展

### 扩展功能
1. **用户界面**
   - 现代化GUI界面
   - 任务配置管理
   - 实时状态监控
   - 日志查看功能

2. **高级特性**
   - 计划任务调度
   - 多实例管理
   - 统计报告生成
   - 插件扩展支持

## 非功能需求

### 性能要求
- 图像识别响应时间 < 500ms
- 操作执行延迟 < 100ms
- 内存使用 < 1GB
- CPU使用率 < 30%

### 可用性要求
- 界面操作直观易懂
- 配置过程简单快捷
- 错误信息清晰明确
- 支持中英文界面

### 可靠性要求
- 连续运行稳定性 > 99%
- 异常自动恢复能力
- 完善的日志记录
- 配置备份恢复

## 目标用户

- 游戏玩家（主要）
- 自动化爱好者
- 开发者和研究人员
```

- [ ] **Step 2: 提交需求文档**

```bash
git add docs/requirements.md
git commit -m "docs: add functional requirements specification

- Core compliance constraints for game automation
- Technical requirements for image recognition and input simulation  
- Multi-game adaptation framework requirements
- Performance and reliability specifications

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

### Task 2: 创建架构设计文档

**Files:**
- Create: `docs/architecture.md`

- [ ] **Step 1: 基于技术调研创建架构文档**

```markdown
# 系统架构设计

## 整体架构

采用分层架构模式，确保各组件职责清晰，便于测试和维护。

```
┌─────────────────────────────────────────┐
│              用户界面层                    │
│        (PySide6 + Fluent UI)           │
├─────────────────────────────────────────┤
│              应用服务层                    │
│      (任务编排 + 配置管理 + 调度器)         │
├─────────────────────────────────────────┤
│              核心引擎层                    │
│    (图像识别 + 输入模拟 + 状态机)          │
├─────────────────────────────────────────┤
│              平台抽象层                    │
│     (截图接口 + 输入接口 + 文件系统)        │
└─────────────────────────────────────────┘
```

## 核心组件设计

### 1. 图像识别引擎 (VisionEngine)

**职责**: 处理所有图像分析任务
**技术栈**: OpenCV + PaddleOCR
**接口**:
```python
class VisionEngine:
    def match_template(self, image, template, threshold=0.8) -> MatchResult
    def extract_text(self, image, roi=None) -> TextResult  
    def find_multiple(self, image, templates) -> List[MatchResult]
    def wait_for_element(self, template, timeout=10) -> bool
```

**设计特点**:
- 多策略识别：模板匹配 → 特征匹配 → OCR 逐级回退
- ROI优化：限定识别区域提升速度
- 缓存机制：模板图片预加载和缓存
- 坐标归一化：基于1280x720基准自动缩放

### 2. 输入模拟引擎 (InputEngine)

**职责**: 处理所有鼠标键盘操作
**技术栈**: pywin32 + pydirectinput
**接口**:
```python
class InputEngine:
    def click(self, x, y, button='left', double=False) -> None
    def drag(self, start, end, duration=0.5) -> None
    def key_press(self, key, hold_time=0.1) -> None
    def key_combo(self, keys: List[str]) -> None
    def scroll(self, x, y, delta) -> None
```

**设计特点**:
- 后台优先：PostMessage不抢焦点
- 前台回退：pydirectinput兼容性保障
- 人类化模拟：随机延迟和贝塞尔曲线轨迹
- 坐标转换：相对坐标到绝对坐标自动转换

### 3. 任务编排引擎 (TaskEngine)

**职责**: 管理任务执行流程和状态
**架构模式**: 有限状态机 + 声明式JSON
**接口**:
```python
class TaskEngine:
    def load_pipeline(self, pipeline_file: str) -> Pipeline
    def execute_task(self, task_name: str) -> TaskResult
    def register_custom_action(self, name: str, handler: Callable)
    def get_task_state(self) -> TaskState
```

**JSON任务定义格式**:
```json
{
  "TaskName": {
    "algorithm": "TemplateMatch|OCR|CustomAction",
    "template": ["image1.png", "image2.png"],
    "roi": [x, y, width, height],
    "action": "Click|Key|Custom",
    "next": ["NextTask1", "NextTask2"],
    "on_error": ["ErrorHandler"],
    "retry": 3,
    "timeout": 10
  }
}
```

### 4. 游戏适配层 (GameAdapter)

**职责**: 处理不同游戏的特定逻辑
**设计模式**: 策略模式 + 工厂模式
**接口**:
```python
class GameAdapter:
    def detect_game(self) -> GameInfo
    def get_templates(self) -> TemplateSet
    def get_pipelines(self) -> PipelineSet  
    def create_custom_actions(self) -> Dict[str, Callable]
```

**多游戏支持策略**:
- 配置文件分层：base + game-specific
- 模板资源隔离：每个游戏独立模板库
- 分辨率适配：多套分辨率模板自动选择
- 自定义扩展：游戏特定识别和动作逻辑

## 数据流设计

### 主要数据流
1. **截图 → 识别 → 决策 → 执行 → 验证**
2. **用户配置 → 任务加载 → 状态机执行**
3. **错误检测 → 恢复策略 → 状态重置**

### 状态管理
- 全局状态：当前执行任务、游戏窗口、配置信息
- 任务状态：执行进度、重试次数、错误信息
- 界面状态：用户设置、显示状态、日志缓存

## 扩展性设计

### 插件架构
```python
class PluginInterface:
    def on_task_start(self, task: Task) -> None
    def on_task_complete(self, task: Task, result: TaskResult) -> None
    def on_recognition_result(self, result: RecognitionResult) -> None
```

### 配置扩展
- 游戏配置：新增游戏只需添加配置文件
- 模板扩展：支持用户自定义模板
- 动作扩展：支持Python脚本自定义动作
- 流程扩展：支持JSON任务流程定义

## 错误处理策略

### 分级错误处理
1. **识别失败**: 模板回退 → 特征匹配 → OCR → 用户介入
2. **操作失败**: 重试机制 → 替代方案 → 任务跳过
3. **系统异常**: 日志记录 → 状态恢复 → 安全退出

### 恢复机制
- 弹窗检测：并行检测常见弹窗并自动关闭
- 状态重置：检测到异常界面时回到安全状态
- 断线重连：网络或窗口异常时自动重连

## 性能优化

### 识别优化
- ROI裁剪：只在必要区域进行识别
- 模板预处理：启动时预加载所有模板
- 并发识别：多个识别任务并行处理
- 结果缓存：相似截图结果复用

### 内存优化
- 图片压缩：模板图片适当压缩存储
- 缓存管理：LRU算法管理识别结果缓存
- 垃圾回收：及时释放大对象内存
- 资源池：复用screenshot和recognition对象
```

- [ ] **Step 2: 提交架构文档**

```bash
git add docs/architecture.md  
git commit -m "docs: add system architecture design

- Layered architecture with clear component separation
- Core engines for vision, input, and task orchestration
- Multi-game adaptation strategy with plugin support
- Error handling and performance optimization plans

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

### Task 3: 创建API接口规范

**Files:**
- Create: `docs/api.md`

- [ ] **Step 1: 定义对外接口规范**

```markdown
# API接口规范

## 概述

本文档定义项目的对外接口，包括Python API、配置接口、插件接口等。

## 核心API

### VisionEngine API

```python
from anime_game_afk.vision import VisionEngine

class VisionEngine:
    """图像识别引擎"""
    
    def __init__(self, config: VisionConfig = None):
        """初始化识别引擎"""
        pass
    
    def match_template(self, 
                      image: np.ndarray, 
                      template: str | np.ndarray,
                      threshold: float = 0.8,
                      roi: Tuple[int, int, int, int] = None) -> MatchResult:
        """模板匹配
        
        Args:
            image: 输入图像
            template: 模板图片路径或数组
            threshold: 匹配阈值 0-1
            roi: 识别区域 (x, y, w, h)
            
        Returns:
            MatchResult: 匹配结果
        """
        pass
    
    def extract_text(self,
                    image: np.ndarray,
                    roi: Tuple[int, int, int, int] = None,
                    language: str = 'ch') -> TextResult:
        """OCR文字提取
        
        Args:
            image: 输入图像
            roi: 识别区域
            language: 语言代码
            
        Returns:
            TextResult: 文字识别结果
        """
        pass
```

### InputEngine API

```python
from anime_game_afk.input import InputEngine

class InputEngine:
    """输入模拟引擎"""
    
    def __init__(self, window_handle: int = None):
        """初始化输入引擎"""
        pass
    
    def click(self, 
             x: int, 
             y: int, 
             button: str = 'left',
             double: bool = False,
             delay: float = 0.1) -> None:
        """鼠标点击
        
        Args:
            x, y: 点击坐标
            button: 鼠标按键 'left'|'right'|'middle'
            double: 是否双击
            delay: 点击后延迟
        """
        pass
    
    def key_press(self,
                 key: str,
                 hold_time: float = 0.1,
                 delay: float = 0.1) -> None:
        """按键操作
        
        Args:
            key: 按键名称
            hold_time: 按住时间
            delay: 释放后延迟
        """
        pass
```

### TaskEngine API

```python
from anime_game_afk.task import TaskEngine

class TaskEngine:
    """任务编排引擎"""
    
    def __init__(self, 
                vision_engine: VisionEngine,
                input_engine: InputEngine):
        """初始化任务引擎"""
        pass
    
    def load_pipeline(self, pipeline_file: str) -> None:
        """加载任务管线
        
        Args:
            pipeline_file: 管线JSON文件路径
        """
        pass
    
    def execute_task(self, 
                    task_name: str,
                    timeout: int = 60) -> TaskResult:
        """执行任务
        
        Args:
            task_name: 任务名称
            timeout: 超时时间(秒)
            
        Returns:
            TaskResult: 执行结果
        """
        pass
```

## 配置接口

### 游戏配置格式

```json
{
  "game": {
    "name": "example_game",
    "version": "1.0.0", 
    "window_title": "Game Window",
    "base_resolution": [1280, 720]
  },
  "templates": {
    "base_path": "assets/templates/example_game/",
    "categories": {
      "ui": ["menu.png", "close.png"],
      "battle": ["attack.png", "skill.png"]
    }
  },
  "pipelines": {
    "daily_tasks": "pipelines/daily.json",
    "story_mode": "pipelines/story.json"
  }
}
```

### 任务管线格式

```json
{
  "StartTask": {
    "algorithm": "TemplateMatch",
    "template": ["start_button.png"],
    "threshold": 0.8,
    "roi": [100, 200, 300, 150],
    "action": "ClickSelf",
    "next": ["WaitLoading"],
    "timeout": 10,
    "retry": 3
  },
  "WaitLoading": {
    "algorithm": "TemplateMatch", 
    "template": ["loading_icon.png"],
    "action": "WaitDisappear",
    "next": ["MainMenu"],
    "timeout": 30
  }
}
```

## 插件接口

### 插件基类

```python
from anime_game_afk.plugin import PluginInterface

class PluginInterface:
    """插件接口基类"""
    
    def on_engine_init(self, engine: TaskEngine) -> None:
        """引擎初始化时调用"""
        pass
    
    def on_task_start(self, task_name: str) -> None:
        """任务开始时调用"""
        pass
    
    def on_task_complete(self, task_name: str, result: TaskResult) -> None:
        """任务完成时调用"""
        pass
    
    def on_recognition_result(self, result: MatchResult) -> None:
        """识别完成时调用"""
        pass
    
    def on_error(self, error: Exception, context: dict) -> bool:
        """错误发生时调用
        
        Returns:
            bool: True表示错误已处理，False继续传播错误
        """
        return False
```

### 自定义动作接口

```python
from anime_game_afk.task.actions import CustomAction

class CustomAction:
    """自定义动作基类"""
    
    def execute(self, 
               engine: TaskEngine,
               params: dict) -> ActionResult:
        """执行自定义动作
        
        Args:
            engine: 任务引擎实例
            params: 动作参数
            
        Returns:
            ActionResult: 执行结果
        """
        pass
```

## 数据结构

### MatchResult

```python
@dataclass
class MatchResult:
    """模板匹配结果"""
    success: bool           # 是否匹配成功
    confidence: float       # 匹配置信度 0-1
    position: Tuple[int, int]  # 匹配位置 (x, y)
    region: Tuple[int, int, int, int]  # 匹配区域 (x, y, w, h)
    template_name: str      # 模板名称
    timestamp: float        # 匹配时间戳
```

### TextResult

```python
@dataclass  
class TextResult:
    """文字识别结果"""
    success: bool           # 是否识别成功
    text: str              # 识别的文字
    confidence: float      # 识别置信度
    regions: List[Tuple[int, int, int, int]]  # 文字区域列表
    timestamp: float       # 识别时间戳
```

### TaskResult

```python
@dataclass
class TaskResult:
    """任务执行结果"""
    success: bool          # 是否执行成功
    task_name: str        # 任务名称
    duration: float       # 执行时长(秒)
    steps_completed: int  # 完成步骤数
    error_message: str    # 错误信息
    final_state: str      # 最终状态
```

## 使用示例

### 基础使用

```python
from anime_game_afk import VisionEngine, InputEngine, TaskEngine

# 初始化引擎
vision = VisionEngine()
input_engine = InputEngine()
task_engine = TaskEngine(vision, input_engine)

# 加载游戏配置
task_engine.load_game_config("configs/example_game.json")

# 执行任务
result = task_engine.execute_task("daily_login")
print(f"Task result: {result.success}")
```

### 插件开发

```python
class LoggingPlugin(PluginInterface):
    def on_task_start(self, task_name: str):
        print(f"Starting task: {task_name}")
    
    def on_task_complete(self, task_name: str, result: TaskResult):
        print(f"Task {task_name} completed: {result.success}")

# 注册插件
task_engine.register_plugin(LoggingPlugin())
```

## 命令行接口

```bash
# 运行特定任务
anime-game-afk run --game example_game --task daily_tasks

# 图形界面模式
anime-game-afk gui

# 配置游戏
anime-game-afk config --game example_game --setup

# 模板录制模式
anime-game-afk record --output templates/

# 调试模式
anime-game-afk debug --task daily_tasks --verbose
```
```

- [ ] **Step 2: 提交API文档**

```bash
git add docs/api.md
git commit -m "docs: add API specification

- Core engine APIs for vision, input, and task management
- Game configuration and pipeline JSON schemas
- Plugin interface for extensibility  
- Data structures and usage examples

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

### Task 4: 创建开发规范文档

**Files:**
- Create: `docs/development.md`

- [ ] **Step 1: 创建开发工作流规范**

```markdown
# 开发规范与工作流

## 开发方式

### 文档先行开发流程

本项目严格遵循**文档先行**的开发方式：

1. **准备阶段**
   - 查阅 `docs/` 目录下的所有相关文档
   - 检查 `.claude/memory/` 中的历史记录和技术决策
   - 了解 `.claude/plan/` 中的当前实施计划

2. **设计阶段**
   - 在相应文档中记录设计决策和变更计划
   - 更新架构文档反映设计变化
   - 在 memory 中记录重要技术选择的原因

3. **实现阶段**
   - 严格按照文档中的设计进行代码实现
   - 遵循既定的API接口和数据结构
   - 保持代码与文档的一致性

4. **验证阶段**
   - 实现完成后review所有相关文档
   - 确保文档内容与实际代码同步
   - 更新API文档反映接口变化

### 强制文档维护规则

- **代码变更前**: 必须先查阅和更新相关文档
- **实现完成后**: 必须review文档确保与代码同步
- **新增目录**: 必须同时创建标准 `README.md`
- **设计决策**: 必须记录到对应文档中
- **技术债务**: 必须在文档中标注和跟踪

## 代码规范

### Python代码风格

**基础规范**: 遵循 PEP 8
**工具配置**:
```ini
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 88

[tool.flake8]
max-line-length = 88
extend-ignore = E203, W503
```

**命名约定**:
- 类名: `PascalCase` (如 `VisionEngine`)
- 函数/方法: `snake_case` (如 `match_template`)
- 常量: `UPPER_SNAKE_CASE` (如 `DEFAULT_TIMEOUT`)
- 私有成员: 以 `_` 开头 (如 `_internal_method`)

### 目录结构规范

```
src/anime_game_afk/
├── __init__.py              # 包初始化
├── vision/                  # 图像识别模块
│   ├── __init__.py
│   ├── engine.py           # 主引擎
│   ├── matchers.py         # 匹配器实现
│   └── ocr.py             # OCR功能
├── input/                   # 输入模拟模块
│   ├── __init__.py
│   ├── engine.py          # 主引擎
│   ├── mouse.py           # 鼠标操作
│   └── keyboard.py        # 键盘操作
├── task/                    # 任务编排模块
│   ├── __init__.py
│   ├── engine.py          # 任务引擎
│   ├── pipeline.py        # 管线执行
│   └── actions.py         # 动作定义
├── game/                    # 游戏适配模块
│   ├── __init__.py
│   ├── adapter.py         # 适配器基类
│   └── configs/           # 游戏配置
└── utils/                   # 工具模块
    ├── __init__.py
    ├── config.py          # 配置管理
    └── logger.py          # 日志功能
```

### 测试规范

**测试覆盖率**: 最低 80%
**测试分类**:
- Unit Tests: `tests/unit/`
- Integration Tests: `tests/integration/`
- End-to-End Tests: `tests/e2e/`

**测试文件命名**: `test_<module_name>.py`
**测试方法命名**: `test_<function_name>_<scenario>`

```python
# 示例测试
def test_match_template_success_with_high_confidence():
    """测试模板匹配在高置信度下成功"""
    engine = VisionEngine()
    result = engine.match_template(test_image, test_template, 0.9)
    
    assert result.success is True
    assert result.confidence > 0.9
    assert result.position is not None
```

### 文档字符串规范

使用 Google 风格的 docstring:

```python
def match_template(self, 
                  image: np.ndarray, 
                  template: str,
                  threshold: float = 0.8) -> MatchResult:
    """在图像中匹配模板
    
    Args:
        image: 输入的截图图像数组
        template: 模板图片文件路径
        threshold: 匹配阈值，范围 0.0-1.0
        
    Returns:
        MatchResult: 包含匹配结果的数据类
        
    Raises:
        FileNotFoundError: 当模板文件不存在时
        ValueError: 当阈值不在有效范围内时
        
    Examples:
        >>> engine = VisionEngine()
        >>> result = engine.match_template(screenshot, "button.png", 0.8)
        >>> if result.success:
        ...     print(f"Found at {result.position}")
    """
```

## Git工作流

### 分支策略

- `main`: 主分支，始终保持可发布状态
- `develop`: 开发分支，集成所有功能开发
- `feature/<name>`: 功能分支，从 develop 创建
- `hotfix/<name>`: 紧急修复分支，从 main 创建

### 提交规范

遵循 Conventional Commits 规范:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Type 类型**:
- `feat`: 新功能
- `fix`: 错误修复  
- `docs`: 文档更改
- `style`: 代码格式化
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

**示例**:
```
feat(vision): add template caching mechanism

Implement LRU cache for template images to improve recognition performance.
Cache size configurable via VisionConfig.template_cache_size parameter.

Closes #123
```

### Pull Request流程

1. 从 `develop` 创建 feature 分支
2. 完成功能开发和测试
3. 更新相关文档
4. 创建 Pull Request 到 `develop`
5. 代码审查通过后合并
6. 删除 feature 分支

## 开发环境

### 必需工具

```bash
# Python 环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装开发依赖
pip install -e ".[dev]"

# 开发工具
pip install black isort flake8 mypy pytest pytest-cov
```

### 预提交钩子

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
```

### 开发脚本

```bash
# 运行所有测试
./scripts/test.sh

# 代码格式化
./scripts/format.sh

# 类型检查
./scripts/typecheck.sh

# 构建分发包
./scripts/build.sh
```

## 调试指南

### 日志配置

```python
# 使用统一的日志配置
import logging
from anime_game_afk.utils.logger import get_logger

logger = get_logger(__name__)

# 调试信息
logger.debug("Template matching started")
logger.info("Task completed successfully") 
logger.warning("Low confidence match")
logger.error("Recognition failed", exc_info=True)
```

### 调试工具

1. **截图调试**: 保存中间截图到 `debug/screenshots/`
2. **模板可视化**: 显示匹配区域和置信度
3. **性能分析**: 使用 `cProfile` 分析性能瓶颈
4. **内存监控**: 监控图像处理的内存使用

### 常见问题排查

1. **识别失败**: 检查模板图片质量、ROI设置、阈值参数
2. **操作无响应**: 验证窗口句柄、坐标转换、权限设置
3. **性能问题**: 优化ROI范围、启用模板缓存、减少截图频率

## 发布流程

### 版本号管理

使用语义化版本 (Semantic Versioning):
- `MAJOR.MINOR.PATCH`
- 示例: `1.0.0`, `1.1.0`, `1.1.1`

### 发布检查清单

- [ ] 所有测试通过
- [ ] 文档更新完成
- [ ] CHANGELOG.md 更新
- [ ] 版本号已更新
- [ ] 构建包测试通过
- [ ] 发布说明准备完毕

### 自动化发布

使用 GitHub Actions 进行自动化发布:
- 推送到 `main` 分支触发发布流程
- 自动运行测试套件
- 构建并发布到 PyPI
- 创建 GitHub Release
```

- [ ] **Step 2: 提交开发规范文档**

```bash
git add docs/development.md
git commit -m "docs: add development workflow and coding standards

- Documentation-first development process
- Python coding standards and project structure
- Git workflow with conventional commits  
- Testing requirements and debugging guidelines

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

### Task 5: 创建项目总览README

**Files:**
- Create: `README.md`

- [ ] **Step 1: 创建项目总览文档**

```markdown
# Anime Game AFK - 通用游戏自动化平台

一个专为二次元游戏（及其他游戏）设计的通用自动化脚本平台，通过图像识别和模拟操作实现游戏任务的自动化处理。

## ✨ 特性

- 🎮 **多游戏支持** - 通用的游戏适配框架，轻松适配新游戏
- 🔍 **智能识别** - OpenCV模板匹配 + OCR文字识别
- 🖱️ **人性化操作** - 模拟真实的鼠标键盘操作
- ⚖️ **严格合规** - 完全基于"看屏幕+点击"模式，符合游戏ToS
- 🎨 **现代界面** - PySide6 + Fluent Design 用户界面
- 🔧 **高度可扩展** - 插件系统和自定义脚本支持

## 📋 功能特性

### 核心功能
- ✅ 图像识别（模板匹配、OCR）
- ✅ 输入模拟（鼠标、键盘）
- ✅ 任务编排（状态机、JSON配置）
- ✅ 多分辨率适配
- ✅ 错误恢复机制

### 高级特性
- 🔄 计划任务调度
- 📊 执行统计报告
- 🔌 插件扩展系统
- 🎯 多实例管理
- 📝 详细日志记录

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Windows 10/11 (主要支持平台)
- 支持的游戏客户端

### 安装

```bash
# 克隆项目
git clone https://github.com/your-username/anime-game-afk.git
cd anime-game-afk

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows

# 安装依赖
pip install -e .
```

### 基础使用

```python
from anime_game_afk import VisionEngine, InputEngine, TaskEngine

# 初始化引擎
vision = VisionEngine()
input_engine = InputEngine()
task_engine = TaskEngine(vision, input_engine)

# 加载游戏配置
task_engine.load_game_config("configs/your_game.json")

# 执行任务
result = task_engine.execute_task("daily_login")
print(f"任务执行结果: {result.success}")
```

### 图形界面

```bash
# 启动GUI
anime-game-afk gui
```

## 🎮 支持的游戏

| 游戏名称 | 状态 | 支持功能 |
|---------|------|----------|
| 示例游戏 | 🚧 开发中 | 日常任务、主线推进 |

*更多游戏支持正在开发中...*

## 📚 文档

- [功能需求](docs/requirements.md) - 详细的功能需求和合规要求
- [系统架构](docs/architecture.md) - 系统设计和技术架构  
- [API文档](docs/api.md) - 完整的API接口说明
- [开发指南](docs/development.md) - 开发规范和工作流
- [部署指南](docs/deployment.md) - 部署和配置说明
- [合规策略](docs/compliance.md) - 详细的合规要求

## 🔧 项目结构

```
anime-game-afk/
├── src/                    # 源代码
│   └── anime_game_afk/    # 主包
├── tests/                  # 测试代码
├── assets/                 # 游戏资源文件
├── configs/               # 游戏配置文件
├── docs/                  # 项目文档
├── .references/           # 参考项目研究
└── .claude/              # 开发记录
```

## 🛠️ 开发

### 开发环境设置

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 安装预提交钩子
pre-commit install

# 运行测试
pytest

# 代码格式化
black src/ tests/
isort src/ tests/
```

### 文档先行开发

本项目采用**文档先行**的开发方式：

1. 📖 查阅现有文档 (`docs/`, `.claude/memory/`)
2. ✏️ 设计阶段记录到文档中
3. 💻 按文档实现代码
4. ✅ 实现后同步更新文档

### 贡献指南

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 遵循开发规范完成开发
4. 提交变更 (`git commit -m 'feat: add amazing feature'`)
5. 推送到分支 (`git push origin feature/amazing-feature`)
6. 开启 Pull Request

## ⚖️ 合规声明

本项目严格遵守游戏厂商的服务条款：

- ✅ **仅使用图像识别**作为信息输入
- ✅ **仅使用鼠标键盘模拟**作为操作输出  
- ❌ **不进行网络抓包**或协议分析
- ❌ **不修改游戏文件**或内存数据
- ✅ **完全模拟人类操作**行为模式

## 📄 许可证

本项目采用 [MIT许可证](LICENSE) 开源。

## 🤝 致谢

感谢以下开源项目的启发：

- [MaaAssistantArknights](https://github.com/MaaAssistantArknights/MaaAssistantArknights) - 优秀的自动化框架
- [M9A](https://github.com/MaaAssistantArknights/M9A) - 重返未来1999自动化
- [ok-wuthering-waves](https://github.com/ok-oldking/ok-wuthering-waves) - 鸣潮自动化
- [BetterGI Scripts](https://github.com/babalae/better-genshin-impact) - 原神自动化脚本

## 📞 支持

如果你遇到问题或有建议，欢迎：

- 🐛 [提交Issue](https://github.com/your-username/anime-game-afk/issues)
- 💬 [参与讨论](https://github.com/your-username/anime-game-afk/discussions)
- 📧 发送邮件至: support@anime-game-afk.com

---

⭐ 如果这个项目对你有帮助，请给我们一个星标！
```

- [ ] **Step 2: 提交项目总览文档**

```bash
git add README.md
git commit -m "docs: add project overview README

- Comprehensive project introduction with features
- Quick start guide and installation instructions
- Development workflow and contribution guidelines  
- Compliance statement and acknowledgments

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

### Task 6: 创建目录说明文档

**Files:**
- Create: `.claude/README.md`
- Create: `.references/README.md`

- [ ] **Step 1: 创建Claude工作区说明**

```markdown
# .claude - Claude工作区目录

## 目录职责

Claude Code 的工作空间，包含项目的开发记录、计划文档和配置信息。

## 文件组织规范

### memory/ 目录
- **用途**: 存储项目开发过程中的重要记录和技术决策
- **格式**: Markdown文件 (.md)
- **命名**: 数字前缀 + 描述性名称 (如 `01-project-overview.md`)
- **内容**: 项目进展、技术选择、问题解决方案等

**当前文件**:
- `01-project-overview.md` - 项目目标与合规要求
- `02-reference-projects.md` - 参考项目深度研究
- `03-tech-comparison.md` - 技术方案对比分析

### plans/ 目录  
- **用途**: 存储实施计划和任务分解
- **格式**: Markdown文件 (.md)
- **命名**: `YYYY-MM-DD-<feature-name>.md`
- **内容**: 详细的实施步骤、文件结构、代码示例等

## 使用示例

### 添加新的memory记录

```bash
# 创建新的memory文件
touch .claude/memory/04-new-feature-design.md

# 更新CLAUDE.md中的文件列表
vim CLAUDE.md
```

### 查看开发历史

```bash
# 查看所有memory文件
ls .claude/memory/

# 按时间顺序阅读
cat .claude/memory/*.md
```

## 注意事项

- **版本控制**: 此目录已在 `.gitignore` 中排除，不会提交到Git
- **隐私保护**: 可能包含敏感的开发信息和API密钥
- **定期整理**: 建议定期整理过时的记录，保持信息的时效性
- **备份重要**: 重要的设计决策应同时记录在 `docs/` 正式文档中

## 与其他目录的关系

- **docs/**: 正式文档，面向用户和开发者
- **.claude/memory/**: 开发过程记录，面向AI助手
- **.claude/plans/**: 实施计划，面向执行者

## 自动加载规则

根据 `CLAUDE.md` 的配置，Claude Code 启动时会自动加载：

1. `.claude/memory/` 下的所有 `.md` 文件
2. `.claude/plans/` 下的当前计划文件
3. 其他配置的文档路径

确保文件格式正确，以便AI正确解析和理解项目上下文。
```

- [ ] **Step 2: 创建参考项目使用指南**

```markdown
# .references - 参考项目目录

## 目录职责

存储用于研究和学习的开源项目，为本项目的技术选型和架构设计提供参考。

## 文件组织规范

### 项目克隆规则
- **克隆方式**: 使用 shallow clone 减少空间占用
- **命名约定**: 使用原项目名称，保持一致性
- **分支选择**: 通常克隆主分支或最新稳定版本

### 当前参考项目

#### 1. MaaAssistantArknights (MAA)
- **路径**: `.references/MaaAssistantArknights/`
- **语言**: C++20
- **特色**: 成熟的图像识别框架，多语言绑定
- **学习重点**: 
  - 多策略识别管线（模板匹配→特征匹配→OCR）
  - JSON声明式任务定义
  - 跨平台抽象设计
  - 插件系统架构

#### 2. M9A (重返未来1999)
- **路径**: `.references/M9A/`  
- **语言**: Python 3.11+
- **特色**: 基于MaaFramework的游戏自动化
- **学习重点**:
  - `[JumpBack]` 弹窗处理机制
  - 自定义识别和动作扩展
  - 活动时间驱动的任务调度
  - 多服务器资源分层管理

#### 3. ok-wuthering-waves (鸣潮)
- **路径**: `.references/ok-wuthering-waves/`
- **语言**: Python 3.12
- **特色**: 高度优化的实时战斗自动化
- **学习重点**:
  - YOLO目标检测的应用
  - 角色工厂和技能循环设计
  - 冻结时间的精确计算
  - PySide6现代UI设计

#### 4. BetterGI Scripts (原神)
- **路径**: `.references/bettergi-scripts-list/`
- **语言**: JavaScript + JSON + TXT
- **特色**: 分层脚本设计和社区生态
- **学习重点**:
  - 三种脚本格式的分层设计
  - 持久化状态管理
  - 社区脚本贡献模式
  - 引擎API设计

## 使用示例

### 克隆新的参考项目

```bash
# 进入references目录
cd .references/

# shallow clone 减少空间占用
git clone --depth 1 https://github.com/example/project.git

# 或指定标签/分支
git clone --depth 1 --branch v1.0.0 https://github.com/example/project.git
```

### 研究特定功能

```bash
# 查看MAA的任务定义
find .references/MaaAssistantArknights/ -name "*.json" -path "*/resource/tasks/*"

# 分析M9A的自定义动作
ls .references/M9A/agent/custom/action/

# 学习ok-ww的角色系统  
cat .references/ok-wuthering-waves/src/char/BaseChar.py
```

### 提取有用代码片段

```bash
# 创建代码片段收集文件
mkdir -p snippets/
echo "# 从MAA学到的识别策略" > snippets/maa-recognition.md
```

## 注意事项

- **版本控制**: 参考项目已在 `.gitignore` 中排除，不会提交到主项目
- **许可证遵守**: 学习借鉴时要遵守原项目的开源许可证
- **定期更新**: 重要项目建议定期更新到最新版本
- **空间管理**: 使用 shallow clone 控制磁盘占用

## 研究成果记录

重要的研究发现应记录在：

1. **即时记录**: `.claude/memory/02-reference-projects.md`
2. **技术对比**: `.claude/memory/03-tech-comparison.md`
3. **正式文档**: `docs/architecture.md` 相关章节

## 学习建议

### 分析顺序
1. **README和文档** - 了解项目目标和整体设计
2. **项目结构** - 学习目录组织和模块划分
3. **核心模块** - 深入关键功能的实现方式
4. **配置文件** - 理解可配置项和扩展机制
5. **测试代码** - 了解使用方式和边界条件

### 重点关注
- 错误处理和恢复机制
- 性能优化技巧
- 扩展性设计模式
- 用户体验设计
- 社区协作模式

通过系统性研究这些优秀项目，为我们的游戏自动化平台提供坚实的技术基础和设计灵感。
```

- [ ] **Step 3: 提交目录说明文档**

```bash
git add .claude/README.md .references/README.md
git commit -m "docs: add directory README files

- .claude/README.md explains Claude workspace organization
- .references/README.md details reference project usage
- Includes file organization rules and usage examples
- Documents relationship with other project directories

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```