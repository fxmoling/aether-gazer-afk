<template>
  <div class="combat-view">
    <div class="combat-layout">
      <!-- Left panel: script list -->
      <div class="script-list-panel">
        <div class="panel-header">
          <h3>连招脚本</h3>
          <button class="btn btn-primary btn-sm" @click="createNew">＋ 新建连招</button>
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
            <h3>启动连招 <span class="section-hint">(执行一次)</span></h3>
            <StepList :steps="form.startup" @update="form.startup = $event" :keys="keyOptions" :globalInterval="form.interval" />
            <AddStepBtn @add="addStep('startup', $event)" />
          </div>

          <!-- Loop section -->
          <div class="steps-section">
            <h3>循环连招 <span class="section-hint">(反复执行)</span></h3>
            <StepList :steps="form.loop" @update="form.loop = $event" :keys="keyOptions" :globalInterval="form.interval" />
            <AddStepBtn @add="addStep('loop', $event)" />
          </div>

          <div class="editor-footer">
            <button class="btn btn-primary" @click="save">💾 保存</button>
            <button class="btn btn-secondary" @click="validate">✔ 验证</button>
            <span v-if="statusMsg" class="status-msg" :class="statusClass">{{ statusMsg }}</span>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, defineComponent, h } from 'vue'
import { api } from '../composables/useApi'

const keyOptions = [
  { value: 'j', label: 'J - 攻击' },
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

const scripts = ref([])
const activeScript = ref('')
const currentScriptId = ref('')
const editing = ref(false)
const isNew = ref(false)
const statusMsg = ref('')
const statusClass = ref('')

const form = reactive({
  name: '',
  description: '',
  interval: 0.12,
  startup: [],
  loop: [],
})

onMounted(async () => {
  await refreshList()
})

async function refreshList() {
  const list = await api.listCombatScripts()
  if (list && list.length > 0) {
    scripts.value = list
  }
  const settings = await api.getSettings()
  if (settings && settings.combat_script) {
    activeScript.value = settings.combat_script
  }
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

// Inline child components

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
        return h('div', { class: 'empty-steps' }, '暂无步骤，点击下方添加')
      }

      return h('div', { class: 'step-list' }, props.steps.map((step, idx) => {
        const typeLabel = step.type === 'press' ? '⚡ 按键' : step.type === 'hold' ? '⏳ 长按' : '💤 等待'

        const children = [
          // Step number
          h('span', { class: 'step-num' }, `${idx + 1}`),
          // Type badge — uses CSS class for theme-aware coloring
          h('span', {
            class: `step-badge step-badge-${step.type}`,
          }, typeLabel),
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
                type: 'number',
                class: 'step-input',
                value: step.duration,
                step: '0.1',
                min: '0.1',
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
                type: 'number',
                class: 'step-input',
                value: step.duration,
                step: '0.1',
                min: '0.1',
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
                type: 'number',
                class: 'step-input',
                value: displayInterval,
                step: '0.01',
                min: '0',
                onInput: (e) => updateField(idx, 'interval', e.target.value === '' ? null : parseFloat(e.target.value)),
              }),
              h('span', { class: 'step-unit' }, 's'),
            ]),
          )
        }

        // Move up / Move down / Delete
        children.push(
          h('div', { class: 'step-btns' }, [
            h('button', {
              class: 'step-btn step-btn-move',
              onClick: () => move(idx, -1),
              disabled: idx === 0,
              title: '上移',
            }, '▲'),
            h('button', {
              class: 'step-btn step-btn-move',
              onClick: () => move(idx, 1),
              disabled: idx === props.steps.length - 1,
              title: '下移',
            }, '▼'),
            h('button', {
              class: 'step-btn step-btn-del',
              onClick: () => remove(idx),
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
</style>
