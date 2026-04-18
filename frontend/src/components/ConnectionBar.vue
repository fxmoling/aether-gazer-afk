<template>
  <div class="connection-bar">
    <div class="conn-status">
      <span class="dot" :class="dotClass"></span>
      <span class="conn-text">{{ statusText }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { state } from '../composables/useStore'

const dotClass = computed(() => {
  if (state.connected) return 'connected'
  if (state.running) return 'working'
  return 'disconnected'
})

const statusText = computed(() => {
  if (state.statusMsg) return state.statusMsg
  if (state.connected) return `深空之眼 — 已连接 (${state.resolution || '?'})`
  if (state.running) return '准备中...'
  return '就绪'
})
</script>

<style scoped>
.connection-bar {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  background: #16213e;
  border-bottom: 1px solid #252550;
}

.conn-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot.connected {
  background: #4caf50;
  box-shadow: 0 0 6px #4caf5088;
}

.dot.working {
  background: #ff9800;
  box-shadow: 0 0 6px #ff980088;
  animation: pulse 1s infinite;
}

.dot.disconnected {
  background: #666;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.conn-text {
  font-size: 13px;
}
</style>
