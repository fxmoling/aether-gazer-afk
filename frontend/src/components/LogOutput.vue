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
  background: rgba(255,255,255,0.02);
  border-bottom: 1px solid rgba(255,255,255,0.04);
}

.log-toolbar select {
  padding: 6px 12px;
  background: rgba(255,255,255,0.05);
  color: #c8c8d0;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  font-size: 12px;
}

.log-output {
  flex: 1;
  overflow-y: auto;
  padding: 8px 20px;
  font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.7;
  background: rgba(0,0,0,0.3);
}

.log-entry {
  white-space: pre-wrap;
  word-break: break-all;
}

.log-DEBUG { color: #666; }
.log-INFO { color: #ccc; }
.log-WARNING { color: #ff9800; }
.log-ERROR { color: #f44336; }
.log-SUCCESS { color: #4caf50; }

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 13px;
  color: rgba(255,255,255,0.4);
}

.checkbox-label input[type="checkbox"] {
  accent-color: #667eea;
  width: 16px;
  height: 16px;
  cursor: pointer;
}
</style>
