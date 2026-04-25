<template>
  <div class="tasks-view">
    <ConnectionBar />

    <!-- Pipeline selector -->
    <div class="pipeline-bar">
      <label>流程</label>
      <select v-model="state.selectedPipelineId" @change="selectPipeline(state.selectedPipelineId)">
        <option v-for="p in state.pipelines" :key="p.id" :value="p.id">
          {{ p.name }}
        </option>
      </select>
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
    <ControlBar />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import ConnectionBar from '../components/ConnectionBar.vue'
import TaskList from '../components/TaskList.vue'
import ControlBar from '../components/ControlBar.vue'
import { state, selectedPipeline, selectPipeline } from '../composables/useStore'

const showTips = ref(true)

onMounted(() => {
  const saved = localStorage.getItem('tips_dismissed')
  if (saved === 'true') showTips.value = false
})

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
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.08), rgba(245, 158, 11, 0.03));
  border: 1px solid rgba(245, 158, 11, 0.2);
  border-radius: 10px;
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
  color: #f5a623;
}

.tips-close {
  background: none;
  border: none;
  color: rgba(245, 158, 11, 0.5);
  font-size: 10px;
  cursor: pointer;
  padding: 2px 4px;
}

.tips-close:hover {
  color: #f5a623;
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
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.5;
}

.tips-text :deep(b) {
  color: rgba(255, 255, 255, 0.85);
  font-weight: 600;
}

.tips-collapsed {
  padding: 6px 16px;
  font-size: 11px;
  color: rgba(245, 158, 11, 0.5);
  cursor: pointer;
  border-bottom: 1px solid rgba(255,255,255,0.03);
}

.tips-collapsed:hover {
  color: #f5a623;
  background: rgba(245, 158, 11, 0.05);
}

.pipeline-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.03);
}

.pipeline-bar label {
  color: rgba(255,255,255,0.35);
  font-size: 12px;
  flex-shrink: 0;
}

.pipeline-bar select {
  flex: 1;
  max-width: 400px;
  font-size: 13px;
}

.pipeline-desc {
  padding: 4px 20px 8px;
  font-size: 11px;
  color: rgba(255,255,255,0.3);
  border-bottom: 1px solid rgba(255,255,255,0.03);
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
  color: #e0e0e8;
}

.progress-count {
  font-size: 12px;
  color: rgba(255,255,255,0.35);
}

.progress-track {
  height: 4px;
  background: rgba(255,255,255,0.05);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  border-radius: 2px;
  transition: width 0.3s ease;
}
</style>
