<template>
  <div class="tasks-view">
    <ConnectionBar />

    <!-- Pipeline selector -->
    <div class="pipeline-bar">
      <label>流程</label>
      <div class="pipeline-chips">
        <button
          v-for="p in state.pipelines"
          :key="p.id"
          class="pipeline-chip"
          :class="{ active: state.selectedPipelineId === p.id }"
          @click="selectPipeline(p.id)"
        >{{ p.name }}</button>
      </div>
    </div>

    <!-- Pipeline description -->
    <div v-if="selectedPipeline" class="pipeline-desc">
      {{ selectedPipeline.description }}
    </div>

    <!-- Usage tips banner (content varies by pipeline) -->
    <div class="tips-banner" v-if="showTips && currentTips.length">
      <div class="tips-header">
        <div class="tips-header-left">
          <span class="tips-icon">⚠️</span>
          <span class="tips-title">使用须知</span>
        </div>
        <button class="tips-close" @click="dismissTips">收起 ▲</button>
      </div>
      <div class="tips-items">
        <div class="tips-item" v-for="(tip, i) in currentTips" :key="i">
          <span class="tips-emoji">{{ tip.icon }}</span>
          <span class="tips-text" v-html="tip.text"></span>
        </div>
      </div>
    </div>
    <div class="tips-collapsed" v-else-if="currentTips.length" @click="showTips = true; saveTips()">
      <span class="tips-icon">⚠️</span> 使用须知（点击展开）
    </div>

    <!-- Progress section -->
    <div class="progress-section" v-if="totalCount > 0">
      <div class="progress-header">
        <span class="progress-title">任务设置</span>
        <span class="progress-count">{{ completedCount }} / {{ totalCount }}</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: progressPct + '%' }"></div>
      </div>
    </div>

    <!-- Section header for processes without sub-tasks -->
    <div class="progress-section" v-else-if="selectedPipeline">
      <div class="progress-header">
        <span class="progress-title">任务设置</span>
        <span class="progress-count" style="color: rgba(102,126,234,0.7)">无限循环</span>
      </div>
    </div>

    <TaskList :tasks="currentTasks" />

    <!-- Duowei-specific settings -->
    <div class="duowei-settings" v-if="state.selectedPipelineId === 'duowei_challenge'">
      <div class="duowei-setting-row">
        <label>游戏帧率</label>
        <div class="fps-chips">
          <button
            v-for="fp in fpsPresets" :key="fp.fps"
            class="fps-chip"
            :class="{ active: selectedFps === fp.fps }"
            @click="selectFps(fp)"
          >{{ fp.label }}</button>
        </div>
      </div>
      <div class="duowei-setting-row">
        <label>视角旋转幅度</label>
        <input
          type="range"
          min="0.1" max="2.0" step="0.1"
          v-model.number="swipeMultiplier"
          @change="saveSwipeMultiplier"
        >
        <span class="multiplier-value">{{ swipeMultiplier.toFixed(1) }}x</span>
      </div>
      <p class="duowei-hint">基于帧率自动设置，也可手动微调。120帧=1.0x，帧率越低需要值越小。</p>
    </div>

    <!-- Lizhan-specific settings -->
    <div class="duowei-settings" v-if="state.selectedPipelineId === 'lizhan_loop'">
      <div class="duowei-setting-row">
        <label>挑战下一关按键</label>
        <input
          type="text"
          class="key-input"
          v-model="lizhanNextKey"
          maxlength="5"
          placeholder="J"
          @change="saveLizhanNextKey"
        >
      </div>
      <p class="duowei-hint">游戏中"挑战下一关"的快捷键，默认为 J（普通攻击键）</p>
    </div>

    <!-- Post-run action -->
    <div class="post-action-bar">
      <label>完成后</label>
      <select
        v-model="postRunAction"
        :disabled="!postRunActionLoaded"
        @change="savePostRunAction"
      >
        <option value="nothing">什么都不做</option>
        <option value="kill_game">退出游戏</option>
        <option value="exit_app">关闭工具</option>
        <option value="exit_app_and_game">关闭工具并退出游戏</option>
        <option value="shutdown_pc">关闭电脑（60秒后）</option>
      </select>
    </div>

    <ControlBar />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import ConnectionBar from '../components/ConnectionBar.vue'
import TaskList from '../components/TaskList.vue'
import ControlBar from '../components/ControlBar.vue'
import { state, selectedPipeline, selectPipeline } from '../composables/useStore'
import { api } from '../composables/useApi'

const showTips = ref(true)
const swipeMultiplier = ref(1.0)
const selectedFps = ref(120)
const postRunAction = ref('nothing')
const postRunActionLoaded = ref(false)
const lizhanNextKey = ref('J')

const fpsPresets = [
  { fps: 120, label: '120帧', multiplier: 1.0 },
  { fps: 90,  label: '90帧',  multiplier: 0.7 },
  { fps: 60,  label: '60帧',  multiplier: 0.5 },
  { fps: 30,  label: '30帧',  multiplier: 0.3 },
]

onMounted(() => {
  const saved = localStorage.getItem('tips_dismissed')
  if (saved === 'true') showTips.value = false
  loadSwipeMultiplier()
  loadPostRunAction()
  loadLizhanNextKey()
})

async function loadSwipeMultiplier() {
  const data = await api.getSettings()
  if (data && data.duowei_swipe_multiplier != null) {
    swipeMultiplier.value = data.duowei_swipe_multiplier
    // Detect which FPS preset matches (within tolerance)
    const preset = fpsPresets.find(p => Math.abs(p.multiplier - swipeMultiplier.value) < 0.05)
    if (preset) selectedFps.value = preset.fps
    else selectedFps.value = 0  // custom
  }
}

function selectFps(preset) {
  selectedFps.value = preset.fps
  swipeMultiplier.value = preset.multiplier
  saveSwipeMultiplier()
}

async function saveSwipeMultiplier() {
  await api.saveDuoweiSwipeMultiplier(swipeMultiplier.value)
  // Update FPS highlight
  const preset = fpsPresets.find(p => Math.abs(p.multiplier - swipeMultiplier.value) < 0.05)
  selectedFps.value = preset ? preset.fps : 0
}

async function loadPostRunAction() {
  for (let i = 0; i < 5; i++) {
    const data = await api.getSettings()
    if (data && data.post_run_action) {
      postRunAction.value = data.post_run_action
      postRunActionLoaded.value = true
      return
    }
    await new Promise(r => setTimeout(r, 300))
  }
}

async function savePostRunAction() {
  await api.setPostRunAction(postRunAction.value)
}

async function loadLizhanNextKey() {
  const data = await api.getSettings()
  if (data && data.lizhan_next_key) {
    lizhanNextKey.value = data.lizhan_next_key
  }
}

async function saveLizhanNextKey() {
  const result = await api.saveLizhanNextKey(lizhanNextKey.value)
  if (result && !result.ok) {
    lizhanNextKey.value = 'J'
  }
}

function dismissTips() {
  showTips.value = false
  saveTips()
}

function saveTips() {
  localStorage.setItem('tips_dismissed', showTips.value ? 'false' : 'true')
}

const tipsByPipeline = {
  daily_routine: [
    { icon: '🖥', text: '游戏分辨率须为 <b>16:9</b>（如 1920×1080、2560×1440）' },
  ],
  duowei_challenge: [
    { icon: '🖥', text: '游戏分辨率须为 <b>16:9</b>（如 1920×1080、2560×1440）' },
    { icon: '⌨️', text: '操控模式选择「<b>键盘</b>」，不要使用键鼠模式' },
    { icon: '⚙️', text: '如修改了战斗快捷键，请在<b>设置 → 战斗按键</b>中同步配置' },
    { icon: '🔓', text: '确保至少已经解锁难度 <b>Lv16</b>' },
  ],
  lizhan_loop: [
    { icon: '🖥', text: '游戏分辨率须为 <b>16:9</b>（如 1920×1080、2560×1440）' },
    { icon: '⚔️', text: '必须<b>手动导航</b>到历战轮回作战准备页面再启动' },
    { icon: '⌨️', text: '操控模式选择「<b>键盘</b>」，确认"挑战下一关"按键与下方设置一致' },
  ],
}

const currentTips = computed(() => {
  const id = state.selectedPipelineId
  return tipsByPipeline[id] || tipsByPipeline.daily_routine || []
})

const currentTasks = computed(() =>
  selectedPipeline.value ? selectedPipeline.value.tasks : []
)

const totalCount = computed(() => currentTasks.value.length)
const completedCount = computed(() =>
  currentTasks.value.filter(t => t.status === 'success').length
)
const progressPct = computed(() =>
  totalCount.value > 0 ? Math.round((completedCount.value / totalCount.value) * 100) : 0
)
</script>

<style scoped>
.tasks-view {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

/* Tips banner */
.tips-banner {
  margin: 8px 12px 0;
  padding: 12px 14px;
  background: var(--tips-bg);
  border: 1px solid var(--tips-border);
  border-radius: var(--radius-lg);
}

.tips-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.tips-header-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tips-icon {
  font-size: 15px;
}

.tips-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--status-warning-text);
}

.tips-close {
  background: none;
  border: none;
  color: var(--tips-text);
  font-size: 10px;
  cursor: pointer;
  padding: 2px 4px;
}

.tips-close:hover {
  color: var(--status-warning-text);
}

.tips-items {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-left: 2px;
}

.tips-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.tips-emoji {
  font-size: 12px;
  flex-shrink: 0;
  margin-top: 1px;
}

.tips-text {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.tips-text :deep(b) {
  color: var(--text-primary);
  font-weight: 600;
}

.tips-collapsed {
  padding: 6px 16px;
  font-size: 11px;
  color: var(--tips-text);
  cursor: pointer;
  border-bottom: 1px solid var(--border-subtle);
}

.tips-collapsed:hover {
  color: var(--status-warning-text);
  background: var(--tips-bg);
}

.pipeline-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 20px;
  border-bottom: 1px solid var(--border-subtle);
}

.pipeline-bar label {
  color: var(--text-muted);
  font-size: 12px;
  flex-shrink: 0;
}

.pipeline-chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.pipeline-chip {
  padding: 5px 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--chip-inactive-border);
  background: var(--chip-inactive-bg);
  color: var(--chip-inactive-text);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
  font-family: var(--font-ui);
}

.pipeline-chip:hover {
  border-color: var(--border-hover);
  color: var(--text-primary);
}

.pipeline-chip.active {
  background: var(--chip-active-bg);
  border-color: var(--chip-active-border);
  color: var(--chip-active-text);
}

.pipeline-desc {
  padding: 4px 20px 8px;
  font-size: 11px;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-subtle);
}

.progress-section {
  padding: 12px 20px 0;
}

.progress-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.progress-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.progress-count {
  font-size: 12px;
  color: var(--text-muted);
}

.progress-track {
  height: 4px;
  background: var(--progress-bg);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--progress-fill);
  border-radius: 2px;
  transition: width 0.3s ease;
}

/* Duowei settings */
.duowei-settings {
  padding: 12px 20px;
  border-top: 1px solid var(--border-subtle);
}

.duowei-setting-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.duowei-setting-row label {
  color: var(--text-secondary);
  font-size: 12px;
  flex-shrink: 0;
  width: 90px;
}

.duowei-setting-row input[type="range"] {
  flex: 1;
  max-width: 180px;
  accent-color: var(--accent-1);
  height: 4px;
}

.multiplier-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--accent-text);
  min-width: 36px;
  text-align: right;
}

.duowei-hint {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
  margin-left: 102px;
}

.key-input {
  width: 60px;
  padding: 4px 8px;
  text-align: center;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
}

/* Post-run action */
.post-action-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 20px;
  border-top: 1px solid var(--border-subtle);
}

.post-action-bar label {
  color: var(--text-muted);
  font-size: 12px;
  flex-shrink: 0;
}

.post-action-bar select {
  font-size: 12px;
  max-width: 260px;
}

/* FPS preset chips */
.fps-chips {
  display: flex;
  gap: 6px;
}

.fps-chip {
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--chip-inactive-border);
  background: var(--chip-inactive-bg);
  color: var(--chip-inactive-text);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.fps-chip:hover {
  border-color: var(--accent-border-strong);
  color: var(--text-secondary);
}

.fps-chip.active {
  background: var(--chip-active-bg);
  border-color: var(--chip-active-border);
  color: var(--chip-active-text);
  font-weight: 600;
}
</style>
