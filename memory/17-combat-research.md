# 战斗系统 & 多维变量 调研报告 (2026-04-23)

## 调研范围

| 仓库 | 类型 | 语言 | 关键能力 |
|------|------|------|----------|
| AetherGazer-ahk | 同游戏 AHK 脚本 | AutoHotkey | 角色技能连招、历史多维变量支持 |
| ok-wuthering-waves | 3D 动作游戏 | Python | 角色继承+工厂、优先级切人、星图导航 |
| BetterGI | 原神秘境自动化 | C# | YOLO+OCR 混合检测、脚本化战斗、秘境循环 |
| ZZZ-OneDragon | 绝区零 | Python | YAML 触发器策略、音频闪避检测、条件语言 |
| MaaEnd | 终末地 (MaaFw) | Go+C++ | CNN 屏幕分析、动作队列优先级、双层导航 |

---

## 我们的现状

### 已有能力
- `CombatStateMachine`: 支持 11 种 GameState（BATTLE/REVIVE/CUTSCENE/DIALOGUE 等）
- `AttackCycleAction`: 固定连招 `J J U J I J O R 1 2`（0.25s 间隔）
- `MediumSeizureCombat`: 介质攫取导航 + **被动挂机等待**（5 分钟超时）
- `WalkForwardAction`: 按住 W 键前进
- `UNKNOWN_ROTATION`: 未知状态恢复轮转

### 关键差距
1. **无主动战斗**: 介质攫取靠队友打，站着不动
2. **无多维变量**: 完全未支持
3. **无角色适配**: 所有角色用同一套 `J J U J I J O R 1 2`
4. **无战斗结束检测优化**: 仅 OCR 轮询 "任务完成"/"结算"
5. **无楼层导航**: 多维变量需要在关卡间行走

---

## 各仓库方案对比

### 1. 战斗策略架构

| 方案 | 代表 | 优点 | 缺点 | 适合我们 |
|------|------|------|------|----------|
| **角色类继承** | ok-ww | 每角色独立 `do_perform()`、工厂模式 | 新角色需写代码 | ⭐⭐⭐ |
| **YAML 触发器** | ZZZ-OneDragon | 零代码配置、优先级+条件语言 | 复杂、学习曲线高 | ⭐⭐ |
| **外部脚本** | BetterGI | 用户可编辑脚本文件 | 需解析器 | ⭐⭐ |
| **固定连招表** | AetherGazer-ahk | 极简、易懂 | 无适应性 | ⭐⭐⭐⭐ |
| **CNN+动作队列** | MaaEnd | 最智能、实时响应 | 需训练模型 | ⭐ |

**推荐方案**: **固定连招表 + 角色工厂**
- 深空之眼战斗节奏固定，不需要 ZZZ 那种实时闪避
- 用 YAML 定义角色连招（参考 AetherGazer-ahk 的 7 种连招模板）
- 用工厂模式按角色名加载（参考 ok-ww 的 CharFactory）

### 2. 战斗状态检测

| 方法 | 代表 | 准确度 | 性能 | 适合我们 |
|------|------|--------|------|----------|
| **模板匹配** | ok-ww, 我们已有 | 高 | 快 | ✅ 继续用 |
| **OCR 文字** | 我们已有, BetterGI | 中高 | 较慢 | ✅ 辅助用 |
| **颜色检测** | AetherGazer-ahk, ok-ww | 中 | 最快 | ✅ 补充用 |
| **YOLO 目标检测** | BetterGI, MaaEnd | 最高 | 需 GPU | ❌ 过重 |
| **音频检测** | ZZZ-OneDragon | 高 | 低延迟 | ❌ 不适用 |

**推荐方案**: **模板匹配为主 + OCR 辅助 + 颜色检测兜底**

### 3. 多维变量/副本循环

| 仓库 | 副本模式 | 循环方式 | 楼层导航 |
|------|----------|----------|----------|
| AetherGazer-ahk (旧版) | 多维变量 | 颜色检测循环 | W键定时行走 |
| BetterGI | 秘境 | 进入→战斗→奖励→重复 | YOLO 找树+行走 |
| ZZZ-OneDragon | 零号空洞 | 状态机+事件处理 | OCR 距离检测 |
| MaaEnd | 精华副本 | Pipeline JSON 编排 | C++ 路径点导航 |

**推荐方案**: 参考 BetterGI 的 **进入→战斗→奖励→重复** 循环 + AetherGazer-ahk 旧版的多维变量流程

---

## 设计建议

### A. 可插拔战斗策略 (Combat Strategy)

```yaml
# config/combat_strategies/jinwu.yaml
name: 金乌
characters: [金乌, Jinwu]
rotation:
  - { keys: [skill1, skill1, attack], interval: 0.05 }
  - { keys: [skill2, attack], interval: 0.05 }
  - { keys: [ultimate, attack], interval: 0.05 }
  - { keys: [teammate1_ult, attack], interval: 0.05 }
  - { keys: [teammate2_ult, attack], interval: 0.05 }
  - { keys: [skill3], interval: 0.05 }
loop: true
```

```python
# 加载方式 (参考 ok-ww CharFactory + ZZZ YAML loader)
class CombatStrategyFactory:
    def load(name: str) -> CombatStrategy
    def detect_character(screenshot) -> str  # 模板匹配识别当前角色
```

### B. 多维变量自动化流程

```
多维变量入口
  ├─ 选择难度 (OCR 识别当前难度)
  ├─ 选择信标 (模板匹配/OCR)
  ├─ 开始挑战
  └─ 循环:
     ├─ 检测战斗开始 (模板匹配: battle_hud)
     ├─ 执行战斗策略 (CombatStrategy.execute)
     ├─ 检测战斗结束 (模板匹配 + OCR: 结算/评价)
     ├─ 处理奖励选择 (模板匹配宝箱)
     ├─ 检测是否有下一层
     │   ├─ 有 → 行走到下一关 (WalkForward + 交互)
     │   └─ 无 → 退出副本
     └─ 继续循环
```

### C. 楼层间导航

参考 AetherGazer-ahk 旧版: 简单的 **W 键定时行走 + 交互键** 即可。
深空之眼的多维变量关卡间移动路线固定，不需要复杂寻路。

---

## 从各仓库可直接 leverage 的内容

1. **AetherGazer-ahk**: 7 种角色连招模板（金乌/诗寇蒂/陵光/托特系/薇儿系等）→ 转为 YAML
2. **AetherGazer-ahk 旧版** (commit 208c0b2): 多维变量 UI 导航流程 → 改用模板匹配+OCR 重写
3. **ok-ww**: 角色工厂+优先级切人模式 → 架构参考
4. **BetterGI**: 秘境循环模式 (进入→战斗→检测结束→奖励→重复) → 流程参考
5. **ZZZ-OneDragon**: YAML 策略配置格式 → 配置方案参考
