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
  padding: 10px 16px;
  background: #16213e;
  border-bottom: 1px solid #252550;
}

.log-toolbar select {
  padding: 4px 8px;
  background: #0f1129;
  color: #e0e0e0;
  border: 1px solid #333;
  border-radius: 4px;
  font-size: 12px;
}

.log-output {
  flex: 1;
  overflow-y: auto;
  padding: 8px 16px;
  font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.7;
  background: #0a0a1a;
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
  color: #aaa;
}

.checkbox-label input[type="checkbox"] {
  accent-color: #4fc3f7;
  width: 16px;
  height: 16px;
  cursor: pointer;
}
</style>
