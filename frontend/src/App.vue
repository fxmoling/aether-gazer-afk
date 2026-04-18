<template>
  <div class="app">
    <Sidebar :currentPage="currentPage" @navigate="currentPage = $event" />
    <main class="main-content">
      <TasksView v-if="currentPage === 'tasks'" />
      <LogsView v-if="currentPage === 'logs'" />
      <SettingsView v-if="currentPage === 'settings'" />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import Sidebar from './components/Sidebar.vue'
import TasksView from './views/TasksView.vue'
import LogsView from './views/LogsView.vue'
import SettingsView from './views/SettingsView.vue'
import {
  loadPipelines,
  loadRecentLogs,
  pollStatus,
  updateTaskStatus,
  appendLog,
  onRunComplete,
} from './composables/useStore'

const currentPage = ref('tasks')
let statusInterval = null

onMounted(async () => {
  // Wait for pywebview ready
  if (typeof pywebview === 'undefined') {
    await new Promise(resolve => {
      window.addEventListener('pywebviewready', resolve, { once: true })
    })
  }

  await loadPipelines()
  await loadRecentLogs()

  // Start status polling
  statusInterval = setInterval(pollStatus, 1000)

  // Register push handlers for Python → JS
  window.updateTaskStatus = updateTaskStatus
  window.appendLog = appendLog
  window.onRunComplete = onRunComplete
})

onUnmounted(() => {
  if (statusInterval) clearInterval(statusInterval)
})
</script>

<style>
/* Global styles */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  background: #1a1a2e;
  color: #e0e0e0;
  font-family: 'Segoe UI', 'Microsoft YaHei', system-ui, sans-serif;
  font-size: 14px;
  overflow: hidden;
  height: 100vh;
}

.app {
  display: flex;
  height: 100vh;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Shared button styles */
.btn {
  padding: 6px 16px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-primary {
  background: #2196f3;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #1976d2;
}

.btn-secondary {
  background: #333;
  color: #ccc;
}

.btn-secondary:hover:not(:disabled) {
  background: #444;
}

.btn-start {
  background: #4caf50;
  color: white;
  font-weight: bold;
}

.btn-start:hover:not(:disabled) {
  background: #388e3c;
}

.btn-stop {
  background: #f44336;
  color: white;
}

.btn-stop:hover:not(:disabled) {
  background: #d32f2f;
}

/* Scrollbar */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: #333;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>
