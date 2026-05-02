# AetherGazer AFK — Frontend

Vue 3 + Vite 前端，运行在 pywebview (WebView2) 中。

## 构建

```bash
cd frontend
npm run build  # → src/anime_game_afk/ui/web/
```

## 主题系统

12 个内置主题，基于 CSS 变量的三层架构：

```
themes/
  base.css              ← 共享样式 (var() 引用)
  useTheme.js           ← 切换/持久化 composable
  registry.js           ← 主题元数据
  tokens/*.css (×12)    ← 每主题 106 个 CSS 变量
```

### 添加新主题
1. 复制 `tokens/cosmic-purple.css` → `tokens/my-theme.css`
2. 修改所有变量值
3. 在 `registry.js` 添加元数据
4. 在 `main.js` 添加 import

### 添加新组件
所有颜色使用 `var(--token)` — 自动适配全部主题。**永远不要硬编码颜色。**

### 可用 token 分类
- `--bg-*` 背景 | `--text-*` 文字 | `--accent-*` 强调色
- `--border-*` 边框 | `--status-*` 状态 | `--btn-*` 按钮
- `--toggle-*` 开关 | `--chip-*` 芯片 | `--log-*` 日志
- `--radius-*` 圆角 | `--font-*` 字体 | `--shadow-*` 阴影
