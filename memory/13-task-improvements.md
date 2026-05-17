# 任务改进 (2026-04-18)

## 概述

5 个每日任务根据实际运行反馈进行了改进，提升了可靠性和完整性。

## 改进列表

### 1. MimiStationCollect — 移除 x8 回退

**变更**: 只搜索 x10（周常奖励），不再搜索 x8。
**原因**: x10 是每周一次性奖励，数字越大效果越好，最高为 10。如果 x10 不可用，跳过即可。

- 文件: `observation_tasks.py`
- 移除: x8/X8 OCR 搜索回退
- 保留: x10/X10 两种大小写

### 2. GuildSupplyClaim — 完整重写

**变更**: 从 OCR 驱动改为固定坐标驱动，新增公会任务领取。
**原因**: OCR 找 领取 按钮太慢，且公会任务领取之前被遗漏。

新流程:
1. 点击公会按钮 (0.641, 0.944)
2. OCR 验证 矩阵补给 文字存在（确认用户在公会中）
3. 点击矩阵补给 tab (0.926, 0.958) ← guild 底部栏
4. 点击领取 (0.5, 0.71) ← 固定坐标，截图验证
5. Enter 关闭弹窗
6. 点击公会任务 tab (0.797, 0.958)
7. 点击一键领取 (0.898, 0.919) ← 截图验证
8. Enter 关闭弹窗
9. 返回 hub

坐标来源: 02_guild_supply_panel.png + 03_guild_task_panel.png (1280×720)

### 3. DailyWeeklyMissionClaim — 修复周常任务 tab

**变更**: 使用 OCR 定位 周常任务 tab，取代固定坐标。
**原因**: 旧坐标 (0.05, 0.217) 经截图验证实际点击的是 每日任务 tab（已选中），页面不变化。

- 主方案: `FindTextCheck(target="周常任务")` OCR 定位
- 回退: (0.05, 0.30) 估算坐标
- `requires_ocr` 改为 `True`

### 4. AmusementStreetDaily — 新增游园任务领取

**变更**: 在委托派遣后、返回前，新增游园任务奖励领取步骤。
**关键发现**: 游园任务按钮在 STREET 页面底部栏，NOT 面板页面！需 ESC 回到街道再点击。
**新增步骤** (Step 7):
1. ESC 关闭面板 → 回到游乐街页面
2. 点击游园任务 (0.621, 0.944) ← 街道底部栏固定坐标，截图验证
3. OCR 找 一键领取 按钮并点击
4. Enter ×3 消除弹窗
5. 点击 (0.5, 0.005) ×2 关闭残留覆盖层
Step 8 改为 ESC ×1（已在街道页面）+ 返回 hub

### 5. JointDefenseSweep — 新增联防协议奖励领取

**变更**: 扫荡完成后，返回联防协议详情页，点击底部一键领取。
**新增步骤** (Step 9):
1. 按返回键回到联防协议详情页（OCR 验证 前往挑战 可见）
2. 点击任务奖励领取按钮 (0.934, 0.829) ← 右侧蓝色箭头图标，截图验证
3. Enter 关闭弹窗

## 坐标来源

| 坐标 | 来源 | 验证状态 |
|------|------|----------|
| Guild 底部栏 tab | guild_main.png 像素分析 | ✅ 截图验证 |
| 领取 (矩阵补给) 0.5, 0.71 | 02_guild_supply_panel.png | ✅ 截图验证 |
| 一键领取 (公会任务) 0.898, 0.919 | 03_guild_task_panel.png | ✅ 截图验证 |
| 周常任务 tab | OCR 驱动 | ✅ 无需固定坐标 |
| 游园任务 0.621, 0.944 | 04_amusement_street.png | ✅ 截图验证 |
| 联防协议奖励 0.934, 0.829 | 07_joint_defense_detail.png | ✅ 截图验证 |

## 修正历史

- **2026-04-18 v1**: 初始实现，3 个坐标为估算值
- **2026-04-18 v2**: 诊断截图验证后修正全部坐标：
  - Guild 领取: 0.65 → 0.71 (偏低了)
  - Guild 一键领取: (0.925,0.956) → (0.898,0.919) (偏右偏低)
  - 游园任务: 从 OCR 面板搜索改为固定坐标街道页面 (0.621,0.944)
  - 联防协议: (0.17,0.88) → (0.934,0.829) (完全在错误的一侧！)
  - 每日补给 tab: wait 0.5s → 1.0s (太快导致未切换 tab)

### 6. BuyIntelShards — 修复误购刻印 Bug

**变更**: 修复脚本在每日采购页面误购非情报道具（刻印）的问题。
**原因**: 三处缺陷导致安全检查失效：

| 问题 | 根因 | 修复 |
|------|------|------|
| 弹窗安全检查无效 | `HasTextCheck("情报")` 搜索全屏，背景页面的情报文字导致检查始终通过 | 限制 OCR 区域到弹窗中心 `_POPUP_REGION = Rect(450, 250, 700, 350)` |
| 点击坐标偏低 | 点击"XX情报"文字标签中心（卡片底部），可能点到下方刻印卡片 | 点击文字上方 80px（卡片图片区域） |
| 售罄检测不精确 | `_is_sold_out_at` 搜索全屏"售"字 | 限制搜索区域到 `_INTEL_REGION` |

- 文件: `shop_tasks.py`
- 弹窗等待时间: 0.5s → 1.0s（确保弹窗完全打开）

### 7. DailyRoutine 最新失败日志结论

**日志**: `dist/anime-game-afk/logs/gui.log` 2026-05-16 21:04-21:13。

**结论**: OCR/打包已恢复，日志显示 `RapidOCR engine initialized (DirectML GPU)`，失败不是 OCR 不可用导致。

**仍失败的任务**:
- `joint_defense`: 已成功进入活动页、找到 `联防协议`、点击 `前往挑战`，但在 Step 6 未找到 `震动`，失败信息为 `震动 not found on map`。需要重新确认联防协议地图/Tab 状态，当前逻辑只找 OCR `震动`，如果默认页不是 `信息集纳` 或地图布局变化会失败。
- `medium_seizure`: 已成功导航到介质攫取并进入战斗，但代码是 passive wait，不会主动战斗；300s 后 `Battle timeout`。需要接入自动战斗/连招，或把该任务改成未启用/需要用户手动战斗。

**额外问题**: `DailyRoutine` 内部有失败子任务时仍返回 `ProcessResult(status="success")`，导致外层 pipeline 日志显示 `Pipeline complete: 1/1 succeeded`，会掩盖子任务失败。

### 8. OCR 重试包装

**变更**: 新增 `ocr_scan_with_retry(ctx, retries=0, retry_delay=0.0, ready=None)`，默认不重试；可用 `ready(OcrResult)` 定义“本次 OCR 是否满足业务条件”。返回同一次采样的 screenshot + `OcrResult`，避免为了坐标换算重复截图。

**应用**:
- `JointDefenseSweep`: 所有 OCR 检查改走 wrapper，传 `retries=2`、`retry_delay=1.5`。`前往作战`、`H`、活动页验证、`联防协议`、`前往挑战`、`信息集纳/震动`、`扫荡`、奖励页验证等都会在条件不满足时重试。
- `MediumSeizureCombat`: 所有该类内 OCR 检查改走 wrapper，传 `retries=2`、`retry_delay=1.5`。`介质`节点、内页验证、奖励状态、战斗结果 OCR 都会避免动画未完成时一次失败即判定。
- `MediumSeizureCombat` 内页验证条件调整为必须同时识别 `开始挑战` 和 `今日积分倍率`；兼容 OCR 拆词为 `今日积分` + `倍率`/`积分倍`。

**测试**: 新增 `tests/games/aether_gazer/checks/test_ocr.py` 覆盖默认单次 OCR 和 `ready` predicate 重试；针对性测试通过。

### 9. 点击期间短暂锁定用户输入

**变更**: `DeviceAdapter.click()` 在调用 MaaFw `post_click(...).wait()` 前执行 `BlockInput(TRUE)`，并在 `finally` 中立即执行 `BlockInput(FALSE)`；锁定范围只覆盖底层点击，不包含任务层的后续等待。

**原因**: 当前输入方法依赖 `SendMessageWithCursorPos`，游戏会读取系统光标位置。用户在自动化点击瞬间移动鼠标时，可能让点击落到错误位置，导致 `介质攫取` / `联防协议` 等流程在动画或页面切换中失败。

**安全性**:
- `BlockInput(FALSE)` 放在 `finally`，即使 MaaFw 点击异常也会释放。
- 若锁定失败（例如非管理员运行），仍继续点击并记录 warning，不把可用性变成硬失败。
- `release_all_held_keys()` 仍作为解锁失败时的恢复兜底。

**测试**: `tests/core/test_device.py` 新增覆盖点击会先锁定后释放、以及点击异常时仍释放。

## 状态

- **创建**: 2026-04-18
- **最后更新**: 2026-05-16
- **测试**: 535 单元测试通过，E2E 需运行验证
