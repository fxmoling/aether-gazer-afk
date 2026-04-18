<template>
  <div class="app">
    <!-- Update notification banner -->
    <div v-if="updateAvailable" class="update-bar">
      <span>🎉 新版本 <b>v{{ updateVersion }}</b> 可用</span>
      <a :href="updateUrl" target="_blank" class="update-link">前往下载</a>
      <button class="update-dismiss" @click="updateAvailable = false">✕</button>
    </div>
    <div class="app-body">
      <Sidebar :currentPage="currentPage" @navigate="currentPage = $event" />
      <main class="main-content">
        <TasksView v-if="currentPage === 'tasks'" />
        <LogsView v-if="currentPage === 'logs'" />
        <SettingsView v-if="currentPage === 'settings'" />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import Sidebar from './components/Sidebar.vue'
import TasksView from './views/TasksView.vue'
import LogsView from './views/LogsView.vue'
import SettingsView from './views/SettingsView.vue'
import { api } from './composables/useApi'
import {
  loadPipelines,
  loadRecentLogs,
  pollStatus,
  updateTaskStatus,
  onConnected,
  onStatusMsg,
  onError,
  appendLog,
  onRunComplete,
} from './composables/useStore'

const currentPage = ref('tasks')
const updateAvailable = ref(false)
const updateVersion = ref('')
const updateUrl = ref('')
let statusInterval = null

async function checkUpdateOnStartup() {
  try {
    const result = await api.checkUpdate()
    if (result && result.ok && result.has_update) {
      updateAvailable.value = true
      updateVersion.value = result.latest_version
      updateUrl.value = result.release_url || 'https://github.com/fxmoling/anime-game-afk/releases/latest'
    }
  } catch {
    // Silently ignore update check failures on startup
  }
}

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
  window.onConnected = onConnected
  window.onStatusMsg = onStatusMsg
  window.onError = onError
  window.appendLog = appendLog
  window.onRunComplete = onRunComplete

  // Check for updates (non-blocking, after UI is ready)
  const settings = await api.getSettings()
  if (settings && settings.auto_update !== false) {
    checkUpdateOnStartup()
  }
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
  flex-direction: column;
  height: 100vh;
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Update notification bar */
.update-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 16px;
  background: linear-gradient(90deg, #1b5e20, #2e7d32);
  color: #e8f5e9;
  font-size: 13px;
  flex-shrink: 0;
}

.update-link {
  color: #fff;
  background: rgba(255,255,255,0.15);
  padding: 2px 10px;
  border-radius: 4px;
  text-decoration: none;
  font-size: 12px;
}

.update-link:hover {
  background: rgba(255,255,255,0.25);
}

.update-dismiss {
  margin-left: auto;
  background: none;
  border: none;
  color: #a5d6a7;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 6px;
}

.update-dismiss:hover {
  color: white;
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
