# 连招录制功能 (2026-05-04)

## 功能概述

实现了连招录制功能，允许用户通过在游戏中实际操作来生成连招脚本，取代手动逐步编辑。

## 架构

### 后端 (recorder.py)
- `ComboRecorder` — 通过 pynput 捕获键盘输入，编译为 press/hold/wait 步骤
- 全局快捷键: F9 切换录制, F11 强制停止
- 结果缓冲机制: `_pending_result` + `consume_result()` — 支持快捷键触发的异步结果消费
- 实时反馈: `_recent_keys` 环形缓冲区（最多30个）+ `countdown_remaining` 倒计时
- 编译策略: 配对 key_down/key_up → 短按(<250ms)=press, 长按=hold, 间隔>300ms=wait

### API 层 (api.py + task_manager.py)
- `start_combo_recording(section, countdown)` — 开始录制
- `stop_combo_recording()` — 停止录制并返回编译后的步骤
- `consume_combo_result()` — 消费快捷键触发的录制结果
- `test_combo_playback(steps, loops)` — 通过 DeviceAdapter 回放测试（带排他性检查）

### 前端 (CombatView.vue)
- 录制覆盖层: 倒计时动画 + 实时按键芯片 + 事件计数
- 替换/追加模式切换
- 安全替换: 录制到临时缓冲区，空结果时恢复旧步骤
- 测试按钮: ▶ 测试 — 在游戏中回放当前连招
- 快捷键提示: "F9 录制 · F11 停止"

## 关键设计决策

1. **前端为状态主人** — 快捷键改变后端状态，前端轮询检测 + 消费结果
2. **安全替换** — 录制到临时缓冲区，成功且有步骤才替换；取消/空结果时恢复旧数据
3. **排他性回放** — 测试回放前检查自动战斗/任务是否运行中
4. **复用现有Runner** — 测试回放通过 CombatScript + execute_steps，与正式自动战斗一致
5. **v1不支持并行按键** — 重叠输入展平为顺序步骤

## 文件变更

| 文件 | 变更 |
|------|------|
| `combat/recorder.py` | 重构: 快捷键自连接、结果缓冲、实时反馈、改进编译 |
| `ui/task_manager.py` | 新增: consume_combo_result, test_combo_playback |
| `ui/api.py` | 新增: consume_combo_result, test_combo_playback 端点 |
| `frontend/src/composables/useApi.js` | 新增: consumeComboResult, testComboPlayback |
| `frontend/src/views/CombatView.vue` | 重写: 录制覆盖层、替换/追加模式、测试按钮 |
| `docs/combat-scripts.md` | 新增: 连招录制使用指南 |
| `combat/README.md` | 更新: 添加 recorder.py 文档 |

## 未来扩展

当需要操作录制（生成task）时，可从 `ComboRecorder` 提取 `InputRecorder` 协议：
- 抽象键盘捕获 + 编译逻辑
- ComboRecorder 继续处理战斗按键
- TaskRecorder 处理UI导航 + 鼠标操作
