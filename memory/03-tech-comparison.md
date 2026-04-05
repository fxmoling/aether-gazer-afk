# 技术方案对比与选型

## 图像识别

| 方案 | 适用场景 | 参考项目 |
|------|----------|----------|
| 模板匹配 (OpenCV) | UI 按钮、固定图标 | MAA, M9A |
| OCR (PaddleOCR) | 文字识别 | 四个都用 |
| 特征匹配 (ORB/SIFT) | 旋转/缩放变化 | MAA |
| YOLO 目标检测 | 动态物体 | ok-ww |

策略：模板匹配 + OCR 为主，YOLO 按需引入（战斗引擎可能需要）。
MaaFramework 内置了模板匹配 + OCR + 特征匹配。

## 输入模拟

| 方案 | 特点 | 用途 |
|------|------|------|
| PostMessage/SendMessage | 后台，不抢焦点 | 主要方案 |
| MaaFramework Win32Controller | 封装了 PostMessage | 通过 MaaFramework 使用 |

## 任务编排

三层架构：
1. **JSON 管线** — 固定流程（MaaFramework 原生）
2. **条件 JSON** — 带分支的流程
3. **Python 脚本** — 复杂逻辑，调用战斗/导航引擎

## 值得借鉴的设计

- M9A 的 `[JumpBack]` — 弹窗打断恢复
- ok-ww 的 CharFactory — 角色识别 + 技能循环
- ok-ww 的 PostMessage 后台输入
- BetterGI 的分层脚本（路径/战斗/JS 编排）
- MAA 的多策略识别管线（模板→特征→OCR 回退）
- MAA 的 on_error_next — 显式错误恢复路径
