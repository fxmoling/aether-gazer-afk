<template>
  <div class="tasks-view">
    <ConnectionBar />

    <!-- Pipeline selector -->
    <div class="pipeline-bar">
      <label>流程</label>
      <select v-model="state.selectedPipelineId" @change="selectPipeline(state.selectedPipelineId)">
        <option v-for="p in state.pipelines" :key="p.id" :value="p.id">
          {{ p.name }} — {{ p.description }}
        </option>
      </select>
    </div>

    <!-- Progress section -->
    <div class="progress-section">
      <div class="progress-header">
        <span class="progress-title">今日进度</span>
        <span class="progress-count">{{ completedCount }} / {{ totalCount }}</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: progressPct + '%' }"></div>
      </div>
    </div>

    <TaskList :tasks="currentTasks" />
    <ControlBar />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import ConnectionBar from '../components/ConnectionBar.vue'
import TaskList from '../components/TaskList.vue'
import ControlBar from '../components/ControlBar.vue'
import { state, selectedPipeline, selectPipeline } from '../composables/useStore'

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
  max-width: 300px;
  padding: 6px 12px;
  background: rgba(255,255,255,0.05);
  color: #c8c8d0;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  font-size: 12px;
  cursor: pointer;
}

.pipeline-bar select:focus {
  outline: none;
  border-color: rgba(102,126,234,0.5);
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
