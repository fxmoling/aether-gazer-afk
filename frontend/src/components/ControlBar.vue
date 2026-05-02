<template>
  <div class="control-bar">
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
      :disabled="autoBattleOn"
      class="script-select"
      @change="onScriptChange"
    >
      <option v-for="s in scripts" :key="s.id" :value="s.id">{{ s.name }}</option>
    </select>
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
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { state, startRun, stopRun } from '../composables/useStore'
import { api } from '../composables/useApi'

const autoBattleOn = ref(false)
const selectedScript = ref('default')
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
    selectedScript.value = settings.combat_script
  }
}

async function onScriptChange() {
  await api.setCombatScript(selectedScript.value)
}

async function toggleAutoBattle() {
  if (autoBattleOn.value) {
    await api.stopAutoBattle()
    autoBattleOn.value = false
  } else {
    const result = await api.startAutoBattle(selectedScript.value)
    if (result && result.ok) {
      autoBattleOn.value = true
      state.connected = true
    } else if (result) {
      alert(result.error || '启动失败')
    }
  }
}

async function pollStatus() {
  const s = await api.getAutoBattleStatus()
  if (s) autoBattleOn.value = s.enabled
}

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
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  background: rgba(255,255,255,0.015);
  border-top: 1px solid rgba(255,255,255,0.04);
}

.btn-start {
  flex: 1;
  max-width: 220px;
  padding: 12px 24px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border: none;
  border-radius: 12px;
  color: white;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  letter-spacing: 0.5px;
  box-shadow: 0 4px 20px rgba(102,126,234,0.35);
  transition: box-shadow 0.15s, transform 0.15s;
}

.btn-start:hover:not(:disabled) {
  box-shadow: 0 6px 28px rgba(102,126,234,0.5);
  transform: translateY(-1px);
}

.btn-start:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-stop {
  padding: 12px 20px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  color: rgba(255,255,255,0.25);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.1s, border-color 0.1s, color 0.1s;
}

.btn-stop:hover:not(:disabled) {
  background: rgba(244,67,54,0.08);
  border-color: rgba(244,67,54,0.3);
  color: #ef5350;
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
  color: rgba(255,255,255,0.3);
}

.btn-auto-battle {
  padding: 10px 18px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  color: rgba(255,255,255,0.4);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.btn-auto-battle:hover {
  background: rgba(245,158,11,0.08);
  border-color: rgba(245,158,11,0.3);
  color: #f5a623;
}

.btn-auto-battle.active {
  background: linear-gradient(135deg, rgba(245,158,11,0.15), rgba(239,108,0,0.15));
  border-color: rgba(245,158,11,0.5);
  color: #f5a623;
  box-shadow: 0 0 16px rgba(245,158,11,0.2);
}

.script-select {
  max-width: 130px;
  font-size: 12px;
}
</style>
