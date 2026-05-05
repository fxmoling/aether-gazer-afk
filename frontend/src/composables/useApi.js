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
  getSettings: () => apiCall('get_settings'),
  saveSettings: (windowTitle) =>
    apiCall('save_settings', windowTitle),
  saveCombatKeybinds: (binds) =>
    apiCall('save_combat_keybinds', binds),
  detectGame: () => apiCall('detect_game'),
  launchGame: () => apiCall('launch_game'),
  checkUpdate: () => apiCall('check_update'),
  setAutoUpdate: (enabled) => apiCall('set_auto_update', enabled),
  setNotifyOnComplete: (enabled) => apiCall('set_notify_on_complete', enabled),
  setTheme: (themeId) => apiCall('set_theme', themeId),
  openLogFolder: () => apiCall('open_log_folder'),
  setPostRunAction: (action) => apiCall('set_post_run_action', action),
  startAutoBattle: (scriptName = '') => apiCall('start_auto_battle', scriptName),
  stopAutoBattle: () => apiCall('stop_auto_battle'),
  swapAutoBattleScript: (scriptName) => apiCall('swap_auto_battle_script', scriptName),
  getAutoBattleStatus: () => apiCall('get_auto_battle_status'),
  listCombatScripts: () => apiCall('list_combat_scripts'),
  getCombatScript: (scriptId) => apiCall('get_combat_script', scriptId),
  saveCombatScript: (scriptId, content) => apiCall('save_combat_script', scriptId, content),
  deleteCombatScript: (scriptId) => apiCall('delete_combat_script', scriptId),
  validateCombatScript: (content) => apiCall('validate_combat_script', content),
  setCombatScript: (scriptName) => apiCall('set_combat_script', scriptName),
  // Combo recording
  startComboRecording: (section, countdown) => apiCall('start_combo_recording', section, countdown),
  stopComboRecording: () => apiCall('stop_combo_recording'),
  getComboRecorderStatus: () => apiCall('get_combo_recorder_status'),
  consumeComboResult: () => apiCall('consume_combo_result'),
  testComboPlayback: (stepsData, loops) => apiCall('test_combo_playback', stepsData, loops),
  // Schedule
  getSchedule: () => apiCall('get_schedule'),
  saveSchedule: (config) => apiCall('save_schedule', config),
  deleteSchedule: () => apiCall('delete_schedule'),
  getScheduleHistory: () => apiCall('get_schedule_history'),
  // Duowei settings
  saveDuoweiSwipeMultiplier: (value) => apiCall('save_duowei_swipe_multiplier', value),
  // Lizhan settings
  saveLizhanNextKey: (key) => apiCall('save_lizhan_next_key', key),
}
