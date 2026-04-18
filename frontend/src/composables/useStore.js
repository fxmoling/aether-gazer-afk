/**
 * Central reactive store for app state.
 * Manages pipelines, tasks, connection, and execution status.
 */
import { reactive, computed } from 'vue'
import { api } from './useApi'

const state = reactive({
  // Connection
  connected: false,
  resolution: '',

  // Pipelines & tasks
  pipelines: [],
  selectedPipelineId: null,

  // Execution
  running: false,
  elapsedS: 0,
  completedCount: 0,
  totalCount: 0,

  // Logs
  logs: [],
  logFilter: 'ALL',
})

// --- Computed ---

export const selectedPipeline = computed(() =>
  state.pipelines.find(p => p.id === state.selectedPipelineId) || null
)

export const filteredLogs = computed(() => {
  if (state.logFilter === 'ALL') return state.logs
  return state.logs.filter(l => l.level === state.logFilter)
})

// --- Actions ---

export async function loadPipelines() {
  const data = await api.getPipelines()
  if (data) {
    state.pipelines = data
    if (data.length > 0 && !state.selectedPipelineId) {
      state.selectedPipelineId = data[0].id
    }
  }
}

export async function loadRecentLogs() {
  const logs = await api.getRecentLogs(200)
  if (logs) {
    state.logs = logs
  }
}

export function selectPipeline(id) {
  state.selectedPipelineId = id
}

export async function toggleTask(taskId, enabled) {
  if (!state.selectedPipelineId) return
  await api.setTaskEnabled(state.selectedPipelineId, taskId, enabled)
  const pipeline = state.pipelines.find(p => p.id === state.selectedPipelineId)
  if (pipeline) {
    const task = pipeline.tasks.find(t => t.id === taskId)
    if (task) task.enabled = enabled
  }
}

export async function toggleAllTasks(enabled) {
  if (!state.selectedPipelineId) return
  await api.setAllEnabled(state.selectedPipelineId, enabled)
  const pipeline = state.pipelines.find(p => p.id === state.selectedPipelineId)
  if (pipeline) {
    pipeline.tasks.forEach(t => { t.enabled = enabled })
  }
}

export async function connect() {
  const result = await api.connect()
  if (result && result.ok) {
    state.connected = true
    state.resolution = result.resolution || ''
    return { ok: true }
  }
  state.connected = false
  return { ok: false, error: result?.error || '连接失败' }
}

export async function disconnect() {
  await api.disconnect()
  state.connected = false
  state.resolution = ''
}

export async function startRun() {
  if (!state.selectedPipelineId) return { ok: false, error: '未选择流程' }

  // Reset task statuses
  const pipeline = state.pipelines.find(p => p.id === state.selectedPipelineId)
  if (pipeline) {
    pipeline.tasks.forEach(t => {
      t.status = t.enabled ? 'pending' : 'skipped'
    })
  }

  const result = await api.startRun(state.selectedPipelineId)
  if (result && result.ok) {
    state.running = true
    state.completedCount = 0
    state.totalCount = pipeline ? pipeline.tasks.filter(t => t.enabled).length : 0
  }
  return result || { ok: false }
}

export async function stopRun() {
  await api.stopRun()
}

export async function pollStatus() {
  const status = await api.getStatus()
  if (!status) return
  state.running = status.running
  state.elapsedS = status.elapsed_s || 0
  state.completedCount = status.completed || 0
  state.totalCount = status.total || 0
  if (status.connected && !state.connected) {
    state.connected = true
  }
}

// --- Push handlers (called from Python via evaluate_js) ---

export function updateTaskStatus(taskId, status) {
  for (const p of state.pipelines) {
    const task = p.tasks.find(t => t.id === taskId)
    if (task) {
      task.status = status
      if (status === 'success') state.completedCount++
      break
    }
  }
}

export function appendLog(entry) {
  state.logs.push(entry)
  if (state.logs.length > 1000) {
    state.logs.splice(0, state.logs.length - 1000)
  }
}

export function onRunComplete() {
  state.running = false
  loadPipelines()
}

export function clearLogs() {
  state.logs.splice(0)
}

export function setLogFilter(filter) {
  state.logFilter = filter
}

// Export reactive state
export { state }
