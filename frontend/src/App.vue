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
    <!-- Toast notifications -->
    <Teleport to="body">
      <TransitionGroup name="toast" tag="div" class="toast-container">
        <div
          v-for="t in state.toasts"
          :key="t.id"
          class="toast-item"
          :class="'toast-' + t.type"
          @click="dismissToast(t.id)"
        >
          <span class="toast-icon">{{ t.type === 'error' ? '❌' : t.type === 'warning' ? '⚠️' : 'ℹ️' }}</span>
          <span class="toast-text">{{ t.text }}</span>
        </div>
      </TransitionGroup>
    </Teleport>
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
  state,
  loadPipelines,
  loadRecentLogs,
  pollStatus,
  updateTaskStatus,
  onConnected,
  onStatusMsg,
  onError,
  onTaskMessage,
  dismissToast,
  appendLog,
  pushToast,
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
  window.onTaskMessage = onTaskMessage
  window.appendLog = appendLog
  window.onRunComplete = onRunComplete
  window.onAutoBattleState = (enabled, script) => {
    state.autoBattleOn = !!enabled
    state.autoBattleScript = script || ''
  }

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
.toast-container {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 99999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
  max-width: 380px;
}

.toast-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 8px;
  backdrop-filter: blur(12px);
  cursor: pointer;
  pointer-events: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  font-size: 13px;
  line-height: 1.4;
}

.toast-error {
  background: rgba(239, 68, 68, 0.9);
  color: #fff;
  border: 1px solid rgba(255, 100, 100, 0.4);
}

.toast-warning {
  background: rgba(245, 158, 11, 0.9);
  color: #fff;
  border: 1px solid rgba(255, 200, 50, 0.4);
}

.toast-info {
  background: rgba(99, 102, 241, 0.9);
  color: #fff;
  border: 1px solid rgba(140, 140, 255, 0.4);
}

.toast-icon {
  flex-shrink: 0;
  font-size: 14px;
}

.toast-text {
  flex: 1;
  word-break: break-word;
}

.toast-enter-active {
  transition: all 0.3s ease;
}

.toast-leave-active {
  transition: all 0.2s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(40px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(40px);
}
</style>