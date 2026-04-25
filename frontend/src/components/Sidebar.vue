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
  { page: 'settings', icon: '⚙', label: '设置' },
]
</script>

<style scoped>
.sidebar {
  width: 88px;
  background: rgba(8,6,26,0.85);
  backdrop-filter: blur(20px);
  border-right: 1px solid rgba(255,255,255,0.05);
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
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 6px;
  font-size: 18px;
  color: white;
  box-shadow: 0 2px 12px rgba(102,126,234,0.3);
}

.logo-text {
  font-size: 9px;
  color: rgba(255,255,255,0.4);
  letter-spacing: 0.5px;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 8px;
  margin: 2px 0;
  border-radius: 10px;
  cursor: pointer;
  text-decoration: none;
  color: rgba(255,255,255,0.3);
  transition: color 0.1s, background 0.1s;
  width: 64px;
  position: relative;
  user-select: none;
}

.nav-item:hover {
  background: rgba(255,255,255,0.05);
  color: rgba(255,255,255,0.65);
}

.nav-item:hover .nav-icon {
  transform: scale(1.1);
}

.nav-item.active {
  color: #b8c4ff;
  background: rgba(102,126,234,0.1);
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: -2px;
  top: 12px;
  bottom: 12px;
  width: 3px;
  background: #667eea;
  border-radius: 2px;
  box-shadow: 0 0 8px rgba(102,126,234,0.6);
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
