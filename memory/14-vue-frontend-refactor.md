# 前端 Vue 3 重构 (2026-04-18)

## 概述

从裸 HTML/JS/CSS 迁移到 Vue 3 + Vite 构建体系。Python 后端零修改。

## 技术栈

- **框架**: Vue 3 (Composition API + SFC)
- **构建工具**: Vite 8.x
- **状态管理**: composables + reactive() (无 Pinia/Vuex)
- **路由**: 无 Vue Router — 3 页面用 v-if 切换
- **运行时**: pywebview (WebView2) 加载构建产物

## 目录结构

```
frontend/                    ← 开发目录 (不打包进发布版)
  src/
    App.vue                  ← 根布局 (侧边栏 + 页面切换)
    composables/
      useApi.js              ← pywebview.api 封装
      useStore.js            ← 中央响应式状态
    components/
      Sidebar.vue            ← 导航侧边栏
      ConnectionBar.vue      ← 连接/断开 + 状态
      TaskList.vue           ← 任务复选框列表 + 状态徽标
      ControlBar.vue         ← 开始/停止 + 进度
      LogOutput.vue          ← 日志查看器 (过滤 + 自动滚动)
    views/
      TasksView.vue          ← 任务页面
      LogsView.vue           ← 日志页面
      SettingsView.vue       ← 设置页面 (新增)
  vite.config.js             ← 构建配置 (输出到 ui/web/)
```

## 构建流程

```bash
cd frontend
npm run build   # → src/anime_game_afk/ui/web/ (index.html + app.js + index.css)
```

## 新增页面

### 设置页面 (SettingsView)
- 版本号显示 (0.1.0)
- 游戏窗口标题配置
- 任务间延迟配置
- 关于信息

## Vite 配置要点

- `base: './'` — 相对路径，兼容 file:// 和 http://
- `stripCrossorigin` 插件 — 移除 crossorigin 属性，兼容 pywebview
- `modulePreload: false` — 不需要预加载优化
- 构建产物: app.js (~73KB) + index.css (~7KB)

## Python 后端未修改

以下文件保持不变:
- `bridge.py` — 日志转发

以下文件有重大改动 (2026-04-18 frozen build session):
- `api.py` — 新增 settings/game-launch API，移除 task_delay
- `app.py` — frozen 模式日志写入 logs/gui.log
- `task_manager.py` — 子进程模式（frozen），一键启动，stop 重置任务状态
- `worker.py` — 自动启动游戏+连接，传 game_was_launched 标志

## 状态

- **创建**: 2026-04-18
- **验证**: pywebview 启动正常，界面显示正确
- **更新**: 2026-04-18 — 一键启动 UX，移除手动连接/断开按钮
