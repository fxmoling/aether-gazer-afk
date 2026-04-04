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
- 输入模拟：优先使用 `PostMessage/SendMessage` 直接向游戏窗口发送消息
- 截图获取：使用 `BitBlt` 或 `Windows Graphics Capture` 后台截图
- 窗口管理：通过窗口句柄操作，不改变窗口状态
- 坐标系统：基于游戏窗口的相对坐标系统

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
│         用户界面层                        │
│    (任务编排界面 + 监控面板)               │
├─────────────────────────────────────────┤
│         任务调度层                        │
│  (定时任务 + 跨游戏编排 + 资源管理)        │
├─────────────────────────────────────────┤
│         游戏适配层                        │
│   (游戏A引擎 + 游戏B引擎 + 通用适配器)    │
├─────────────────────────────────────────┤
│         核心引擎层                        │
│   (后台图像识别 + 后台输入模拟)           │
├─────────────────────────────────────────┤
│         系统抽象层                        │
│ (后台截图 + 窗口管理 + 系统服务)          │
└─────────────────────────────────────────┘
```

### 核心组件设计

#### 1. 后台运行引擎 (BackgroundEngine)

```python
class BackgroundEngine:
    def capture_window_background(self, hwnd) -> np.ndarray
    def send_input_background(self, hwnd, action) -> bool  
    def is_window_responsive(self, hwnd) -> bool
    def get_window_bounds(self, hwnd) -> Rect
```

**关键特性**：
- 使用窗口句柄而非屏幕坐标
- PostMessage优先，SendMessage回退
- 支持最小化窗口的内容捕获
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