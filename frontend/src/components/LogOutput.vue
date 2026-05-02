<template>
  <div class="log-toolbar">
    <select v-model="logFilter" @change="setLogFilter(logFilter)">
      <option value="ALL">全部</option>
      <option value="INFO">INFO</option>
      <option value="WARNING">WARNING</option>
      <option value="ERROR">ERROR</option>
      <option value="DEBUG">DEBUG</option>
    </select>
    <label class="checkbox-label">
      <input type="checkbox" v-model="autoScroll">
      <span>自动滚动</span>
    </label>
    <button class="btn btn-secondary" @click="clearLogs()">清空</button>
  </div>
  <div ref="logOutputRef" class="log-output">
    <div
      v-for="(entry, i) in displayLogs"
      :key="i"
      class="log-entry"
      :class="`log-${entry.level}`"
    >
      [{{ entry.time }}] {{ entry.level.padEnd(7) }} {{ entry.message }}
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { filteredLogs, clearLogs, setLogFilter, state } from '../composables/useStore'

const logFilter = ref('ALL')
const autoScroll = ref(true)
const logOutputRef = ref(null)

const displayLogs = filteredLogs

watch(displayLogs, async () => {
  if (autoScroll.value) {
    await nextTick()
    const el = logOutputRef.value
    if (el) el.scrollTop = el.scrollHeight
  }
}, { deep: true })
</script>

<style scoped>
.log-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 20px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
}

.log-toolbar select {
  padding: 6px 12px;
  background: var(--bg-surface-hover);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: 12px;
}

.log-output {
  flex: 1;
  overflow-y: auto;
  padding: 8px 20px;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.7;
  background: var(--log-bg);
}

.log-entry {
  white-space: pre-wrap;
  word-break: break-all;
}

.log-DEBUG { color: var(--log-debug); }
.log-INFO { color: var(--log-info); }
.log-WARNING { color: var(--log-warning); }
.log-ERROR { color: var(--log-error); }
.log-SUCCESS { color: var(--log-success); }

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-muted);
}

.checkbox-label input[type="checkbox"] {
  accent-color: var(--accent-1);
  width: 16px;
  height: 16px;
  cursor: pointer;
}
</style>
