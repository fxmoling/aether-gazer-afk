# Op / Check / Task 三层重构设计

**日期**: 2026-04-07
**状态**: Approved
**范围**: games/aether_gazer/ 下的 ops/, checks/ (新), tasks/ 层

## 目标

将现有的混合式代码（task 直接调 device + 视觉函数）重构为严格的三层架构：

- **Op** — 改变世界（点击、按键、滑动、导航）
- **Check** — 观察世界（截图 + 识别，返回结构化结果）
- **Task** — 编排 Op + Check（业务流程，禁止直接碰 device）

## 五条硬规则

1. **Task 禁止 `ctx.device.*`** — 所有设备交互必须通过 Op
2. **Task 禁止直接调视觉函数** — 所有观察必须通过 Check
3. **原始 Op 不调其他 Op** — 复合 Op 只用原始 Op + Check
4. **Check 不改变状态** — 只截图 + 识别，不点击不按键
5. **Op 和 Check 都是 class 式** — `__init__` 传参，利于未来序列化

## 设计决策记录

| 问题 | 决策 | 理由 |
|------|------|------|
| Task 定义方式 | 代码式 (Python class)，但严格只用 Op + Check | 当前只 1 游戏 11 task，声明式 DSL 过度；代码式 + 硬规则足够，未来可序列化 |
| Check 定位 | 独立于 Op 的第三种类型 | Op 改变状态，Check 只观察，职责分离 |
| Op 粒度 | 两级：原始 Op + 复合 Op | 原始 Op 包装 device 调用；复合 Op 只组合原始 Op |
| Op API 形态 | class 式 (`XxxOp(params).run(ctx)`) | 利于自描述和未来序列化 |
| Check 返回值 | 结构化 `CheckResult(passed, data, message)` | data 携带坐标/文本/置信度，供后续 Op 使用 |

---

## Op 层

### 基础类型 (不变)

```python
@dataclass
class OpResult:
    success: bool
    data: Any = None
    error: str | None = None

class Op(Protocol):
    async def run(self, ctx: OpContext) -> OpResult: ...
```

### 原始 Op (新增 `ops/primitives.py`)

| Op | `__init__` 参数 | 包装 |
|----|-----------------|------|
| `ClickOp` | `x, y, wait=0.5` | `device.click()` |
| `PressKeyOp` | `key: int, wait=0.5` | `device.press_key()` |
| `HoldKeyOp` | `key: int, duration=1.0, wait=0.3` | `device.hold_key()` |
| `SwipeOp` | `x1, y1, x2, y2, duration=300, wait=0.5` | `device.swipe()` |
| `SleepOp` | `seconds: float` | `asyncio.sleep()` |
| `ScreenshotOp` | (无) | `device.screenshot()` → data=image |

每个原始 Op 附加：自动日志、wait 延时、异常捕获。

### 复合 Op (重构现有)

内部只用原始 Op + Check，不直接调 `ctx.device.*`：

| 复合 Op | 文件 | 变化 |
|---------|------|------|
| `ReturnToHubOp` | navigate/return_to_hub.py | 重构内部调用 |
| `GotoPageOp` | navigate/goto_page.py | 重构内部调用 |
| `GoBackOp` | navigate/go_back.py | 重构内部调用 |
| `WakeHubUiOp` | navigate/wake_hub_ui.py | 重构内部调用 |
| `AttackCycleOp` | combat/attack_cycle.py | 重构内部调用 |
| `WalkForwardOp` | combat/walk_forward.py | 重构内部调用 |
| `HandleReviveOp` | combat/handle_revive.py | 重构内部调用 |
| `ClickElementOp` | interact/click_element.py | 重构内部调用 |
| `ConfirmPopupOp` | interact/confirm_popup.py | 重构内部调用 |
| `SkipCutsceneOp` | interact/skip_cutscene.py | 重构内部调用 |
| `AdvanceDialogueOp` | interact/advance_dialogue.py | 重构内部调用 |
| `SmartReturnToHubOp` | navigate/smart_return.py | **新增** (从 helpers 提升) |
| `RapidClickOp` | interact/rapid_click.py | **新增** (从 helpers 提升) |

---

## Check 层 (新增)

### 基础类型 (`checks/base.py`)

```python
@dataclass
class CheckResult:
    passed: bool
    data: Any = None
    message: str = ""

class Check(Protocol):
    async def evaluate(self, ctx: OpContext) -> CheckResult: ...
```

### Check 清单

| Check | 参数 | 来源 | 返回 data |
|-------|------|------|-----------|
| `HasTextCheck` | `target, region?` | `ocr_find` | `TextResult` if found |
| `FindTextCheck` | `target, region?` | `ocr_find` | `TextResult` with x,y |
| `FindAllTextCheck` | `target, region?` | `ocr_find_all` | `list[TextResult]` |
| `OcrScanCheck` | `region?` | `ocr_full` | `OcrResult` |
| `OnPageCheck` | `page: str` | `is_on_page` | `{page, confidence}` |
| `IdentifyPageCheck` | (无) | `identify` | `{page, confidence}` |
| `DetectGameStateCheck` | (无) | `detect_state` | `{state, confidence}` |
| `AtHubCheck` | (无) | 模板+4关键词OCR | `{method}` |
| `ScreenUnchangedCheck` | `prev_image, threshold` | 像素差异 | `{diff}` |
| `HasColorCheck` | `hsv_low, hsv_high, region, min_ratio` | `color_ratio` | `{ratio}` |
| `TemplateMatchCheck` | `template, region?` | `match_template` | `MatchResult` |

### 文件结构

```
checks/
├── __init__.py
├── base.py       # CheckResult, Check protocol
├── ocr.py        # HasTextCheck, FindTextCheck, FindAllTextCheck, OcrScanCheck
├── page.py       # OnPageCheck, IdentifyPageCheck, AtHubCheck
├── state.py      # DetectGameStateCheck, ScreenUnchangedCheck
└── vision.py     # TemplateMatchCheck, HasColorCheck
```

---

## Task 层

### 硬规则执行

Task 内部只允许：
- `await XxxOp(...).run(ctx)` — 执行动作
- `await XxxCheck(...).evaluate(ctx)` — 执行观察
- Python 控制流 (if/else, for, while) — 业务逻辑
- 常量引用 (knowledge 层)

Task 内部禁止：
- `ctx.device.*` — 任何直接设备调用
- `from anime_game_afk.vision import ...` — 任何直接视觉函数调用

### helpers.py 处理

| 现有函数 | 迁移目标 |
|----------|----------|
| `is_at_hub()` | `AtHubCheck` |
| `is_at_hub_with_ocr()` | 删除 (由 `AtHubCheck` 替代) |
| `smart_return_to_hub()` | `SmartReturnToHubOp` |
| `rapid_click()` | `RapidClickOp` |

`helpers.py` 最终删除。

---

## 层级依赖规则

```
Layer 4:  knowledge/     ← 纯数据
Layer 5A: checks/        ← imports: knowledge, vision (L2)
Layer 5B: ops/           ← imports: knowledge, vision (L2), checks (L5A)
    原始 op              ← 只 imports: base (DevicePort)
    复合 op              ← imports: 原始 op, checks
Layer 6:  tasks/         ← imports: ops (L5B), checks (L5A)
                            禁止: ctx.device.*, vision.*
Layer 7:  processes/     ← imports: tasks (L6)
```

---

## 迁移策略

### Phase 1 — 基础设施 (不动现有代码)

1. 创建 `checks/base.py`
2. 创建 `ops/primitives.py`
3. 创建 `checks/ocr.py`, `checks/page.py`, `checks/state.py`, `checks/vision.py`

### Phase 2 — 复合 Op 重构 (逐个文件)

4. 重构每个复合 Op 使用原始 Op + Check
5. 将 `ops/perception/` 迁移到 `checks/`
6. 将 helpers 函数提升为 Op/Check

### Phase 3 — Task 重构 (逐个文件)

7. 重构每个 Task 只用 Op + Check
8. 删除 `helpers.py`
9. 删除 `ops/perception/`

每个 phase 结束时全量跑测试。

## 质量保障

架构验证测试 (`tests/test_architecture.py`):

```python
def test_tasks_do_not_call_device():
    """Tasks must not directly call ctx.device.*"""
    for task_file in glob("tasks/*.py"):
        if task_file.endswith("base.py"):
            continue
        source = Path(task_file).read_text()
        assert "ctx.device." not in source

def test_tasks_do_not_import_vision():
    """Tasks must not directly import vision functions"""
    for task_file in glob("tasks/*.py"):
        source = Path(task_file).read_text()
        assert "from anime_game_afk.vision" not in source
```

## 完整文件结构

```
games/aether_gazer/
├── knowledge/            # Layer 4 (不变)
├── checks/               # Layer 5A (新增)
│   ├── __init__.py
│   ├── base.py
│   ├── ocr.py
│   ├── page.py
│   ├── state.py
│   └── vision.py
├── ops/                  # Layer 5B (重构)
│   ├── base.py           # (不变)
│   ├── primitives.py     # (新增)
│   ├── navigate/
│   │   ├── return_to_hub.py
│   │   ├── smart_return.py  # (新增)
│   │   ├── goto_page.py
│   │   ├── go_back.py
│   │   └── wake_hub_ui.py
│   ├── interact/
│   │   ├── click_element.py
│   │   ├── confirm_popup.py
│   │   ├── skip_cutscene.py
│   │   ├── advance_dialogue.py
│   │   └── rapid_click.py   # (新增)
│   └── combat/
│       ├── attack_cycle.py
│       ├── handle_revive.py
│       └── walk_forward.py
├── tasks/                # Layer 6 (重构)
│   ├── base.py           # (不变)
│   ├── mail_tasks.py
│   ├── shop_tasks.py
│   ├── observation_tasks.py
│   ├── guild_tasks.py
│   ├── amusement_tasks.py
│   ├── activity_tasks.py
│   ├── startup_tasks.py
│   ├── combat_tasks.py
│   ├── navigation_tasks.py
│   ├── story_tasks.py
│   └── stamina_tasks.py
│   # helpers.py → 删除
├── processes/            # Layer 7 (不变)
```

删除:
- `ops/perception/` 整个目录 → 迁移到 checks/
- `tasks/helpers.py` → 功能分散到 ops + checks
