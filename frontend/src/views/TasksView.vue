<template>
  <div class="tasks-view">
    <ConnectionBar />

    <!-- Pipeline selector -->
    <div class="pipeline-selector">
      <label>选择流程：</label>
      <select v-model="state.selectedPipelineId" @change="selectPipeline(state.selectedPipelineId)">
        <option v-for="p in state.pipelines" :key="p.id" :value="p.id">
          {{ p.name }} — {{ p.description }}
        </option>
      </select>
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
</script>

<style scoped>
.tasks-view {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.pipeline-selector {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: #1a1a3e;
  border-bottom: 1px solid #252550;
}

.pipeline-selector label {
  color: #aaa;
  font-size: 13px;
  flex-shrink: 0;
}

.pipeline-selector select {
  flex: 1;
  max-width: 300px;
  padding: 6px 10px;
  background: #0f1129;
  color: #e0e0e0;
  border: 1px solid #333;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}

.pipeline-selector select:focus {
  outline: none;
  border-color: #4fc3f7;
}
</style>
