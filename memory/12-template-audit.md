# 模板系统审查与清理 (2026-04-18)

## 审查结论

23个模板审查后，仅保留5个，删除18个。

### 保留的模板 (5个)

| 模板 | 页面 | 用途 | ref_height | 特征 |
|------|------|------|------------|------|
| main_hub__goto_battle | main_hub | AtHubCheck 检测 active hub | 720 | 按钮 icon，高对比度 |
| main_hub__mr_icon | main_hub | AtHubCheck 检测 active hub | 720 | MR 图标，独特小 icon |
| hub_idle__disc_icon | hub_idle | AtHubCheck 检测 idle hub | 720 | 碟片 icon，圆形蒙版 |
| shop__trade_tab | shop | GotoPageAction 验证到达商店 | 720 | 用户手动选择的稳定特征 |
| character__char_right_icons | character | 角色页面识别（预留） | 900 | 右侧 icon 列 |

### 删除原因分类

| 问题类型 | 删除的模板 |
|----------|-----------|
| 半透明背景 | shop_bottom_tabs, guild_bottom_nav, amusement_bottom_bar, char_bottom_bar |
| 版本敏感文字 | gacha_banner_list, events_left_tabs, tactics_contract_labels |
| 动态内容 | player_collection_stats, daily_score_bar, training_reward_area, inventory_left_tabs |
| 低对比度/特征不足 | tactics_level_bar, training_left_tabs, daily_left_tabs, battle_tab_bar |
| 背景干扰 | uid_icon |
| 公会名变化 | guild_info_header |
| 日常不需要 | mail_header, settings_grid |

## 模板使用链

```
AtHubCheck (每个 task 调用)
  → is_on_page("main_hub")  → goto_battle + mr_icon (2个都必须通过)
  → is_on_page("hub_idle")  → disc_icon (圆形蒙版)
  → OCR fallback ("前往作战" 等 4 关键词, ≥2 即可)

WakeHubUiAction (task 开始时调用)
  → is_on_page("main_hub")  → 已 active, 跳过
  → is_on_page("hub_idle")  → 点击 back button 唤醒

GotoPageAction("shop") (BuyIntelShards, ClaimFreeStamina)
  → OnPageCheck("shop")     → shop__trade_tab
  → IdentifyPageCheck()     → 扫描所有 5 个模板, 选最高分
```

## 关键设计决策

### MATCH_THRESHOLD 0.65 → 0.80
- 原因: 1280×720 原生分辨率下, ref_height=900 的模板缩放后产生 false positive
- shop_bottom_tabs 在 hub 上得分 0.75 (超过 0.65), 导致 GotoPage 误判
- TM_CCOEFF_NORMED 对低特征模板天然虚高 (归一化互相关, 方差小时数值不稳定)
- 0.80 阈值: 合法匹配 0.96+, 误匹配 <0.78, 留有足够安全边距

### WakeHubUiAction 重写 (不再按 ESC)
- 旧: 按 ESC → 在 active hub 触发退出弹窗 → OCR 检测 → ESC 取消 (~5s 浪费)
- 新: 模板检测状态 → active 跳过 / idle 点击 back button (~5ms)

### 模板选择原则
1. 高对比度的独特 icon/图标，不是大面积 UI 条
2. 不含版本敏感文字、动态数值
3. 非透明背景区域
4. 在其他页面不会出现的特征

## Commits
- `0486f12` — refactor: clean up templates
- `706831c` — fix: raise MATCH_THRESHOLD 0.65->0.80
- `34c9387` — fix: WakeHubUiAction no longer presses ESC
- `7477b4a` — perf: optimize action timing
