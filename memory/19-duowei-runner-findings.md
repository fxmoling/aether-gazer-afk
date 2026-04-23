# 多维变量自动化 — 发现与结论 (2026-04-23)

## 一、核心成果

实现了完整的多维变量 Process + Task，E2E 验证通过，可无限循环获取积分。

- **DuoweiProcess** (`processes/duowei_process.py`) — 无限循环 Process
- **DuoweiCombat** (`tasks/duowei_tasks.py`) — 单次挑战 Task
- **duowei_runner.py** (`scripts/`) — 命令行测试工具 (`--loop` / `--resume`)

---

## 二、策略：最小循环

只通关 1-2 层即退出，获取最低限度积分（~10万+/次）。

```
导航到多维变量页 → 开始挑战 → Setup(赏金猎人信标) → Loading
→ 1-1 珍宝选择(确认) → swipe旋转 + W前进 + J交互(进入传送门) → Loading
→ 1-2 战斗(攻击循环) → 奖励处理(中央+确认) → ESC+H+Enter退出结算
→ 回到多维变量页 → 重复
```

---

## 三、关键参数（已验证）

| 参数 | 值 | 说明 |
|------|------|------|
| 传送门旋转 | swipe dx=0.02×1280/actual_w | 分辨率自适应，保持25.6px拖拽距离 |
| 奖励确认 | (0.608, 0.847) | 单卡按钮92%位置，与多卡确认overlap |
| 屏幕中央 | (0.50, 0.40) | 选卡/关闭弹窗 |
| 结算退出 | (0.901, 0.931) | 积分页"退出"按钮固定位置 |
| 攻击循环 | J J U J I J O R 1 2 | 0.12s间隔，5循环≈10s |

---

## 四、导航流程

1. OCR检测"记忆珍宝图鉴" → 已在多维变量详情页 → 直接点开始挑战
2. 否则: ReturnToHub → 按J进入战斗页 → 点击挑战tab(0.83,0.9)
3. 挑战列表: OCR找"多维变量"(取y最大的匹配=卡片图标)
4. 找不到则点击左侧(0.05,0.5)滚动列表，最多3次
5. 进入详情页后: OCR点击"开始挑战"/"继续挑战"

---

## 五、Setup Wizard

- 难度页: OCR点击"下一步"
- 角色页: OCR点击"下一步"  
- 信标页: swipe下滑2次 → OCR找"赏金猎人"并点击 → OCR点击"开始挑战"

---

## 六、MaaFramework 输入特性

- `hold_key` = PostMessage快速按放循环(100ms间隔)，非真正KeyHold
- `swipe()` = post_swipe，用于相机旋转（距离可控、速度无关）
- `press_key` = 单次PostMessage按放
- 所有操作均为后台操作，游戏窗口无需前台

---

## 七、错误恢复

- 单次失败: 尝试ESC+H退出 → 继续下一轮
- 连续3次失败: 停止Process并报告
- 未知状态: ESC spam作为最后手段

---

## 八、战斗按键配置

战斗按键可在 设置 → 战斗按键 中自定义，存储在 `user_config.json` 的 `combat_keybinds` 字段。

| 功能 | 默认键 | 配置key |
|------|--------|---------|
| 攻击 | J | attack |
| 技能1 | U | skill1 |
| 技能2 | I | skill2 |
| 技能3 | O | skill3 |
| 大招 | R | ultimate |
| 闪避 | Space | dodge |

- `DuoweiCombat.__init__()` 从 UserConfig 读取，通过 `letter_to_vk()` 转换
- 攻击循环: attack×2 → skill1 → attack → skill2 → attack → skill3 → ultimate → QTE1 → QTE2
- QTE (1, 2) 不可配置，保持默认

---

## 九、UI 须知提示

任务页顶部琥珀色提示栏（可收起，状态存localStorage）：
- 游戏分辨率须为 16:9
- 操控模式选择键盘
- 如修改战斗快捷键需在设置中同步配置
