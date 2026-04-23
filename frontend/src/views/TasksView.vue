<template>
  <div class="tasks-view">
    <ConnectionBar />

    <!-- Usage tips banner -->
    <div class="tips-banner" v-if="showTips">
      <div class="tips-header">
        <span class="tips-icon">⚠</span>
        <span class="tips-title">使用须知</span>
        <button class="tips-close" @click="dismissTips">收起</button>
      </div>
      <ul class="tips-list">
        <li>游戏分辨率须为 <b>16:9</b>（如 1920×1080、2560×1440）</li>
        <li>操控模式选择「<b>键盘</b>」，不要使用键鼠模式</li>
        <li>关闭<b>异形屏适配</b>（设置 → 画面）</li>
        <li>战斗快捷键保持<b>默认设置</b>，勿自定义键位</li>
      </ul>
    </div>
    <div class="tips-collapsed" v-else @click="showTips = true; saveTips()">
      <span class="tips-icon">⚠</span> 使用须知（点击展开）
    </div>

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
  padding: 10px 14px;
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.25);
  border-radius: 8px;
}

.tips-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.tips-icon {
  font-size: 14px;
  color: #f59e0b;
}

.tips-title {
  font-size: 12px;
  font-weight: 600;
  color: #f59e0b;
  flex: 1;
}

.tips-close {
  background: none;
  border: 1px solid rgba(245, 158, 11, 0.3);
  color: rgba(245, 158, 11, 0.7);
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.tips-close:hover {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.tips-list {
  margin: 0;
  padding: 0 0 0 18px;
  list-style: disc;
}

.tips-list li {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.55);
  line-height: 1.7;
}

.tips-list b {
  color: rgba(255, 255, 255, 0.8);
  font-weight: 600;
}

.tips-collapsed {
  padding: 6px 20px;
  font-size: 11px;
  color: rgba(245, 158, 11, 0.5);
  cursor: pointer;
  border-bottom: 1px solid rgba(255,255,255,0.03);
}

.tips-collapsed:hover {
  color: #f59e0b;
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
  padding: 6px 12px;
  background: rgba(255,255,255,0.05);
  color: #c8c8d0;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
}

.pipeline-bar select:focus {
  outline: none;
  border-color: rgba(102,126,234,0.5);
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
