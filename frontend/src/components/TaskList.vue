<template>
  <div class="task-list">
    <div class="task-header">
      <label class="checkbox-label">
        <input
          type="checkbox"
          :checked="allChecked"
          :indeterminate="someChecked && !allChecked"
          @change="toggleAllTasks($event.target.checked)"
        >
        <span>全选</span>
      </label>
    </div>
    <div class="task-items">
      <div
        v-for="task in tasks"
        :key="task.id"
        class="task-item"
        :class="task.status !== 'pending' ? task.status : ''"
      >
        <input
          type="checkbox"
          :checked="task.enabled"
          @change="toggleTask(task.id, $event.target.checked)"
        >
        <span class="task-name" :class="{ unsafe: !task.safe }">
          {{ task.name }}
        </span>
        <span class="task-badge" :class="`badge-${task.status || 'pending'}`">
          {{ statusText(task.status || 'pending') }}
        </span>
      </div>
      <div v-if="tasks.length === 0" class="task-empty">
        暂无任务
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { toggleTask, toggleAllTasks } from '../composables/useStore'

const props = defineProps({
  tasks: { type: Array, default: () => [] },
})

const allChecked = computed(() =>
  props.tasks.length > 0 && props.tasks.every(t => t.enabled)
)
const someChecked = computed(() =>
  props.tasks.some(t => t.enabled)
)

const STATUS_MAP = {
  pending: '● 等待',
  running: '▶ 运行中',
  success: '✔ 完成',
  failed: '✘ 失败',
  skipped: '— 跳过',
}

function statusText(status) {
  return STATUS_MAP[status] || status
}
</script>

<style scoped>
.task-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 16px;
}

.task-header {
  padding: 6px 0;
  border-bottom: 1px solid #252550;
  margin-bottom: 4px;
}

.task-items {
  display: flex;
  flex-direction: column;
}

.task-item {
  display: flex;
  align-items: center;
  padding: 8px 10px;
  border-radius: 6px;
  margin: 2px 0;
  transition: background 0.15s;
}

.task-item:hover {
  background: #1a1a3e;
}

.task-item.running {
  background: #1a1a4e;
  border: 1px solid #ff9800;
}

.task-item input[type="checkbox"] {
  accent-color: #4fc3f7;
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.task-name {
  flex: 1;
  margin-left: 8px;
  font-size: 13px;
}

.task-name.unsafe {
  color: #ffb74d;
}

.task-badge {
  font-size: 12px;
  min-width: 60px;
  text-align: right;
  flex-shrink: 0;
}

.badge-pending { color: #666; }
.badge-running { color: #ff9800; animation: pulse 1.5s ease-in-out infinite; }
.badge-success { color: #4caf50; }
.badge-failed { color: #f44336; }
.badge-skipped { color: #555; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.task-empty {
  padding: 24px;
  text-align: center;
  color: #555;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #aaa;
}

.checkbox-label input[type="checkbox"] {
  accent-color: #4fc3f7;
  width: 16px;
  height: 16px;
  cursor: pointer;
}
</style>
