# 基于MaaFramework的游戏自动化基础架构设计

## 项目定位

**深度自动化游戏助手**，基于MaaFramework构建，实现完全后台无感运行的多游戏自动化平台。

## 技术架构

### 分层架构设计

```
┌─────────────────────────────────────────┐
│          Python 应用层                   │
│    (GUI, 任务编排, 游戏适配, 扩展功能)    │
│  技术栈: PySide6, asyncio, pydantic     │
├─────────────────────────────────────────┤
│        Python 业务逻辑层                 │
│  (定时任务, 多游戏编排, 系统服务集成)     │
│  技术栈: APScheduler, asyncio, typing   │
├─────────────────────────────────────────┤
│         MaaFramework 绑定层              │
│      (Python API封装, 数据转换)          │
│  技术栈: MaaFramework Python绑定        │
├─────────────────────────────────────────┤
│       MaaFramework 核心引擎              │
│  (图像识别, 输入模拟, 任务管线, 错误恢复) │
│  技术栈: C++20, OpenCV, OCR, Win32     │
├─────────────────────────────────────────┤
│          系统抽象层                      │
│   (Win32 API, 硬件驱动, 系统服务)       │
│  技术栈: Windows APIs, Virtual Display  │
└─────────────────────────────────────────┘
```

### 核心组件设计

#### 1. Python应用层 (anime_game_afk/)

**职责**: 用户界面、高级业务逻辑、扩展功能
```python
src/anime_game_afk/
├── ui/                        # 用户界面模块
│   ├── main_window.py        # 主窗口 (PySide6)
│   ├── task_editor.py        # 任务编辑器
│   ├── monitor_panel.py      # 实时监控面板
│   └── settings_dialog.py    # 设置对话框
├── scheduling/               # 定时任务模块
│   ├── scheduler.py         # APScheduler封装
│   ├── system_tasks.py      # Windows任务计划集成
│   ├── workflow.py          # 跨游戏工作流引擎
│   └── virtual_display.py   # 虚拟显示器管理
├── games/                   # 游戏适配模块
│   ├── adapter_base.py      # 游戏适配器基类
│   ├── detector.py          # 游戏检测和窗口管理
│   └── adapters/           # 具体游戏适配器
│       └── example_game/    # 示例游戏实现
└── config/                 # 配置管理模块
    ├── models.py           # Pydantic数据模型
    ├── loader.py           # 配置加载和验证
    └── defaults.py         # 默认配置
```

#### 2. MaaFramework集成层

**职责**: 封装MaaFramework API，提供Python友好接口
```python
src/anime_game_afk/maa/
├── __init__.py             # MaaFramework Python绑定导入
├── controller.py           # 输入控制器封装
├── recognizer.py           # 图像识别器封装
├── pipeline.py             # 任务管线执行器
├── resource.py             # 资源管理 (模板, JSON配置)
└── utils.py               # 工具函数和转换器
```

#### 3. 业务逻辑层组件

**3.1 后台运行增强引擎**
```python
class BackgroundEngine:
    """后台无感运行核心引擎"""
    
    def __init__(self, maa_controller: MaaController):
        self.controller = maa_controller
        self.window_manager = WindowManager()
        
    async def run_in_background(
        self, 
        window_handle: int,
        pipeline: str,
        params: dict
    ) -> TaskResult:
        """在后台执行任务管线，不影响用户操作"""
        # 1. 检查窗口状态
        # 2. 配置后台输入模式
        # 3. 执行MaaFramework管线
        # 4. 监控执行状态
        # 5. 错误恢复处理
```

**3.2 定时任务系统**
```python
class AdvancedScheduler:
    """高级定时任务调度器"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.task_registry: Dict[str, TaskDefinition] = {}
        
    async def schedule_workflow(
        self,
        workflow: WorkflowDefinition,
        schedule: str,  # Cron表达式
        enable_wakeup: bool = False
    ) -> str:
        """调度跨游戏工作流"""
        # 1. 解析工作流定义
        # 2. 注册到系统任务计划程序
        # 3. 配置虚拟显示器环境
        # 4. 设置系统唤醒(可选)
```

**3.3 多游戏编排引擎**
```python
class WorkflowOrchestrator:
    """跨游戏任务编排引擎"""
    
    async def execute_cross_game_workflow(
        self,
        workflow: WorkflowDefinition
    ) -> WorkflowResult:
        """执行跨游戏任务序列"""
        # 1. 游戏进程管理
        # 2. 资源隔离和状态管理
        # 3. 游戏间切换和启动
        # 4. 任务执行和错误处理
```

### 数据流设计

#### 主要数据流
```
用户配置 → 任务定义 → MaaFramework → 系统执行
    ↓           ↓            ↓           ↓
 配置验证   管线生成    图像识别    输入模拟
    ↓           ↓            ↓           ↓
 任务调度   资源加载    决策判断    状态反馈
```

#### 后台运行数据流
```
定时触发 → 虚拟显示器初始化 → 游戏窗口检测 → 后台截图
    ↓                ↓              ↓         ↓
系统服务模式 → 环境配置完成 → MaaFramework → 图像识别
    ↓                ↓              ↓         ↓
任务执行状态 ←  PostMessage后台输入 ← 动作决策 ← 识别结果
```

### 关键技术实现

#### 1. MaaFramework集成策略

**动态链接方式**：
```python
# 使用MaaFramework官方Python绑定
from maa.framework import Controller, Resource, Instance

class MaaIntegration:
    def __init__(self):
        # 初始化MaaFramework组件
        self.controller = Controller()
        self.resource = Resource()
        self.instance = Instance()
        
    def setup_for_background(self, window_handle: int):
        """配置MaaFramework用于后台运行"""
        # 设置窗口句柄
        self.controller.set_option(
            ControllerOption.DefaultAppPackageEntry, 
            window_handle
        )
        # 启用后台模式
        self.controller.set_option(
            ControllerOption.ScreenCapture, 
            ScreenCaptureMethod.DXGI_DesktopDuplication
        )
```

#### 2. 后台运行核心机制

**窗口状态管理**：
```python
class WindowStateManager:
    def ensure_background_ready(self, hwnd: int) -> bool:
        """确保窗口在后台运行状态"""
        # 1. 检查窗口是否响应
        # 2. 验证是否支持后台截图
        # 3. 测试PostMessage输入
        # 4. 配置坐标系统转换
```

**虚拟显示器支持**：
```python
class VirtualDisplayManager:
    def create_headless_environment(self) -> DisplayContext:
        """创建无头显示环境"""
        # 1. 安装/配置虚拟显示驱动
        # 2. 设置虚拟分辨率
        # 3. 配置游戏窗口到虚拟显示器
        # 4. 验证图像捕获能力
```

#### 3. 定时任务增强

**系统集成**：
```python
class SystemTaskIntegration:
    def register_windows_task(
        self, 
        name: str, 
        schedule: str, 
        command: str
    ) -> bool:
        """注册到Windows任务计划程序"""
        # 使用Windows Task Scheduler API
        # 支持系统唤醒和权限管理
```

### 项目结构规划

```
anime-game-afk/
├── pyproject.toml              # 项目配置和依赖
├── README.md                   # 项目说明
├── LICENSE                     # 协议声明
├── docs/                       # 项目文档
├── src/anime_game_afk/         # 主应用包
├── assets/                     # 游戏资源文件
│   ├── templates/             # 模板图片
│   ├── pipelines/             # MaaFramework JSON管线
│   └── configs/               # 游戏配置文件
├── tests/                      # 测试代码
├── scripts/                    # 辅助脚本
│   ├── setup_maa.py          # MaaFramework安装脚本
│   ├── build.py              # 构建脚本
│   └── deploy.py             # 部署脚本
└── .references/               # 参考项目 (已有)
```

### 开发路线图

#### Phase 1: MaaFramework集成基础 (4-6周)
1. **Week 1-2**: MaaFramework环境搭建和Python绑定
2. **Week 3-4**: 基础窗口管理和后台运行验证
3. **Week 5-6**: 第一个示例游戏的完整自动化流程

#### Phase 2: 后台运行增强 (3-4周)  
1. **Week 7-8**: 定时任务系统和系统服务集成
2. **Week 9-10**: 虚拟显示器支持和无头运行
3. **Week 11**: 稳定性测试和性能优化

#### Phase 3: 多游戏平台 (4-5周)
1. **Week 12-13**: 跨游戏工作流引擎
2. **Week 14-15**: 第二个游戏适配和验证
3. **Week 16**: 用户界面和配置系统

### 技术风险和缓解策略

#### 风险1: MaaFramework学习曲线
**缓解**: 
- 深入研究M9A项目的MaaFramework使用方式
- 从简单的模板匹配开始，逐步掌握高级功能
- 建立MaaFramework使用最佳实践文档

#### 风险2: 后台运行兼容性
**缓解**:
- 支持多种后台截图方案 (DXGI, GDI, BitBlt)
- 实现PostMessage输入的兼容性回退机制  
- 建立游戏兼容性测试矩阵

#### 风险3: 系统权限和安全
**缓解**:
- 实现权限检查和提升机制
- 提供用户友好的权限配置指导
- 支持非管理员权限下的有限功能模式

### 成功标准

#### 技术指标
- ✅ 游戏可在最小化状态下稳定运行
- ✅ 识别准确率 > 95%，操作成功率 > 98%  
- ✅ 支持连续72小时无人值守运行
- ✅ 用户操作电脑时零干扰

#### 业务指标  
- ✅ 单个游戏完整自动化覆盖率 > 80%
- ✅ 跨游戏任务编排成功执行
- ✅ 用户设置定时任务成功率 > 95%

这个基于MaaFramework的架构设计充分利用了成熟框架的优势，同时实现了我们的核心差异化能力。设计看起来如何？