<template>
  <div class="control-bar">
    <div class="control-actions">
      <button
        class="btn btn-start"
        :disabled="state.running"
        @click="handleStart"
      >
        ▶ 开始
      </button>
      <button
        class="btn btn-stop"
        :disabled="!state.running"
        @click="handleStop"
      >
        ■ 停止
      </button>
    </div>
    <div class="run-status">
      {{ statusText }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { state, startRun, stopRun } from '../composables/useStore'

const statusText = computed(() => {
  if (state.running) {
    const min = Math.floor(state.elapsedS / 60)
    const sec = Math.floor(state.elapsedS % 60)
    const time = `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
    return `${state.completedCount}/${state.totalCount} 完成 · 运行中 ${time}`
  }
  if (state.completedCount > 0 || state.totalCount > 0) {
    return `${state.completedCount}/${state.totalCount} 完成`
  }
  return ''
})

async function handleStart() {
  const result = await startRun()
  if (!result.ok) {
    alert(result.error || '启动失败')
  }
}

async function handleStop() {
  await stopRun()
}
</script>

<style scoped>
.control-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: #16213e;
  border-top: 1px solid #252550;
}

.control-actions {
  display: flex;
  gap: 8px;
}

.run-status {
  color: #888;
  font-size: 12px;
}
</style>
