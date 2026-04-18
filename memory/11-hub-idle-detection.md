# Hub 检测与 Idle 状态处理 (2026-04-18)

## Hub 两种状态

| 状态 | UI 可见 | 检测方法 | 模板匹配 |
|------|---------|----------|----------|
| **Active Hub** | ✅ 底部导航栏、按钮、设置 | 3个模板: goto_battle, mr_icon, uid_icon | TM_CCOEFF_NORMED, threshold=0.65 |
| **Idle Hub** | ❌ ~5秒无操作后UI隐藏 | 1个模板: disc_icon (圆形蒙版) | TM_CCORR_NORMED, threshold=0.85 |

## 关键设计决策

### 1. 底部导航栏不可靠
- 导航栏背景透明，不同设置下颜色完全不同
- 改用3个稳定特征: 右下角"前往作战"按钮非透明部分、右上角"MR"图标、左上角"UID"图标

### 2. Idle 检测使用圆形蒙版
- 音乐播放器碟片图标在 idle/active 两种状态都可见
- 碟片背景可变 → 使用 cv2 circular mask 只匹配碟片圆形区域
- OpenCV 仅 TM_SQDIFF 和 TM_CCORR_NORMED 支持 mask
- TM_CCORR_NORMED 分数偏高(碟片得分1.0), 所以 threshold=0.85

### 3. AtHubCheck 3层检测
```
1. 模板匹配 main_hub (3个模板全部通过) → passed=True, hub_state="active"
2. 模板匹配 hub_idle (碟片模板通过)     → passed=False, hub_state="idle"
3. OCR 关键词 (≥2/4: 前往作战/探测/修正者/仓库) → passed=True, hub_state="active"
```
- **idle 返回 passed=False** 因为调用者期望可交互的 hub
- 调用者看到 hub_state="idle" 后可点击 (0.022, 0.039) 唤醒

### 4. 已知：碟片在 active hub 也匹配
- `is_on_page("hub_idle")` 在 active hub 也返回 True
- AtHubCheck 先检查 main_hub, 所以不影响逻辑
- identify() 返回 main_hub (3模板平均分更高)

## E2E 测试结果 (2026-04-18)

**11/11 任务全部通过, 总耗时 240.1 秒 (4分钟)**

| 任务 | 状态 | 耗时 |
|------|------|------|
| startup | ✅ success | 3.6s |
| mail | ✅ success | 9.4s |
| intel | ✅ success | 27.9s |
| stamina_packs | ✅ success | 30.3s |
| free_stamina | ⏭ skipped | 26.8s |
| mimi | ✅ success | 30.7s |
| guild | ✅ success | 15.2s |
| amusement | ✅ success | 24.0s |
| joint_defense | ✅ success | 50.9s |
| missions | ✅ success | 11.7s |
| tactics | ✅ success | 9.7s |

### 修复的问题
- OCR 搜索区域 Rect 从 1600×900 坐标更新为 1280×720
- `ocr_once()` 增加空裁剪保护，防止零宽度图像导致 RapidOCR 崩溃

## 模板文件

| 模板 | 文件 | 尺寸 | ref_height | mask |
|------|------|------|------------|------|
| goto_battle | main_hub__goto_battle.png | 124×34 | 720 | 无 |
| mr_icon | main_hub__mr_icon.png | 45×30 | 720 | 无 |
| uid_icon | main_hub__uid_icon.png | 32×16 | 720 | 无 |
| disc_icon | hub_idle__disc_icon.png | 38×38 | 720 | circle |

## 性能

| 操作 | 耗时 |
|------|------|
| screenshot() | ~88ms |
| identify() 16页 | ~42ms |
| is_on_page() 单页 | ~3ms |
| AtHubCheck 模板命中 | ~36ms |
| OCR fallback | ~1596ms |

## Commits

- `bfc41f0` — feat: hub idle detection with masked template matching
- `a1c0bf7` — chore: track all template PNGs in git
- `b6d1fd6` — fix: scale OCR search regions from 1600×900 to 1280×720
