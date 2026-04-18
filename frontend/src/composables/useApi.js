/**
 * Wrapper around pywebview.api for type-safe calls.
 * Falls back gracefully when pywebview is not available (dev mode).
 */

function getApi() {
  if (typeof pywebview !== 'undefined' && pywebview.api) {
    return pywebview.api
  }
  return null
}

export async function apiCall(method, ...args) {
  const api = getApi()
  if (!api) {
    console.warn(`[useApi] pywebview.api not available, skipping ${method}`)
    return null
  }
  try {
    return await api[method](...args)
  } catch (e) {
    console.error(`[useApi] ${method} failed:`, e)
    throw e
  }
}

export const api = {
  connect: () => apiCall('connect'),
  disconnect: () => apiCall('disconnect'),
  getStatus: () => apiCall('get_status'),
  getPipelines: () => apiCall('get_pipelines'),
  setTaskEnabled: (pipelineId, taskId, enabled) =>
    apiCall('set_task_enabled', pipelineId, taskId, enabled),
  setAllEnabled: (pipelineId, enabled) =>
    apiCall('set_all_enabled', pipelineId, enabled),
  startRun: (pipelineId) => apiCall('start_run', pipelineId),
  stopRun: () => apiCall('stop_run'),
  getRecentLogs: (count = 200) => apiCall('get_recent_logs', count),
}
