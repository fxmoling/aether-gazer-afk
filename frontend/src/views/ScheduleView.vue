<template>
  <div class="schedule-view">
    <div class="schedule-section">
      <h3>定时任务</h3>
      <p class="section-desc">设置定时执行每日任务，即使程序未运行也能自动触发。</p>

      <div class="setting-row">
        <label>启用定时任务</label>
        <label class="toggle-switch">
          <input type="checkbox" v-model="form.enabled" @change="onSave">
          <span class="toggle-slider"></span>
        </label>
      </div>

      <div class="setting-row">
        <label>执行时间</label>
        <div class="time-picker">
          <input
            type="number" min="0" max="23"
            v-model.number="hour"
            class="time-input"
            :disabled="saving"
            @change="onSave"
          />
          <span class="time-sep">:</span>
          <input
            type="number" min="0" max="59"
            v-model.number="minute"
            class="time-input"
            :disabled="saving"
            @change="onSave"
          />
        </div>
      </div>

      <div class="setting-row">
        <label>执行日期</label>
        <div class="day-chips">
          <button
            v-for="d in allDays" :key="d.id"
            class="day-chip"
            :class="{ active: form.days.includes(d.id) }"
            @click="toggleDay(d.id)"
            :disabled="saving"
          >{{ d.label }}</button>
          <span class="day-hint">不选 = 每天</span>
        </div>
      </div>

      <div class="setting-row">
        <label>失败后重试</label>
        <label class="toggle-switch">
          <input type="checkbox" v-model="form.retry_on_failure" @change="onSave">
          <span class="toggle-slider"></span>
        </label>
      </div>

      <div class="setting-row">
        <label>完成后动作</label>
        <select v-model="form.post_action" @change="onSave" :disabled="saving">
          <option value="nothing">什么都不做</option>
          <option value="kill_game">关闭游戏</option>
          <option value="exit_app">退出程序</option>
        </select>
      </div>
    </div>

    <!-- Status panel -->
    <div class="schedule-section" v-if="taskInfo.registered">
      <h3>任务状态</h3>
      <div class="info-row">
        <span class="info-label">状态</span>
        <span class="info-value" :class="statusClass">{{ taskInfo.status || '未知' }}</span>
      </div>
      <div class="info-row" v-if="taskInfo.next_run_time">
        <span class="info-label">下次运行</span>
        <span class="info-value">{{ taskInfo.next_run_time }}</span>
      </div>
      <div class="info-row" v-if="taskInfo.last_run_time">
        <span class="info-label">上次运行</span>
        <span class="info-value">{{ taskInfo.last_run_time }}</span>
      </div>
    </div>

    <!-- Save feedback -->
    <div v-if="saveMsg" class="save-msg" :class="{ error: saveError }">
      {{ saveMsg }}
    </div>

    <!-- History -->
    <div class="schedule-section" v-if="history.length > 0">
      <h3>执行记录</h3>
      <div class="history-list">
        <div
          v-for="(h, i) in history" :key="i"
          class="history-item"
          :class="h.result"
        >
          <span class="h-icon">{{ h.result === 'success' ? '✅' : '❌' }}</span>
          <span class="h-time">{{ formatTime(h.timestamp) }}</span>
          <span class="h-msg">{{ h.message }}</span>
          <span class="h-dur">{{ h.duration_s }}s</span>
          <span v-if="h.retried" class="h-retry">重试</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { api } from '../composables/useApi'

const allDays = [
  { id: 'mon', label: '一' },
  { id: 'tue', label: '二' },
  { id: 'wed', label: '三' },
  { id: 'thu', label: '四' },
  { id: 'fri', label: '五' },
  { id: 'sat', label: '六' },
  { id: 'sun', label: '日' },
]

const form = reactive({
  enabled: false,
  days: [],
  pipeline_id: 'daily_routine',
  retry_on_failure: false,
  post_action: 'nothing',
})

const hour = ref(4)
const minute = ref(0)
const saving = ref(false)
const saveMsg = ref('')
const saveError = ref(false)
const taskInfo = reactive({
  registered: false,
  enabled: false,
  next_run_time: '',
  last_run_time: '',
  last_result: 0,
  status: '',
})
const history = ref([])

const statusClass = computed(() => {
  const s = (taskInfo.status || '').toLowerCase()
  if (s === 'ready' || s === '就绪') return 'status-ready'
  if (s === 'running' || s === '正在运行') return 'status-running'
  if (s === 'disabled' || s === '已禁用') return 'status-disabled'
  return ''
})

function toggleDay(id) {
  const idx = form.days.indexOf(id)
  if (idx >= 0) {
    form.days.splice(idx, 1)
  } else {
    form.days.push(id)
  }
  onSave()
}

async function onSave() {
  saving.value = true
  saveMsg.value = ''
  try {
    const config = {
      enabled: form.enabled,
      time: `${String(hour.value).padStart(2, '0')}:${String(minute.value).padStart(2, '0')}`,
      days: [...form.days],
      pipeline_id: form.pipeline_id,
      retry_on_failure: form.retry_on_failure,
      post_action: form.post_action,
    }
    const result = await api.saveSchedule(config)
    if (result && result.ok) {
      saveMsg.value = result.message || '已保存'
      saveError.value = false
    } else {
      saveMsg.value = result?.error || result?.message || '保存失败'
      saveError.value = true
    }
    // Refresh status
    await loadSchedule()
  } catch (e) {
    saveMsg.value = '保存异常: ' + e.message
    saveError.value = true
  } finally {
    saving.value = false
    setTimeout(() => { saveMsg.value = '' }, 4000)
  }
}

async function loadSchedule() {
  const data = await api.getSchedule()
  if (!data) return

  if (data.config) {
    form.enabled = data.config.enabled || false
    form.days = data.config.days || []
    form.pipeline_id = data.config.pipeline_id || 'daily_routine'
    form.retry_on_failure = data.config.retry_on_failure || false
    form.post_action = data.config.post_action || 'nothing'

    if (data.config.time) {
      const parts = data.config.time.split(':')
      hour.value = parseInt(parts[0]) || 0
      minute.value = parseInt(parts[1]) || 0
    }
  }

  if (data.task) {
    Object.assign(taskInfo, data.task)
  }
}

async function loadHistory() {
  const records = await api.getScheduleHistory()
  if (records) history.value = records
}

function formatTime(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return `${d.getMonth()+1}/${d.getDate()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
  } catch { return iso }
}

onMounted(async () => {
  // Wait for pywebview
  if (typeof pywebview === 'undefined') {
    await new Promise(resolve => {
      window.addEventListener('pywebviewready', resolve, { once: true })
    })
  }
  await loadSchedule()
  await loadHistory()
})
</script>

<style scoped>
.schedule-view {
  padding: 24px 28px;
  overflow-y: auto;
  max-height: calc(100vh - 60px);
}

.schedule-section {
  margin-bottom: 28px;
}

.schedule-section h3 {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255,255,255,0.7);
  margin-bottom: 16px;
}

.section-desc {
  font-size: 12px;
  color: rgba(255,255,255,0.35);
  margin: -8px 0 16px;
}

.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255,255,255,0.03);
}

.setting-row label {
  font-size: 13px;
  color: rgba(255,255,255,0.6);
}

/* Time picker */
.time-picker {
  display: flex;
  align-items: center;
  gap: 4px;
}

.time-input {
  width: 48px;
  padding: 6px 8px;
  background: rgba(15, 12, 35, 0.95);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  color: #c8c8d0;
  font-size: 14px;
  text-align: center;
  font-family: inherit;
  -moz-appearance: textfield;
}

.time-input::-webkit-inner-spin-button,
.time-input::-webkit-outer-spin-button {
  -webkit-appearance: none;
}

.time-input:focus {
  outline: none;
  border-color: rgba(102,126,234,0.5);
}

.time-sep {
  color: rgba(255,255,255,0.4);
  font-size: 16px;
  font-weight: 700;
}

/* Day chips */
.day-chips {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
}

.day-chip {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.03);
  color: rgba(255,255,255,0.4);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.day-chip:hover {
  border-color: rgba(102,126,234,0.3);
  color: rgba(255,255,255,0.7);
}

.day-chip.active {
  background: rgba(102,126,234,0.15);
  border-color: rgba(102,126,234,0.5);
  color: #b8c4ff;
}

.day-hint {
  font-size: 11px;
  color: rgba(255,255,255,0.2);
  margin-left: 4px;
}

/* Toggle switch */
.toggle-switch {
  position: relative;
  width: 40px;
  height: 22px;
  display: inline-block;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background: rgba(255,255,255,0.08);
  border-radius: 22px;
  transition: 0.2s;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background: rgba(255,255,255,0.4);
  border-radius: 50%;
  transition: 0.2s;
}

.toggle-switch input:checked + .toggle-slider {
  background: linear-gradient(135deg, #667eea, #764ba2);
}

.toggle-switch input:checked + .toggle-slider::before {
  transform: translateX(18px);
  background: white;
}

/* Info rows */
.info-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255,255,255,0.03);
}

.info-label {
  font-size: 12px;
  color: rgba(255,255,255,0.4);
}

.info-value {
  font-size: 12px;
  color: rgba(255,255,255,0.7);
}

.status-ready { color: #66bb6a; }
.status-running { color: #42a5f5; }
.status-disabled { color: rgba(255,255,255,0.3); }

/* Save message */
.save-msg {
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 12px;
  background: rgba(102,126,234,0.1);
  color: #b8c4ff;
  margin-bottom: 20px;
}

.save-msg.error {
  background: rgba(244,67,54,0.1);
  color: #ef5350;
}

/* History */
.history-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  background: rgba(255,255,255,0.02);
  font-size: 12px;
}

.history-item.success {
  border-left: 3px solid rgba(102,187,106,0.5);
}

.history-item.failed {
  border-left: 3px solid rgba(239,83,80,0.5);
}

.h-icon { font-size: 14px; }
.h-time { color: rgba(255,255,255,0.4); min-width: 72px; }
.h-msg { color: rgba(255,255,255,0.6); flex: 1; }
.h-dur { color: rgba(255,255,255,0.3); }
.h-retry {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(245,158,11,0.15);
  color: #f5a623;
}
</style>
