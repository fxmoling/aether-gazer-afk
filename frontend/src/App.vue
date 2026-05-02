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
import { useTheme } from './themes/useTheme'

const { loadTheme } = useTheme()

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

  await loadTheme()
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


