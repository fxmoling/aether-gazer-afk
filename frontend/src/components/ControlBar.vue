<template>
  <div class="control-bar">
    <div class="control-row">
      <button
        class="btn-start"
        :disabled="state.running"
        @click="handleStart"
      >
        ▶ 开始运行
      </button>
      <button
        class="btn-stop"
        :disabled="!state.running"
        @click="handleStop"
      >
        ■ 停止
      </button>
    <button
      class="btn-auto-battle"
      :class="{ active: autoBattleOn }"
      @click="toggleAutoBattle"
    >
      ⚔️ {{ autoBattleOn ? '自动战斗中' : '自动战斗' }}
    </button>
    <select
      v-model="selectedScript"
      class="script-select"
      @change="onScriptChange"
      @focus="refreshScripts"
    >
      <option v-for="s in scripts" :key="s.id" :value="s.id">{{ s.name }}</option>
    </select>
    <span v-if="autoBattleOn && activeScriptName" class="active-script-hint">
      ▸ {{ activeScriptName }}
    </span>
    <div class="control-info">
      <svg v-if="state.totalCount > 0" class="progress-ring" width="40" height="40" viewBox="0 0 40 40">
        <circle cx="20" cy="20" r="16" fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="3"/>
        <circle cx="20" cy="20" r="16" fill="none" stroke="url(#ringGrad)" stroke-width="3" stroke-linecap="round"
          :stroke-dasharray="circumference"
          :stroke-dashoffset="dashOffset"
          transform="rotate(-90 20 20)"/>
        <defs>
          <linearGradient id="ringGrad">
            <stop offset="0%" stop-color="#667eea"/>
            <stop offset="100%" stop-color="#764ba2"/>
          </linearGradient>
        </defs>
        <text x="20" y="22" text-anchor="middle" fill="#c8c8d0" font-size="9" font-weight="600">{{ progressPct }}%</text>
      </svg>
      <span v-if="state.running" class="run-time">{{ runTimeText }}</span>
    </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { state, startRun, stopRun } from '../composables/useStore'
import { api } from '../composables/useApi'

const autoBattleOn = ref(false)
const selectedScript = ref('default')
const activeScriptName = ref('')
const scripts = ref([{ id: 'default', name: '默认连招' }])
let pollTimer = null

async function loadScripts() {
  // pywebview may not be ready on first mount, retry a few times
  for (let i = 0; i < 5; i++) {
    const list = await api.listCombatScripts()
    if (list && list.length > 0) {
      scripts.value = list
      break
    }
    await new Promise(r => setTimeout(r, 500))
  }
  // Load saved script selection from user config
  const settings = await api.getSettings()
  if (settings && settings.combat_script) {
    // Verify the saved script exists in the list
    const exists = scripts.value.some(s => s.id === settings.combat_script)
    selectedScript.value = exists ? settings.combat_script : 'default'
  }
  // Persist default if user never picked one
  if (!settings?.combat_script || selectedScript.value === 'default') {
    await api.setCombatScript(selectedScript.value)
  }
}

function scriptDisplayName(id) {
  const s = scripts.value.find(s => s.id === id)
  return s ? s.name : id
}

async function refreshScripts() {
  const list = await api.listCombatScripts()
  if (list && list.length > 0) {
    scripts.value = list
  }
}

async function onScriptChange() {
  // Save to config for future sessions
  await api.setCombatScript(selectedScript.value)
  // If auto-battle is running, hot-swap immediately
  if (autoBattleOn.value) {
    const result = await api.swapAutoBattleScript(selectedScript.value)
    if (result && result.ok) {
      activeScriptName.value = scriptDisplayName(selectedScript.value)
    }
  }
}

async function toggleAutoBattle() {
  if (autoBattleOn.value) {
    await api.stopAutoBattle()
    autoBattleOn.value = false
    activeScriptName.value = ''
  } else {
    const result = await api.startAutoBattle(selectedScript.value)
    if (result && result.ok) {
      autoBattleOn.value = true
      activeScriptName.value = scriptDisplayName(result.script || selectedScript.value)
      state.connected = true
    } else if (result) {
      alert(result.error || '启动失败')
    }
  }
}

async function pollStatus() {
  const s = await api.getAutoBattleStatus()
  if (s) {
    autoBattleOn.value = s.enabled
    if (s.enabled && s.script) {
      activeScriptName.value = scriptDisplayName(s.script)
    } else if (!s.enabled) {
      activeScriptName.value = ''
    }
  }
}

async function loadPostRunAction() {}

onMounted(() => {
  loadScripts()
  pollTimer = setInterval(pollStatus, 3000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

const circumference = computed(() => 2 * Math.PI * 16)

const progressPct = computed(() => {
  if (!state.totalCount) return 0
  return Math.round((state.completedCount / state.totalCount) * 100)
})

const dashOffset = computed(() => {
  const pct = state.totalCount ? state.completedCount / state.totalCount : 0
  return circumference.value * (1 - pct)
})

const runTimeText = computed(() => {
  const min = Math.floor(state.elapsedS / 60)
  const sec = Math.floor(state.elapsedS % 60)
  return `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
})

async function handleStart() {
  const result = await startRun()
  if (!result.ok) {
    alert(result.error || '启动失败')
  }
}

async function handleStop() {
  await stopRun()
}
</script>

<style scoped>
.control-bar {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 20px;
  background: var(--bg-surface);
  border-top: 1px solid var(--border-subtle);
}

.control-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-start {
  flex: 1;
  max-width: 220px;
  padding: 12px 24px;
  background: var(--btn-primary-bg);
  border: none;
  border-radius: var(--radius-lg);
  color: var(--text-on-accent);
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  letter-spacing: 0.5px;
  box-shadow: 0 4px 20px var(--accent-border-strong);
  transition: box-shadow 0.15s, transform 0.15s;
}

.btn-start:hover:not(:disabled) {
  box-shadow: 0 6px 28px var(--border-focus);
  transform: translateY(-1px);
}

.btn-start:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-stop {
  padding: 12px 20px;
  background: var(--btn-secondary-bg);
  border: 1px solid var(--btn-secondary-border);
  border-radius: var(--radius-lg);
  color: var(--text-muted);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.1s, border-color 0.1s, color 0.1s;
}

.btn-stop:hover:not(:disabled) {
  background: var(--btn-danger-hover-bg);
  border-color: var(--btn-danger-hover-border);
  color: var(--btn-danger-text);
}

.btn-stop:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.control-info {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
}

.run-time {
  font-size: 12px;
  color: var(--text-muted);
}

.btn-auto-battle {
  padding: 10px 18px;
  background: var(--btn-secondary-bg);
  border: 1px solid var(--btn-secondary-border);
  border-radius: var(--radius-lg);
  color: var(--text-muted);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.btn-auto-battle:hover {
  background: var(--autobattle-active-bg);
  border-color: var(--autobattle-active-border);
  color: var(--autobattle-active-text);
}

.btn-auto-battle.active {
  background: var(--autobattle-active-bg);
  border-color: var(--autobattle-active-border);
  color: var(--autobattle-active-text);
  box-shadow: var(--autobattle-active-glow);
}

.script-select {
  max-width: 130px;
  font-size: 12px;
}

.active-script-hint {
  font-size: 11px;
  color: var(--autobattle-active-text);
  white-space: nowrap;
}
</style>
