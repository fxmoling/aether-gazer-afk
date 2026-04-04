# 架构设计

## 核心原则

1. MaaFw 是一个**库**，不是框架。我们是主进程，MaaFw 提供截图/输入/识别/管线能力
2. 不依赖 MaaPiCli、AgentServer 或 Maa 生态的任何其他组件
3. 战斗和导航是 Python 层的事，MaaFw 管不了实时控制循环

## 运行时架构

```
┌──────────────────────────────────────────────┐
│  我们的 Python 应用（主进程）                   │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ GUI      │  │ Scheduler│  │ Workflow   │  │
│  │ (PySide6)│  │ (定时)   │  │ (多游戏)  │  │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘  │
│       │              │              │        │
│  ┌────▼──────────────▼──────────────▼─────┐  │
│  │          GameSession                   │  │
│  │  (一个游戏实例的完整生命周期)            │  │
│  │                                        │  │
│  │  ┌─────────┐ ┌──────────┐ ┌─────────┐ │  │
│  │  │ Pipeline│ │ Combat   │ │ Navi-   │ │  │
│  │  │ Runner  │ │ Engine   │ │ gation  │ │  │
│  │  └────┬────┘ └────┬─────┘ └────┬────┘ │  │
│  └───────┼───────────┼────────────┼──────┘  │
│          │           │            │          │
│  ┌───────▼───────────▼────────────▼───────┐  │
│  │        MaaFw 封装层 (thin wrapper)     │  │
│  │  Controller · Resource · Tasker        │  │
│  └───────────────────┬───────────────────┘  │
└──────────────────────┼───────────────────────┘
                       │
           ┌───────────▼───────────┐
           │  MaaFw C++ DLL        │
           │  OpenCV · OCR · Win32 │
           └───────────────────────┘
```

## 核心概念

### GameSession

一个游戏从启动到退出的完整会话。持有 MaaFw 的三大对象：

```python
class GameSession:
    """一个游戏实例的运行会话"""

    def __init__(self, game_config: GameConfig) -> None:
        self._config = game_config
        self._controller: Win32Controller | None = None
        self._resource: Resource | None = None
        self._tasker: Tasker | None = None

    def connect(self) -> None:
        """连接游戏窗口，初始化 MaaFw"""
        hwnd = self._find_game_window()

        self._controller = Win32Controller(
            hWnd=hwnd,
            screencap_method=self._config.screencap_method,
            mouse_method=self._config.mouse_method,
            keyboard_method=self._config.keyboard_method,
        )
        self._controller.post_connection().wait()

        self._resource = Resource()
        self._resource.post_bundle(str(self._config.resource_path)).wait()

        self._tasker = Tasker()
        self._tasker.bind(self._resource, self._controller)

    def run_pipeline(self, entry: str, override: dict | None = None) -> bool:
        """执行 JSON 管线"""
        job = self._tasker.post_task(entry, override or {})
        job.wait()
        return job.status.succeeded()

    def screenshot(self) -> np.ndarray:
        """截图（供战斗引擎/导航引擎使用）"""
        return self._controller.post_screencap().wait().get()

    def click(self, x: int, y: int) -> None:
        """点击（供战斗引擎/导航引擎使用）"""
        self._controller.post_click(x, y).wait()

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 500) -> None:
        self._controller.post_swipe(x1, y1, x2, y2, duration).wait()

    def key_press(self, key: int) -> None:
        self._controller.post_key(key).wait()

    def disconnect(self) -> None:
        """清理资源"""
        self._tasker = None
        self._resource = None
        self._controller = None
```

**GameSession 是我们对 MaaFw 的唯一封装点。** 其他所有代码只跟 GameSession 交互，不直接接触 MaaFw API。如果未来换引擎，只改这一个类。

### GameAdapter

每个游戏的适配器，定义"这个游戏能做什么"：

```python
from abc import ABC, abstractmethod

class GameAdapter(ABC):
    """游戏适配器基类"""

    def __init__(self, session: GameSession) -> None:
        self._session = session

    @abstractmethod
    def game_name(self) -> str: ...

    @abstractmethod
    def window_title_pattern(self) -> str: ...

    @abstractmethod
    def resource_path(self) -> Path: ...

    @abstractmethod
    def available_tasks(self) -> list[str]: ...
```

深空之眼的适配器：

```python
class AetherGazerAdapter(GameAdapter):
    def game_name(self) -> str:
        return "深空之眼"

    def window_title_pattern(self) -> str:
        return "深空之眼"  # 或正则

    def resource_path(self) -> Path:
        return Path("assets/aether_gazer/resource")

    def available_tasks(self) -> list[str]:
        return ["daily_login", "collect_rewards", "story_push", "stamina_burn"]

    async def daily_login(self) -> None:
        """日常登录 + 签到"""
        self._session.run_pipeline("DailyLogin")

    async def stamina_burn(self, config: StaminaConfig) -> None:
        """消耗体力"""
        # Layer 1: JSON 管线 — 导航到关卡页面
        self._session.run_pipeline("NavigateToStage")
        # Layer 2: 条件逻辑 — 选择关卡
        level = await self._detect_next_level()
        self._session.run_pipeline("EnterLevel", {"EnterLevel": {"template": [f"level_{level}.png"]}})
        # Layer 3: Python 引擎 — 战斗
        await self._combat_engine.auto_battle(timeout=120)
        # Layer 1: JSON 管线 — 领取奖励
        self._session.run_pipeline("CollectRewards")
```

### CombatEngine

实时战斗控制，不走 MaaFw 管线，直接用 GameSession 的截图/点击/按键：

```python
class CombatEngine:
    """实时战斗引擎"""

    def __init__(self, session: GameSession) -> None:
        self._session = session

    async def auto_battle(self, timeout: float = 120) -> CombatResult:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            screen = self._session.screenshot()
            state = self._analyze_combat_state(screen)

            if state.battle_finished:
                return CombatResult(success=True)

            action = self._decide_action(state)
            self._execute_action(action)
            await asyncio.sleep(0.05)  # ~20fps 决策循环

        return CombatResult(success=False, reason="timeout")

    def _analyze_combat_state(self, screen: np.ndarray) -> CombatState:
        """分析战斗状态：血量、技能CD、敌人等"""
        ...

    def _decide_action(self, state: CombatState) -> CombatAction:
        """决策：攻击/闪避/技能/切人"""
        ...

    def _execute_action(self, action: CombatAction) -> None:
        """执行动作"""
        match action:
            case CombatAction.ATTACK:
                self._session.click(...)
            case CombatAction.DODGE:
                self._session.click(...)
            case CombatAction.SKILL:
                self._session.click(...)
            case CombatAction.SWITCH_CHAR:
                self._session.key_press(...)
```

### NavigationEngine

类似 CombatEngine，直接操控 GameSession：

```python
class NavigationEngine:
    """地图导航引擎"""

    def __init__(self, session: GameSession) -> None:
        self._session = session

    async def navigate_to(self, target: MapPoint) -> bool:
        while not self._reached(target):
            screen = self._session.screenshot()
            current = self._detect_position(screen)
            direction = self._calculate_direction(current, target)
            self._move(direction)
            await asyncio.sleep(0.1)
        return True
```

## 项目结构

```
src/anime_game_afk/
├── __init__.py
├── core/                      # 核心层 — 不依赖具体游戏
│   ├── session.py            # GameSession（MaaFw 封装）
│   ├── combat.py             # CombatEngine 基类
│   ├── navigation.py         # NavigationEngine 基类
│   └── adapter.py            # GameAdapter ABC
├── games/                     # 游戏适配层
│   └── aether_gazer/         # 深空之眼
│       ├── adapter.py        # AetherGazerAdapter
│       ├── combat.py         # 深空之眼战斗引擎
│       ├── navigation.py     # 深空之眼导航引擎
│       └── config.py         # 游戏配置
├── task/                      # 任务调度层
│   ├── scheduler.py          # 定时任务调度
│   └── workflow.py           # 跨游戏工作流
├── config/                    # 配置
│   └── models.py             # 配置数据类
├── ui/                        # GUI（Phase 2+）
│   └── ...
└── utils/
    └── logger.py

assets/
└── aether_gazer/
    └── resource/              # MaaFw 资源目录
        ├── pipeline/          # JSON 管线文件
        │   ├── startup.json
        │   ├── daily.json
        │   └── combat_nav.json
        └── image/             # 模板图片
            ├── login_btn.png
            └── ...

tests/
├── core/
│   ├── test_session.py
│   └── test_combat.py
└── games/
    └── aether_gazer/
        └── test_adapter.py
```

## 依赖方向

```
ui → task → games → core
              ↓       ↓
           config → utils
```

- `core/` 不知道任何具体游戏的存在
- `games/aether_gazer/` 依赖 `core/` 的 GameSession、CombatEngine、GameAdapter
- `task/` 依赖 `games/` 的适配器接口
- `ui/` 依赖 `task/`

## MaaFw 的使用边界

**用 MaaFw 的**:
- Win32 后台截图（FramePool / PrintWindow）
- Win32 后台输入（SendMessage / PostMessage）
- 模板匹配 + OCR（通过 JSON 管线的识别节点）
- JSON 管线执行（固定流程的菜单导航、领奖等）
- 窗口发现（Toolkit.find_desktop_windows）

**不用 MaaFw 的**:
- GUI — 我们自己用 PySide6
- 定时任务 — 我们自己集成 Windows Task Scheduler
- 战斗控制 — 太实时了，MaaFw 管线不适合，用 Python 直接调 screenshot/click
- 导航控制 — 同上
- 多游戏编排 — MaaFw 没有这个概念
- 配置管理 — 我们自己的格式

## 后台运行的关键配置

```python
# 截图：后台方案
# FramePool (Win10 1903+, 最快) | PrintWindow (兼容性好)
# 两个都设上，MaaFw 自动选最快的
screencap_method = MaaWin32ScreencapMethodEnum.Background  # = FramePool | PrintWindow

# 输入：后台方案（选一个）
# SendMessage — 后台，不移动鼠标，兼容性中等
# PostMessage — 后台，不移动鼠标，兼容性中等
# SendMessageWithCursorPos — 短暂移动鼠标再恢复，兼容性更好
mouse_method = MaaWin32InputMethodEnum.SendMessage
keyboard_method = MaaWin32InputMethodEnum.SendMessage
```

需要实测深空之眼支持哪种组合。不同游戏的渲染方式和消息处理不同，没有通用方案。

## 开发顺序

1. **安装 MaaFw，跑通最小 demo** — 连接深空之眼窗口，截图，点一下
2. **实测后台方案** — 哪种 screencap_method + input_method 组合在深空之眼上能用
3. **写第一个 JSON 管线** — 日常登录签到
4. **实现 GameSession + AetherGazerAdapter 骨架**
5. **战斗引擎原型** — 能自动打一关
6. **完善日常任务流程**
