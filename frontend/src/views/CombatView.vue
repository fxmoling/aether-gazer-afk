<template>
  <div class="combat-view">
    <!-- Recording Overlay -->
    <Teleport to="body">
      <div v-if="recState !== 'idle'" class="rec-overlay">
        <div class="rec-overlay-content">
          <div v-if="recState === 'countdown'" class="rec-countdown">
            <div class="rec-countdown-num">{{ recCountdown }}</div>
            <div class="rec-countdown-label">{{ recSection === 'startup' ? '启动连招' : '循环连招' }}录制即将开始...</div>
            <button class="btn btn-secondary" @click="cancelRecord">取消</button>
          </div>
          <div v-else class="rec-active">
            <div class="rec-dot-row">
              <span class="rec-dot"></span>
              <span class="rec-label">录制中 · {{ recSection === 'startup' ? '启动连招' : '循环连招' }}</span>
            </div>
            <div class="rec-keys-display">
              <span
                v-for="k in recRecentKeys"
                :key="k.seq"
                class="rec-key-chip"
                :class="[k.holding ? 'rec-key-holding' : '', k.dur >= 0.25 ? 'rec-key-held' : '']"
              >{{ keyLabel(k.key) }}<span v-if="k.holding" class="rec-key-hold-icon">⏳</span><span v-else-if="k.dur >= 0.25" class="rec-key-dur">{{ k.dur }}s</span></span>
              <span v-if="!recRecentKeys.length" class="rec-hint">在游戏中操作，按键将被自动录制...</span>
            </div>
            <div class="rec-stats">
              <span>{{ recEventCount }} 次按键</span>
            </div>
            <div class="rec-controls">
              <button class="btn btn-danger" @click="stopRecording">⏹ 停止录制 (F11)</button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <div class="combat-layout">
      <!-- Left panel: script list -->
      <div class="script-list-panel">
        <div class="panel-header">
          <h3>连招脚本</h3>
          <button class="btn btn-primary btn-sm" @click="createNew">＋ 新建</button>
        </div>
        <div class="script-items">
          <div
            v-for="s in scripts"
            :key="s.id"
            class="script-item"
            :class="{ active: s.id === currentScriptId }"
            @click="loadScript(s.id)"
          >
            <span class="script-name">
              <span v-if="s.id === activeScript" class="star">⭐</span>
              {{ s.name || s.id }}
            </span>
            <div class="script-actions">
              <button
                v-if="s.id !== activeScript"
                class="btn-icon"
                title="设为当前"
                @click.stop="setActive(s.id)"
              >✓</button>
              <button
                v-if="s.id !== 'default'"
                class="btn-icon btn-icon-danger"
                title="删除"
                @click.stop="deleteScript(s.id)"
              >✕</button>
            </div>
          </div>
          <div v-if="!scripts.length" class="empty-hint">暂无脚本</div>
        </div>
      </div>

      <!-- Right panel: editor -->
      <div class="editor-panel">
        <div v-if="!editing" class="empty-editor">
          <span>← 选择或新建一个连招脚本</span>
        </div>
        <template v-else>
          <div class="editor-header">
            <div class="field-row">
              <label>名称</label>
              <input v-model="form.name" class="setting-input" placeholder="连招名称">
            </div>
            <div class="field-row">
              <label>描述</label>
              <input v-model="form.description" class="setting-input" placeholder="可选描述">
            </div>
            <div class="field-row">
              <label>全局间隔(秒)</label>
              <input v-model.number="form.interval" type="number" step="0.01" min="0" class="setting-input narrow">
            </div>
          </div>

          <!-- Startup section -->
          <div class="steps-section">
            <div class="section-header">
              <h3>启动连招 <span class="section-hint">(执行一次)</span></h3>
              <div class="section-btns">
                <button
                  class="btn btn-sm"
                  :class="recModeClass('startup')"
                  @click="startRecording('startup')"
                  :disabled="recState !== 'idle'"
                  :title="'录制启动连招 (F9)'"
                >
                  ⏺ 录制
                </button>
                <select v-model="recMode" class="rec-mode-select" title="录制模式">
                  <option value="replace">替换</option>
                  <option value="append">追加</option>
                </select>
              </div>
            </div>
            <StepList :steps="form.startup" @update="form.startup = $event" :keys="keyOptions" :globalInterval="form.interval" />
            <AddStepBtn @add="addStep('startup', $event)" />
          </div>

          <!-- Loop section -->
          <div class="steps-section">
            <div class="section-header">
              <h3>循环连招 <span class="section-hint">(反复执行)</span></h3>
              <div class="section-btns">
                <button
                  class="btn btn-sm"
                  :class="recModeClass('loop')"
                  @click="startRecording('loop')"
                  :disabled="recState !== 'idle'"
                  :title="'录制循环连招 (F9)'"
                >
                  ⏺ 录制
                </button>
              </div>
            </div>
            <StepList :steps="form.loop" @update="form.loop = $event" :keys="keyOptions" :globalInterval="form.interval" />
            <AddStepBtn @add="addStep('loop', $event)" />
          </div>

          <div class="editor-footer">
            <button class="btn btn-primary" @click="save">💾 保存</button>
            <button class="btn btn-secondary" @click="validate">✔ 验证</button>
            <button
              class="btn btn-secondary"
              @click="testPlayback"
              :disabled="testRunning"
              title="在游戏中测试当前连招"
            >{{ testRunning ? '▶ 测试中...' : '▶ 测试' }}</button>
            <span class="hotkey-hint">F9 录制 · F11 停止</span>
            <span v-if="statusMsg" class="status-msg" :class="statusClass">{{ statusMsg }}</span>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, defineComponent, h } from 'vue'
import { api } from '../composables/useApi'

// --- Key options ---
const keyOptions = [
  { value: 'j', label: 'J - 攻击' },
  { value: 'k', label: 'K - 模块' },
  { value: 'u', label: 'U - 技能1' },
  { value: 'i', label: 'I - 技能2' },
  { value: 'o', label: 'O - 技能3' },
  { value: 'r', label: 'R - 大招' },
  { value: '1', label: '1 - 连携1' },
  { value: '2', label: '2 - 连携2' },
  { value: 'space', label: 'Space - 闪避' },
  { value: 'w', label: 'W - 前进' },
  { value: 'a', label: 'A - 左移' },
  { value: 's', label: 'S - 后退' },
  { value: 'd', label: 'D - 右移' },
]

const keyLabelMap = {
  j: 'J', k: 'K', u: 'U', i: 'I', o: 'O', r: 'R',
  '1': '1', '2': '2', space: '空格',
  w: 'W', a: 'A', s: 'S', d: 'D',
}
function keyLabel(k) { return keyLabelMap[k] || k.toUpperCase() }

// --- State ---
const scripts = ref([])
const activeScript = ref('')
const currentScriptId = ref('')
const editing = ref(false)
const isNew = ref(false)
const statusMsg = ref('')
const statusClass = ref('')
const testRunning = ref(false)

// Recording state
const recState = ref('idle')            // idle | countdown | recording
const recSection = ref('loop')          // startup | loop
const recEventCount = ref(0)
const recCountdown = ref(0)
const recRecentKeys = ref([])
const recMode = ref('replace')          // replace | append
let recPollTimer = null

const form = reactive({
  name: '',
  description: '',
  interval: 0.12,
  startup: [],
  loop: [],
})

// Stash old steps for safe replace
let _stashedSteps = null

onMounted(async () => {
  await refreshList()
})

onUnmounted(() => {
  stopRecPoll()
})

// --- Script list ---
async function refreshList() {
  const list = await api.listCombatScripts()
  if (list && list.length > 0) scripts.value = list
  const settings = await api.getSettings()
  if (settings && settings.combat_script) activeScript.value = settings.combat_script
}

async function loadScript(id) {
  const result = await api.getCombatScript(id)
  if (!result || !result.ok) return
  currentScriptId.value = id
  isNew.value = false
  editing.value = true
  const s = result.script || {}
  form.name = s.name || id
  form.description = s.description || ''
  form.interval = s.interval ?? 0.12
  form.startup = (s.startup || []).map(parseStep)
  form.loop = (s.loop || []).map(parseStep)
}

function parseStep(raw) {
  if (raw.press != null) return { type: 'press', key: String(raw.press), interval: raw.interval ?? null }
  if (raw.hold != null) return { type: 'hold', key: String(raw.hold), duration: raw.duration ?? 0.3, interval: raw.interval ?? null }
  if (raw.wait != null) return { type: 'wait', duration: raw.wait, interval: null }
  return { type: 'press', key: 'j', interval: null }
}

function createNew() {
  currentScriptId.value = ''
  isNew.value = true
  editing.value = true
  form.name = ''
  form.description = ''
  form.interval = 0.12
  form.startup = []
  form.loop = [{ type: 'press', key: 'j', interval: null }]
}

function addStep(section, type) {
  const step = type === 'press' ? { type: 'press', key: 'j', interval: null }
    : type === 'hold' ? { type: 'hold', key: 'j', duration: 0.3, interval: null }
    : { type: 'wait', duration: 0.5, interval: null }
  form[section].push(step)
}

// --- YAML build ---
function buildYaml() {
  const lines = []
  lines.push(`name: ${form.name || '未命名'}`)
  if (form.description) lines.push(`description: ${form.description}`)
  if (form.interval != null && form.interval !== 0.12) lines.push(`interval: ${form.interval}`)
  if (form.startup.length) {
    lines.push('startup:')
    form.startup.forEach(s => lines.push(...stepToYaml(s)))
  }
  lines.push('loop:')
  form.loop.forEach(s => lines.push(...stepToYaml(s)))
  return lines.join('\n') + '\n'
}

function stepToYaml(s) {
  const lines = []
  const quoteKey = (k) => /^\d+$/.test(k) ? `"${k}"` : k
  if (s.type === 'press') {
    lines.push(`  - press: ${quoteKey(s.key)}`)
    if (s.interval != null && s.interval !== '') lines.push(`    interval: ${s.interval}`)
  } else if (s.type === 'hold') {
    lines.push(`  - hold: ${quoteKey(s.key)}`)
    lines.push(`    duration: ${s.duration}`)
    if (s.interval != null && s.interval !== '') lines.push(`    interval: ${s.interval}`)
  } else {
    lines.push(`  - wait: ${s.duration}`)
  }
  return lines
}

// --- Save / Validate ---
async function save() {
  const yaml = buildYaml()
  const id = isNew.value ? toId(form.name || 'custom') : currentScriptId.value
  const result = await api.saveCombatScript(id, yaml)
  if (result && result.ok) {
    statusMsg.value = '✔ 已保存'
    statusClass.value = 'ok'
    currentScriptId.value = id
    isNew.value = false
    await refreshList()
  } else {
    statusMsg.value = '保存失败: ' + (result?.error || '未知错误')
    statusClass.value = 'err'
  }
  clearStatus()
}

async function validate() {
  const yaml = buildYaml()
  const result = await api.validateCombatScript(yaml)
  if (result && result.ok) {
    statusMsg.value = `✔ 格式正确 (启动${result.startup_count}步 + 循环${result.loop_count}步)`
    statusClass.value = 'ok'
  } else {
    statusMsg.value = '✘ ' + (result?.error || '验证失败')
    statusClass.value = 'err'
  }
  clearStatus()
}

async function setActive(id) {
  const result = await api.setCombatScript(id)
  if (result && result.ok) {
    activeScript.value = id
    await refreshList()
  }
}

async function deleteScript(id) {
  if (id === 'default') return
  const result = await api.deleteCombatScript(id)
  if (result && result.ok) {
    if (currentScriptId.value === id) {
      editing.value = false
      currentScriptId.value = ''
    }
    await refreshList()
  }
}

function toId(name) {
  return name.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, '_').replace(/^_|_$/g, '') || 'custom'
}

function clearStatus() {
  setTimeout(() => { statusMsg.value = '' }, 4000)
}

// --- Recording ---

function recModeClass(section) {
  return 'btn-accent'
}

async function startRecording(section) {
  if (recState.value !== 'idle') return
  recSection.value = section
  recRecentKeys.value = []
  recEventCount.value = 0

  // Stash current steps for safe replace (restore on cancel/empty)
  if (recMode.value === 'replace') {
    _stashedSteps = [...form[section]]
  }

  const result = await api.startComboRecording(section, 3)
  if (result && result.ok) {
    recState.value = 'countdown'
    recCountdown.value = 3
    startRecPoll()
  }
}

async function stopRecording() {
  if (recState.value === 'idle') return
  const section = recSection.value
  const result = await api.stopComboRecording()
  recState.value = 'idle'
  stopRecPoll()

  if (result && result.ok && result.steps && result.steps.length) {
    const parsed = result.steps.map(parseStep)
    if (recMode.value === 'replace') {
      form[section] = parsed
    } else {
      form[section] = [...form[section], ...parsed]
    }
    _stashedSteps = null
    statusMsg.value = `✔ 录制完成: ${result.count} 步${recMode.value === 'replace' ? '已替换' : '已追加'}到${section === 'startup' ? '启动' : '循环'}连招`
    statusClass.value = 'ok'
    clearStatus()
  } else {
    // No steps captured — restore stash if in replace mode
    if (recMode.value === 'replace' && _stashedSteps) {
      form[section] = _stashedSteps
    }
    _stashedSteps = null
    statusMsg.value = '录制完成但未捕获到按键'
    statusClass.value = 'warn'
    clearStatus()
  }
}

function cancelRecord() {
  // Cancel during countdown — restore stash
  api.stopComboRecording()
  recState.value = 'idle'
  stopRecPoll()
  if (recMode.value === 'replace' && _stashedSteps) {
    form[recSection.value] = _stashedSteps
  }
  _stashedSteps = null
}

function startRecPoll() {
  stopRecPoll()
  recPollTimer = setInterval(async () => {
    const s = await api.getComboRecorderStatus()
    if (!s) return
    recState.value = s.state
    recEventCount.value = s.event_count
    recCountdown.value = s.countdown_remaining || 0
    recRecentKeys.value = s.recent_keys || []

    // Auto-consume hotkey-initiated stop results
    if (s.state === 'idle' && s.has_result && recState.value !== 'idle') {
      recState.value = 'idle'
    }
    if (s.has_result && s.state === 'idle') {
      const result = await api.consumeComboResult()
      if (result && result.ok) {
        stopRecPoll()
        const section = result.section || recSection.value
        const parsed = (result.steps || []).map(parseStep)
        if (parsed.length) {
          if (recMode.value === 'replace') {
            form[section] = parsed
          } else {
            form[section] = [...form[section], ...parsed]
          }
          _stashedSteps = null
          statusMsg.value = `✔ 录制完成: ${result.count} 步`
          statusClass.value = 'ok'
        } else {
          if (recMode.value === 'replace' && _stashedSteps) {
            form[section] = _stashedSteps
          }
          _stashedSteps = null
          statusMsg.value = '录制完成但未捕获到按键'
          statusClass.value = 'warn'
        }
        clearStatus()
        recState.value = 'idle'
      }
    }
  }, 250)
}

function stopRecPoll() {
  if (recPollTimer) {
    clearInterval(recPollTimer)
    recPollTimer = null
  }
}

// --- Test playback ---
async function testPlayback() {
  if (testRunning.value) return
  const steps = form.loop.map(s => {
    if (s.type === 'press') {
      const d = { press: s.key }
      if (s.interval != null) d.interval = s.interval
      return d
    }
    if (s.type === 'hold') {
      const d = { hold: s.key, duration: s.duration }
      if (s.interval != null) d.interval = s.interval
      return d
    }
    return { wait: s.duration }
  })
  if (!steps.length) {
    statusMsg.value = '没有可测试的步骤'
    statusClass.value = 'warn'
    clearStatus()
    return
  }
  testRunning.value = true
  statusMsg.value = '▶ 正在测试连招...'
  statusClass.value = 'ok'
  try {
    const result = await api.testComboPlayback(steps, 1)
    if (result && result.ok) {
      statusMsg.value = `✔ 测试完成: 播放了 ${result.steps_played} 步`
      statusClass.value = 'ok'
    } else {
      statusMsg.value = '✘ 测试失败: ' + (result?.error || '未知错误')
      statusClass.value = 'err'
    }
  } catch (e) {
    statusMsg.value = '✘ 测试异常: ' + e.message
    statusClass.value = 'err'
  } finally {
    testRunning.value = false
    clearStatus()
  }
}

// --- Inline child components ---

const StepList = defineComponent({
  props: {
    steps: Array,
    keys: Array,
    globalInterval: { type: Number, default: 0.12 },
  },
  emits: ['update'],
  setup(props, { emit }) {
    function move(idx, dir) {
      const arr = [...props.steps]
      const target = idx + dir
      if (target < 0 || target >= arr.length) return
      ;[arr[idx], arr[target]] = [arr[target], arr[idx]]
      emit('update', arr)
    }
    function remove(idx) {
      const arr = [...props.steps]
      arr.splice(idx, 1)
      emit('update', arr)
    }
    function updateField(idx, field, value) {
      const arr = [...props.steps]
      arr[idx] = { ...arr[idx], [field]: value }
      emit('update', arr)
    }

    return () => {
      if (!props.steps.length) {
        return h('div', { class: 'empty-steps' }, '暂无步骤，点击下方添加或使用录制功能')
      }
      return h('div', { class: 'step-list' }, props.steps.map((step, idx) => {
        const typeLabel = step.type === 'press' ? '⚡ 按键' : step.type === 'hold' ? '⏳ 长按' : '💤 等待'
        const children = [
          h('span', { class: 'step-num' }, `${idx + 1}`),
          h('span', { class: `step-badge step-badge-${step.type}` }, typeLabel),
        ]
        if (step.type === 'press' || step.type === 'hold') {
          children.push(
            h('select', {
              class: 'step-select',
              value: step.key,
              onChange: (e) => updateField(idx, 'key', e.target.value),
            }, props.keys.map(k =>
              h('option', { value: k.value, selected: k.value === step.key }, k.label)
            ))
          )
        }
        if (step.type === 'hold') {
          children.push(
            h('span', { class: 'step-field' }, [
              h('span', { class: 'step-label' }, '时长'),
              h('input', {
                type: 'number', class: 'step-input', value: step.duration,
                step: '0.1', min: '0.1',
                onInput: (e) => updateField(idx, 'duration', parseFloat(e.target.value) || 0.3),
              }),
              h('span', { class: 'step-unit' }, 's'),
            ]),
          )
        }
        if (step.type === 'wait') {
          children.push(
            h('span', { class: 'step-field' }, [
              h('span', { class: 'step-label' }, '等待'),
              h('input', {
                type: 'number', class: 'step-input', value: step.duration,
                step: '0.1', min: '0.1',
                onInput: (e) => updateField(idx, 'duration', parseFloat(e.target.value) || 0.5),
              }),
              h('span', { class: 'step-unit' }, 's'),
            ]),
          )
        }
        if (step.type !== 'wait') {
          const displayInterval = step.interval != null ? step.interval : props.globalInterval
          children.push(
            h('span', { class: 'step-field' }, [
              h('span', { class: 'step-label' }, '间隔'),
              h('input', {
                type: 'number', class: 'step-input', value: displayInterval,
                step: '0.01', min: '0',
                onInput: (e) => updateField(idx, 'interval', e.target.value === '' ? null : parseFloat(e.target.value)),
              }),
              h('span', { class: 'step-unit' }, 's'),
            ]),
          )
        }
        children.push(
          h('div', { class: 'step-btns' }, [
            h('button', {
              class: 'step-btn step-btn-move', onClick: () => move(idx, -1),
              disabled: idx === 0, title: '上移',
            }, '▲'),
            h('button', {
              class: 'step-btn step-btn-move', onClick: () => move(idx, 1),
              disabled: idx === props.steps.length - 1, title: '下移',
            }, '▼'),
            h('button', {
              class: 'step-btn step-btn-del', onClick: () => remove(idx),
              title: '删除此步骤',
            }, '🗑'),
          ])
        )
        return h('div', { class: `step-row step-row-${step.type}`, key: idx }, children)
      }))
    }
  },
})

const AddStepBtn = defineComponent({
  emits: ['add'],
  setup(_, { emit }) {
    return () => h('div', { class: 'add-step-row' }, [
      h('button', { class: 'add-step-btn', onClick: () => emit('add', 'press') }, '⚡ 按键'),
      h('button', { class: 'add-step-btn', onClick: () => emit('add', 'hold') }, '⏳ 长按'),
      h('button', { class: 'add-step-btn', onClick: () => emit('add', 'wait') }, '💤 等待'),
    ])
  },
})
</script>

<style scoped>
.combat-view {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.combat-layout {
  display: flex;
  gap: 20px;
  height: 100%;
  min-height: 0;
}

/* Left panel */
.script-list-panel {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 14px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.panel-header h3 {
  font-size: 15px;
  color: var(--accent-text);
  margin: 0;
}

.script-items {
  flex: 1;
  overflow-y: auto;
}

.script-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 13px;
  transition: background 0.15s;
}

.script-item:hover {
  background: var(--bg-surface-hover);
}

.script-item.active {
  background: var(--accent-tint-hover);
  color: var(--accent-text);
}

.script-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.star { margin-right: 4px; }

.script-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.empty-hint {
  color: var(--text-muted);
  font-size: 12px;
  text-align: center;
  padding: 20px 0;
}

/* Right panel */
.editor-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 18px;
  overflow-y: auto;
}

.empty-editor {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--text-muted);
  font-size: 14px;
  gap: 8px;
  opacity: 0.6;
}

.editor-header {
  margin-bottom: 18px;
  padding: 14px 16px;
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
}

.field-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.field-row label {
  width: 100px;
  color: var(--text-muted);
  font-size: 13px;
  flex-shrink: 0;
}

.field-row .setting-input {
  flex: 1;
  max-width: 300px;
  padding: 6px 10px;
  background: var(--bg-input);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: 13px;
}

.field-row .setting-input:focus {
  outline: none;
  border-color: var(--border-focus);
}

.field-row .narrow {
  max-width: 100px;
}

/* Sections */
.steps-section {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border-separator);
}

.section-header h3 {
  font-size: 14px;
  color: var(--accent-text);
  margin: 0;
}

.steps-section h3 {
  font-size: 14px;
  color: var(--accent-text);
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border-separator);
}

.section-hint {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: normal;
}

/* ── Child component styles (StepList / AddStepBtn use h() render) ──
   Vue scoped CSS doesn't penetrate child components — use :deep() */

.steps-section :deep(.step-list) {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;
  padding-right: 4px;
}

.steps-section :deep(.step-row) {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  transition: border-color 0.15s, box-shadow 0.15s, background 0.15s;
}

.steps-section :deep(.step-row:hover) {
  border-color: var(--border-hover);
  box-shadow: var(--shadow-sm);
  background: var(--bg-surface-hover);
}

.steps-section :deep(.step-num) {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
  min-width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: var(--bg-surface-hover);
  border-radius: var(--radius-sm);
  opacity: 0.7;
}

/* Badges — theme-aware with semantic colors */
.steps-section :deep(.step-badge) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
  min-width: 64px;
  text-align: center;
  letter-spacing: 0.3px;
  border: 1px solid transparent;
}

.steps-section :deep(.step-badge-press) {
  background: var(--accent-tint-hover);
  color: var(--accent-text);
  border-color: var(--accent-border);
}

.steps-section :deep(.step-badge-hold) {
  background: var(--status-warning-bg);
  color: var(--status-warning-text);
  border-color: rgba(255, 152, 0, 0.2);
}

.steps-section :deep(.step-badge-wait) {
  background: var(--bg-surface-hover);
  color: var(--text-muted);
  border-color: var(--border-default);
}

/* Step select dropdown */
.steps-section :deep(.step-select) {
  width: 140px;
  flex-shrink: 0;
  font-size: 12px;
  appearance: none;
  -webkit-appearance: none;
  background-color: var(--select-bg);
  color: var(--select-text);
  border: 1px solid var(--select-border);
  border-radius: var(--radius-md);
  padding: 6px 28px 6px 10px;
  font-family: inherit;
  cursor: pointer;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%23888'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  background-size: 10px 6px;
  transition: border-color 0.15s;
}

.steps-section :deep(.step-select:hover) {
  border-color: var(--border-hover);
}

.steps-section :deep(.step-select:focus) {
  outline: none;
  border-color: var(--border-focus);
}

.steps-section :deep(.step-select option) {
  background: var(--select-option-bg);
  color: var(--select-text);
}

.steps-section :deep(.step-field) {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-shrink: 0;
}

.steps-section :deep(.step-label) {
  color: var(--text-muted);
  font-size: 11px;
  flex-shrink: 0;
}

.steps-section :deep(.step-input) {
  width: 64px;
  padding: 5px 6px;
  background: var(--bg-input);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: 12px;
  flex-shrink: 0;
  text-align: center;
  transition: border-color 0.15s;
  font-family: inherit;
}

.steps-section :deep(.step-input:focus) {
  outline: none;
  border-color: var(--border-focus);
}

.steps-section :deep(.step-unit) {
  color: var(--text-muted);
  font-size: 11px;
  opacity: 0.6;
}

.steps-section :deep(.step-btns) {
  display: flex;
  gap: 4px;
  margin-left: auto;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.15s;
}

.steps-section :deep(.step-row:hover .step-btns) {
  opacity: 1;
}

.steps-section :deep(.step-btn) {
  background: var(--btn-secondary-bg);
  border: 1px solid var(--border-default);
  width: 28px;
  height: 28px;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  padding: 0;
}

.steps-section :deep(.step-btn-move) {
  color: var(--text-muted);
}

.steps-section :deep(.step-btn-move:hover:not(:disabled)) {
  background: var(--accent-tint-hover);
  border-color: var(--accent-border);
  color: var(--accent-text);
}

.steps-section :deep(.step-btn-move:disabled) {
  opacity: 0.2;
  cursor: not-allowed;
}

.steps-section :deep(.step-btn-del) {
  color: var(--text-muted);
}

.steps-section :deep(.step-btn-del:hover) {
  background: var(--status-error-bg);
  border-color: var(--btn-danger-hover-border);
  color: var(--status-error-text);
}

.steps-section :deep(.empty-steps) {
  color: var(--text-muted);
  font-size: 12px;
  padding: 16px;
  text-align: center;
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-lg);
}

/* Icon buttons (left panel actions) */
.btn-icon {
  background: var(--btn-secondary-bg);
  border: 1px solid var(--border-default);
  color: var(--text-muted);
  width: 26px;
  height: 26px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  padding: 0;
}

.btn-icon:hover:not(:disabled) {
  background: var(--accent-tint-hover);
  border-color: var(--accent-border);
  color: var(--accent-text);
}

.btn-icon:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.btn-icon-danger:hover:not(:disabled) {
  background: var(--status-error-bg);
  border-color: var(--btn-danger-hover-border);
  color: var(--status-error-text);
}

.btn-sm {
  padding: 4px 12px;
  font-size: 12px;
}

/* Add step — horizontal inline buttons (child component, needs :deep()) */
.steps-section :deep(.add-step-row) {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.steps-section :deep(.add-step-btn) {
  padding: 6px 14px;
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-muted);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.steps-section :deep(.add-step-btn:hover) {
  background: var(--accent-tint-hover);
  border-color: var(--accent-border);
  color: var(--accent-text);
  border-style: solid;
}

/* Footer */
.editor-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 20px;
  padding-top: 14px;
  border-top: 1px solid var(--border-separator);
}

.status-msg {
  font-size: 13px;
}

.status-msg.ok { color: var(--status-success-text); }
.status-msg.err { color: var(--status-error-text); }
.status-msg.warn { color: var(--accent-text); }

/* Recording */
.btn-sm {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: var(--radius-md);
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s;
  white-space: nowrap;
}

.btn-accent {
  background: var(--accent-tint);
  color: var(--accent-text);
  border-color: var(--accent-tint-hover);
}

.btn-accent:hover:not(:disabled) {
  background: var(--accent-tint-hover);
}

.btn-accent:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-danger {
  background: rgba(239, 83, 80, 0.12);
  color: #ef5350;
  border-color: rgba(239, 83, 80, 0.25);
  animation: rec-pulse 1s infinite;
}

.btn-danger:hover {
  background: rgba(239, 83, 80, 0.2);
}

@keyframes rec-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.hotkey-hint {
  font-size: 10px;
  color: var(--text-muted);
  margin-left: auto;
  font-family: 'Consolas', monospace;
  opacity: 0.6;
}

/* Section header buttons */
.section-btns {
  display: flex;
  align-items: center;
  gap: 6px;
}

.rec-mode-select {
  font-size: 10px;
  padding: 3px 6px;
  background: var(--bg-input);
  color: var(--text-muted);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

/* Recording overlay */
.rec-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.rec-overlay-content {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 16px;
  padding: 32px 40px;
  min-width: 400px;
  max-width: 540px;
  text-align: center;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.5);
}

/* Countdown */
.rec-countdown {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.rec-countdown-num {
  font-size: 64px;
  font-weight: 800;
  color: var(--accent-text);
  line-height: 1;
  animation: countPulse 1s ease infinite;
}

@keyframes countPulse {
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.1); opacity: 0.8; }
  100% { transform: scale(1); opacity: 1; }
}

.rec-countdown-label {
  color: var(--text-muted);
  font-size: 14px;
}

/* Active recording */
.rec-active {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.rec-dot-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.rec-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #ef5350;
  animation: dotBlink 1s infinite;
}

@keyframes dotBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}

.rec-label {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.rec-keys-display {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: center;
  min-height: 36px;
  padding: 8px;
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  width: 100%;
}

.rec-key-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  min-width: 32px;
  height: 28px;
  padding: 0 8px;
  background: var(--accent-tint);
  color: var(--accent-text);
  border: 1px solid var(--accent-border);
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
  font-family: 'Consolas', monospace;
  animation: chipPop 0.15s ease;
}

.rec-key-holding {
  background: rgba(255, 152, 0, 0.2);
  color: #ff9800;
  border-color: rgba(255, 152, 0, 0.4);
  animation: holdPulse 0.6s ease infinite;
}

.rec-key-held {
  background: var(--status-warning-bg);
  color: var(--status-warning-text);
  border-color: rgba(255, 152, 0, 0.3);
}

.rec-key-hold-icon {
  font-size: 10px;
}

.rec-key-dur {
  font-size: 9px;
  opacity: 0.7;
}

@keyframes chipPop {
  from { transform: scale(0.8); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

@keyframes holdPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.08); }
}

.rec-hint {
  color: var(--text-muted);
  font-size: 12px;
  line-height: 28px;
}

.rec-stats {
  font-size: 13px;
  color: var(--text-muted);
}

.rec-controls {
  display: flex;
  gap: 10px;
}

.rec-controls .btn {
  padding: 8px 20px;
  font-size: 13px;
}
</style>
