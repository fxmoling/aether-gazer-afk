<template>
  <div class="app-bg"></div>
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
        <Transition name="page" mode="out-in">
          <TasksView v-if="currentPage === 'tasks'" key="tasks" />
          <ScheduleView v-else-if="currentPage === 'schedule'" key="schedule" />
          <LogsView v-else-if="currentPage === 'logs'" key="logs" />
          <CombatView v-else-if="currentPage === 'combat'" key="combat" />
          <SettingsView v-else-if="currentPage === 'settings'" key="settings" />
        </Transition>
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
import ScheduleView from './views/ScheduleView.vue'
import CombatView from './views/CombatView.vue'
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
  background: #08061a;
  color: #e0e0e0;
  font-family: 'Segoe UI', 'Microsoft YaHei', system-ui, sans-serif;
  font-size: 14px;
  overflow: hidden;
  height: 100vh;
}

.app-bg {
  position: fixed;
  inset: 0;
  background: linear-gradient(135deg, #08061a 0%, #0e0a28 25%, #1a1545 50%, #0f0825 75%, #08061a 100%);
  background-size: 400% 400%;
  animation: gradientShift 20s ease infinite;
  z-index: 0;
}

@keyframes gradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.app {
  position: relative;
  z-index: 1;
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

/* Page transition */
.page-enter-active,
.page-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* Update notification bar */
.update-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 16px;
  background: linear-gradient(90deg, rgba(27,94,32,0.6), rgba(46,125,50,0.6));
  backdrop-filter: blur(10px);
  color: #e8f5e9;
  font-size: 12px;
  flex-shrink: 0;
}

.update-link {
  color: #fff;
  background: rgba(255,255,255,0.15);
  padding: 2px 10px;
  border-radius: 4px;
  text-decoration: none;
  font-size: 11px;
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
  font-size: 13px;
  padding: 2px 6px;
}

.update-dismiss:hover {
  color: white;
}

/* Shared button styles */
.btn {
  padding: 6px 16px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  box-shadow: 0 4px 16px rgba(102,126,234,0.4);
}

.btn-secondary {
  background: rgba(255,255,255,0.04);
  color: #c8c8d0;
  border: 1px solid rgba(255,255,255,0.08);
}

.btn-secondary:hover:not(:disabled) {
  background: rgba(255,255,255,0.08);
}

/* Scrollbar */
::-webkit-scrollbar {
  width: 5px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.08);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255,255,255,0.15);
}

/* Global select styling — dark theme dropdown */
select {
  appearance: none;
  -webkit-appearance: none;
  background-color: rgba(15, 12, 35, 0.95);
  color: #c8c8d0;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  padding: 6px 28px 6px 10px;
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%23888'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  background-size: 10px 6px;
  transition: border-color 0.15s;
}

select:hover {
  border-color: rgba(255,255,255,0.18);
}

select:focus {
  outline: none;
  border-color: rgba(102,126,234,0.5);
}

select:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

select option {
  background: #1a1545;
  color: #c8c8d0;
  padding: 6px 10px;
}
</style>
