<template>
  <div class="connection-bar">
    <div class="conn-status">
      <span class="dot" :class="state.connected ? 'connected' : 'disconnected'"></span>
      <span class="conn-text">
        {{ state.connected ? `深空之眼 — 已连接 (${state.resolution || '?'})` : '未连接' }}
      </span>
    </div>
    <div class="conn-actions">
      <button
        class="btn btn-primary"
        :disabled="connecting || state.connected"
        @click="handleConnect"
      >
        {{ connecting ? '连接中...' : '连接' }}
      </button>
      <button
        class="btn btn-secondary"
        :disabled="!state.connected"
        @click="handleDisconnect"
      >
        断开
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { state, connect, disconnect } from '../composables/useStore'

const connecting = ref(false)

async function handleConnect() {
  connecting.value = true
  const result = await connect()
  connecting.value = false
  if (!result.ok) {
    alert(result.error || '连接失败')
  }
}

async function handleDisconnect() {
  await disconnect()
}
</script>

<style scoped>
.connection-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
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

.dot.disconnected {
  background: #666;
}

.conn-text {
  font-size: 13px;
}

.conn-actions {
  display: flex;
  gap: 8px;
}
</style>
