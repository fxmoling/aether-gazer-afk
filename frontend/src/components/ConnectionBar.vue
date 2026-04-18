<template>
  <div class="status-bar">
    <div class="status-left">
      <div class="status-dot" :class="dotClass"></div>
      <span class="status-text">{{ statusText }}</span>
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
.status-bar {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  background: rgba(255,255,255,0.02);
  border-bottom: 1px solid rgba(255,255,255,0.04);
}

.status-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.connected {
  background: #4caf50;
  box-shadow: 0 0 8px rgba(76,175,80,0.5);
  animation: dotPulse 2s ease-in-out infinite;
}

.status-dot.working {
  background: #8b9cf7;
  box-shadow: 0 0 8px rgba(102,126,234,0.5);
  animation: dotPulse 2s ease-in-out infinite;
}

.status-dot.disconnected {
  background: rgba(255,255,255,0.2);
}

@keyframes dotPulse {
  0%, 100% { box-shadow: 0 0 8px rgba(76,175,80,0.5); }
  50% { box-shadow: 0 0 16px rgba(76,175,80,0.8); }
}

.status-text {
  font-size: 13px;
  color: rgba(255,255,255,0.5);
}
</style>
