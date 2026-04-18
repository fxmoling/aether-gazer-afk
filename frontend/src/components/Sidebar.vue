<template>
  <nav class="sidebar">
    <div class="logo">
      <span class="logo-icon">◆</span>
      <span class="logo-text">AetherGazer<br>AFK</span>
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
  { page: 'logs', icon: '≡', label: '日志' },
  { page: 'settings', icon: '⚙', label: '设置' },
]
</script>

<style scoped>
.sidebar {
  width: 72px;
  background: #0f1129;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 0;
  flex-shrink: 0;
  border-right: 1px solid #252550;
}

.logo {
  text-align: center;
  margin-bottom: 24px;
  padding: 8px 4px;
}

.logo-icon {
  font-size: 24px;
  color: #4fc3f7;
  display: block;
}

.logo-text {
  font-size: 9px;
  color: #888;
  line-height: 1.3;
  margin-top: 4px;
  display: block;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 8px;
  margin: 4px 0;
  border-radius: 8px;
  cursor: pointer;
  text-decoration: none;
  color: #888;
  transition: all 0.2s;
  width: 56px;
  user-select: none;
}

.nav-item:hover {
  background: #1a1a3e;
  color: #ccc;
}

.nav-item.active {
  background: #1a1a4e;
  color: #4fc3f7;
}

.nav-icon {
  font-size: 20px;
  margin-bottom: 2px;
}

.nav-label {
  font-size: 10px;
}
</style>
