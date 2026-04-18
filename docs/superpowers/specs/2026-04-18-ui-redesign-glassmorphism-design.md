# UI Redesign — Glassmorphism Theme

## Overview

Redesign the existing Vue 3 frontend from a basic dark UI to a polished glassmorphism theme. The app is a pywebview desktop tool (900×600 window) with 3 pages: Tasks, Logs, Settings. All changes are CSS/template-only in the Vue components — no backend changes needed.

Reference mockup: `.superpowers/brainstorm/1416037966-1776521739/content/full-mockup-v3.html`

## Design Direction

**Glassmorphism** — dark purple-blue base with semi-transparent surfaces, gradient accents, and subtle glow effects. Inspired by macOS vibes and modern game launchers.

### Color Palette

| Token | Value | Usage |
|-------|-------|-------|
| bg-base | `#08061a` | Body / deepest background |
| bg-gradient | `#08061a → #0e0a28 → #1a1545 → #0f0825` | Animated background (20s cycle) |
| surface | `rgba(255,255,255,0.025)` | Task cards, panels |
| surface-hover | `rgba(255,255,255,0.06)` | Hover state |
| border | `rgba(255,255,255,0.04)` | Default borders |
| border-hover | `rgba(255,255,255,0.1)` | Hover borders |
| accent-gradient | `#667eea → #764ba2` | Start button, progress, active indicators |
| text-primary | `#e0e0e8` | Headings |
| text-secondary | `#c8c8d0` | Task names, body text |
| text-muted | `rgba(255,255,255,0.35)` | Labels, counts |
| success | `#66bb6a` / `rgba(76,175,80,*)` | Completed tasks |
| running | `#8b9cf7` / `rgba(102,126,234,*)` | Running task glow |
| error | `#ef5350` / `rgba(244,67,54,*)` | Failed tasks |

### Performance Rule

**No `backdrop-filter` on frequently-hovered elements** (task items). Only allowed on sidebar and status bar (infrequent interaction). Task item hover must be instant — no CSS `transition` on the `.task-item` selector.

## Component Changes

### 1. App.vue — Layout & Background

- Add animated gradient background div (`.app-bg`) behind the app
- Wrap sidebar + main in `.app-body` flex container (the update banner sits above)
- `.app` becomes `flex-direction: column` (was `flex`)
- Keep existing update notification bar unchanged

### 2. Sidebar.vue

- Widen from 72px → 88px
- Background: `rgba(8,6,26,0.85)` with `backdrop-filter: blur(20px)`
- Border-right: `rgba(255,255,255,0.05)`
- Logo: gradient square icon (◆ on `#667eea → #764ba2`) with glow shadow
- Nav items: larger hit area (64px wide), rounded 10px
- Active state: left edge glow bar (3px wide, `#667eea`, `box-shadow` glow), tinted background `rgba(102,126,234,0.1)`
- Hover: scale icon 1.1x, light background
- Labels always visible under icons (current behavior, keep)

### 3. ConnectionBar.vue → StatusBar

- Rename conceptually to status bar styling
- Background: `rgba(255,255,255,0.02)`, border-bottom `rgba(255,255,255,0.04)`
- Status dot: green with pulsing glow animation (`box-shadow` pulse)
- Text color: `rgba(255,255,255,0.5)`

### 4. TasksView.vue

- Pipeline selector: subtle styling (transparent bg select, muted label)
- Add progress section above task list:
  - Header: "今日进度" left, "N / M" right
  - 4px track bar with gradient fill (`#667eea → #764ba2`)
  - Progress computed from completed/total task counts

### 5. TaskList.vue — Task Cards

- Each task item gets an emoji icon (defined in task data from backend, fallback to generic)
- Card styling: `rgba(255,255,255,0.025)` bg, `rgba(255,255,255,0.04)` border, 12px border-radius
- **No `transition` on `.task-item`** — hover is instant CSS change
- **No `backdrop-filter`** on task items
- Hover: bg → `rgba(255,255,255,0.06)`, border → `rgba(255,255,255,0.1)`
- Running state: purple-tinted bg, purple border, `box-shadow` glow with `glowPulse` animation (3s), spinning loader
- Success state: green-tinted border, strikethrough name, dimmed icon
- Failed state: red-tinted border
- Custom checkbox: 18px, rounded 6px, accent-gradient fill when checked, ✓ symbol
- Status badges: pill-shaped (6px radius), colored bg + text per state

### 6. ControlBar.vue

- Start button: large (12px padding, 14px font, 700 weight), gradient bg, 12px radius, glow shadow, hover lifts 1px
- Stop button: ghost style (transparent bg, subtle border), hover turns red
- Add progress ring (SVG circle): gradient stroke showing completion %, positioned right side
- Running time display next to ring

### 7. LogOutput.vue

- Toolbar: match surface styling (transparent bg, subtle border)
- Log area: darker bg `rgba(0,0,0,0.3)`, keep monospace font
- Keep existing log level colors (they work well on dark bg)

### 8. SettingsView.vue

- Already updated with toggle switch and update section — keep as-is
- Section headers: keep `#4fc3f7` color (fits the palette)
- Footer: add GitHub link (already done)

### 9. Global Styles (App.vue `<style>`)

- Animated gradient background keyframes
- Updated button classes to match new palette
- Scrollbar: thinner (5px), `rgba(255,255,255,0.08)` thumb
- Page transitions: wrap `<main>` content in Vue `<Transition>` with fade+slide-up (150ms)

## Task Icon Mapping

Icons are defined frontend-side based on `task.id`:

```js
const TASK_ICONS = {
  'launch_game': '🎮',
  'collect_mail': '📬',
  'buy_intel': '🛒',
  'collect_stamina_pack': '🔋',
  'shop_free_stamina': '🏪',
  'mimi_station': '🔭',
  'guild_supply': '🏰',
  'amusement_daily': '🎡',
  'joint_defense': '⚔️',
  'daily_weekly_tasks': '📋',
  'countermeasure': '📝',
}
```

Fallback: `📌` for unmapped tasks.

## Files to Modify

1. `frontend/src/App.vue` — layout restructure, animated bg, page transitions
2. `frontend/src/components/Sidebar.vue` — wider, glassmorphism, glow active indicator
3. `frontend/src/components/ConnectionBar.vue` — status bar restyling
4. `frontend/src/components/TaskList.vue` — card redesign, icons, progress section
5. `frontend/src/components/ControlBar.vue` — gradient button, progress ring
6. `frontend/src/components/LogOutput.vue` — minor toolbar/bg tweaks
7. `frontend/src/views/TasksView.vue` — add progress bar section

## Files NOT Modified

- Backend Python files — zero changes
- `SettingsView.vue` — already updated
- `useApi.js` / `useStore.js` — no changes needed
- `vite.config.js` — no changes

## Build

After all frontend changes: `cd frontend && npm run build`
