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
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
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
  background: var(--conn-dot-connected);
  box-shadow: var(--conn-dot-glow);
  animation: dotPulse 2s ease-in-out infinite;
}

.status-dot.working {
  background: var(--conn-dot-working);
  box-shadow: 0 0 8px var(--accent-glow);
  animation: dotPulse 2s ease-in-out infinite;
}

.status-dot.disconnected {
  background: var(--text-muted);
}

@keyframes dotPulse {
  0%, 100% { box-shadow: var(--conn-dot-glow); }
  50% { box-shadow: 0 0 16px var(--conn-dot-connected); }
}

.status-text {
  font-size: 13px;
  color: var(--text-secondary);
}
</style>
