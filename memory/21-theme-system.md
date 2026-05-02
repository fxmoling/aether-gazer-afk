# UI 主题系统 (2026-05-02)

## 概述

实现了 12 主题的 CSS 变量主题系统，支持一键切换、持久化存储、新组件自动适配。

## 架构: 三层设计

```
Layer 3: Theme Overrides (可选) — 特殊视觉效果
Layer 2: Base Styles (base.css) — 共享样式，引用 var()
Layer 1: Design Tokens (每主题一份) — 106 个 CSS 自定义属性
```

## 目录结构

```
frontend/src/themes/
  useTheme.js        — 主题切换 composable
  registry.js        — 主题元数据 (id/名称/描述/预览色)
  base.css           — 共享基础样式 (所有颜色用 var())
  tokens/
    cosmic-purple.css    — 默认: 深紫渐变 + 玻璃拟态
    clean-light.css      — 浅灰白底 + 现代扁平
    candy-pastel.css     — 浅彩渐变 + 粉紫橙
    liquid-glass.css     — iOS 26 液态玻璃
    twilight-gradient.css — 紫蓝极光 + 液态面板
    neon-city.css        — 赛博朋克 + 四色流光
    vaporwave.css        — 透视网格 + 复古未来
    sakura-bloom.css     — 粉紫金 + 温柔粉嫩
    ocean-abyss.css      — 深海渐变 + 微星光
    lava-ember.css       — 底部脉动 + 红橙
    neumorphism-light.css — 亮色凸凹投影
    neumorphism-dark.css  — 暗色凸凹投影
```

## 关键设计决策

1. **106 个 CSS 变量** 覆盖所有视觉属性: 背景、文字、强调色、边框、状态色、按钮、开关、复选框、日志色、侧边栏、提示、芯片等
2. **切换机制**: `document.documentElement.setAttribute('data-theme', name)` — 立即生效
3. **持久化**: 通过 Python API `set_theme` / `get_settings().theme` 保存到用户配置
4. **特殊效果**: 赛博扫描线、蒸汽波透视网格、深渊蓝星光、熔岩底部辉光 — 在各自 token 文件末尾用 `[data-theme="xxx"] .app-bg::after` 覆盖
5. **SVG 限制**: 进度环的 SVG 渐变不支持 CSS var()，保持硬编码

## 如何添加新主题

1. 创建 `tokens/my-theme.css`，定义全部 106 个变量
2. 在 `registry.js` 添加一行元数据
3. 在 `main.js` 添加 `import './themes/tokens/my-theme.css'`
4. 完成 — 所有组件自动适配

## 如何添加新组件

只使用 `var(--token)` 引用颜色，**永远不要硬编码**。新组件自动支持全部 12 主题。

## 主题选择器

位于 **设置页面** 顶部，12 个卡片网格布局，点击即切换。
