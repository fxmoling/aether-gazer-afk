<template>
  <nav class="sidebar">
    <div class="logo">
      <div class="logo-icon">◆</div>
      <div class="logo-text">AFK</div>
    </div>
    <a
      v-for="item in items"
      :key="item.page"
      class="nav-item"
      :class="{ active: currentPage === item.page }"
      @click="$emit('navigate', item.page)"
    >
      <span class="nav-icon" v-html="item.icon"></span>
      <span class="nav-label">{{ item.label }}</span>
    </a>
  </nav>
</template>

<script setup>
defineProps({
  currentPage: { type: String, default: 'tasks' },
})
defineEmits(['navigate'])

const items = [
  { page: 'tasks', icon: '☑', label: '任务' },
  { page: 'schedule', icon: '⏰', label: '定时' },
  { page: 'logs', icon: '≡', label: '日志' },
  { page: 'combat', icon: '⚔', label: '连招' },
  { page: 'settings', icon: '⚙', label: '设置' },
]
</script>

<style scoped>
.sidebar {
  width: 88px;
  background: var(--bg-sidebar);
  backdrop-filter: blur(20px);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0;
  flex-shrink: 0;
}

.logo {
  text-align: center;
  margin-bottom: 28px;
}

.logo-icon {
  width: 36px;
  height: 36px;
  background: var(--accent-gradient);
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 6px;
  font-size: 18px;
  color: var(--text-on-accent);
  box-shadow: var(--sidebar-logo-shadow);
}

.logo-text {
  font-size: 9px;
  color: var(--text-muted);
  letter-spacing: 0.5px;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 8px;
  margin: 2px 0;
  border-radius: var(--radius-lg);
  cursor: pointer;
  text-decoration: none;
  color: var(--sidebar-tab-text);
  transition: color 0.1s, background 0.1s;
  width: 64px;
  position: relative;
  user-select: none;
}

.nav-item:hover {
  background: var(--bg-surface-hover);
  color: var(--text-secondary);
}

.nav-item:hover .nav-icon {
  transform: scale(1.1);
}

.nav-item.active {
  color: var(--sidebar-tab-active-text);
  background: var(--sidebar-tab-active-bg);
}

.nav-icon {
  font-size: 20px;
  margin-bottom: 3px;
  transition: transform 0.1s;
}

.nav-label {
  font-size: 10px;
}
</style>
