# 连招脚本使用指南

本文档介绍如何创建和使用自定义连招脚本。连招脚本让你可以定义战斗中角色自动执行的按键序列。

---

## 文件结构

### 格式

连招脚本使用 **YAML** 格式编写。YAML 是一种简洁的配置文件格式，使用缩进表示层级关系。

### 保存位置

所有连招脚本保存在项目根目录下的 `config/combat_scripts/` 目录中，文件扩展名为 `.yaml`。

### 文件命名规则

文件名（不含 `.yaml` 后缀）只能包含以下字符：
- 英文字母（a-z, A-Z）
- 数字（0-9）
- 下划线（`_`）、连字符（`-`）
- 中文字符

文件名最长 64 个字符。

**示例**：`fantian.yaml`、`梵天.yaml`、`my_combo_1.yaml`

---

## 基本概念

一个连招脚本包含两个阶段：

### 启动连招（startup）— 可选

战斗开始时 **只执行一次** 的动作序列。适合放置开场蓄力、闪避等一次性操作。

### 循环连招（loop）— 必填

战斗过程中 **反复循环执行** 的动作序列。这是连招的核心部分。

### 旧格式兼容

如果你看到使用 `steps:` 的旧格式脚本，它仍然可以正常工作。`steps:` 等效于只有 `loop:`、没有 `startup:` 的连招。

> ⚠️ 不能同时使用 `steps:` 和 `startup:/loop:`，只能选其一。

---

## 支持的动作类型

### 1. 按键（press）— 点按一次

```yaml
- press: j
```

模拟按下并松开一个键。

### 2. 长按（hold）— 按住一段时间

```yaml
- hold: space
  duration: 0.3
```

模拟按住某个键一段时间（单位：秒）。`duration` 是必填参数。

### 3. 等待（wait）— 暂停一段时间

```yaml
- wait: 0.5
```

或者简写为直接写数字：

```yaml
- 0.5
```

在动作之间等待指定秒数。

---

## 可用按键

| 按键 | 功能 | YAML 写法 |
|------|------|-----------|
| J | 普通攻击 | `press: j` |
| U | 技能 1 | `press: u` |
| I | 技能 2 | `press: i` |
| O | 技能 3 | `press: o` |
| R | 大招（终结技） | `press: r` |
| 1 | 连携 1（QTE） | `press: "1"` |
| 2 | 连携 2（QTE） | `press: "2"` |
| W | 前进 | `press: w` |
| A | 左移 | `press: a` |
| S | 后退 | `press: s` |
| D | 右移 | `press: d` |
| Space | 闪避 | `press: space` |

> ⚠️ **数字键必须加引号**：`press: "1"` 和 `press: "2"`。不加引号会被 YAML 解析为数字而不是字符串。

---

## 全局参数

```yaml
name: 我的连招
description: 这是一个自定义连招
interval: 0.12
```

| 参数 | 说明 | 是否必填 |
|------|------|----------|
| `name` | 连招名称，支持中文和英文 | 推荐填写 |
| `description` | 连招描述 | 可选 |
| `interval` | 默认按键间隔（秒），即每次按键后等待多久再执行下一步 | 可选，默认 `0.12` |

### 单步覆盖间隔

每个动作步骤可以用 `interval` 覆盖全局值：

```yaml
- press: j
  interval: 0.2    # 这一步之后等待 0.2 秒，而不是全局的 0.12 秒
```

---

## 完整示例

### 示例 1：最简单的连招（仅 loop）

```yaml
name: 默认连招
description: 通用攻击循环
interval: 0.12
loop:
  - press: j
  - press: j
  - press: u
  - press: j
  - press: i
  - press: j
  - press: o
  - press: r
  - press: "1"
  - press: "2"
```

这个连招会不停循环：攻击×2 → 技能1 → 攻击 → 技能2 → 攻击 → 技能3 → 大招 → 连携1 → 连携2。

### 示例 2：带 startup 的连招（开场闪避 + 循环攻击）

```yaml
name: 梵天
description: 开场闪避蓄力 → 攻击技能循环连招
interval: 0.12
startup:
  - hold: space
    duration: 0.3
loop:
  - press: j
  - press: j
  - press: j
  - press: u
  - press: u
  - press: o
  - press: o
  - press: "1"
  - press: j
  - press: "2"
  - press: i
  - press: j
  - press: j
  - press: j
  - press: u
  - press: u
  - press: o
  - press: o
  - press: r
```

战斗开始时先长按闪避键 0.3 秒进行蓄力，然后进入攻击循环。

### 示例 3：复杂连招（多技能组合 + 等待 + 长按）

```yaml
name: 高级连招
description: 包含等待和长按的复杂连招
interval: 0.10
startup:
  - hold: space
    duration: 0.5
  - wait: 0.3
  - press: u
loop:
  - press: j
  - press: j
  - press: j
    interval: 0.2
  - hold: j
    duration: 0.3
  - press: u
  - press: i
  - wait: 0.5
  - press: o
  - press: r
  - press: "1"
  - press: j
  - press: "2"
```

这个连招演示了：
- **startup**：开场长按闪避 0.5 秒 → 等待 0.3 秒 → 释放技能1
- **loop**：攻击×3（第3下间隔更长）→ 长按攻击 → 技能1 → 技能2 → 等待 0.5 秒 → 技能3 → 大招 → 连携

---

## 如何选择连招

1. 在应用的 **设置页面** 中，找到「连招脚本」选项
2. 从下拉列表中选择你想使用的连招脚本
3. 所有自动战斗功能（多维变量、介质攫取等）都会使用你选中的连招

---

## 注意事项

- **按键间隔不要太短**：建议 `interval` ≥ 0.08 秒。间隔过短可能导致游戏来不及响应。
- **游戏更新可能影响按键**：如果游戏版本更新后按键映射发生变化，需要相应调整脚本。
- **可视化编辑**：你可以打开 `docs/combat-script-editor.html` 文件，使用可视化编辑器来创建和编辑连招，无需手动编写 YAML。
- **测试你的连招**：创建新连招后，建议先在简单关卡中测试效果。
- **备份自定义脚本**：更新工具时，`config/combat_scripts/` 目录下的自定义脚本不会被覆盖，但建议自行备份。
