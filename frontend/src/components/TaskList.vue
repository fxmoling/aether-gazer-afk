<template>
  <div class="task-list">
    <div class="task-header">
      <label class="checkbox-label">
        <div
          class="task-check"
          :class="{ checked: allChecked, indeterminate: someChecked && !allChecked }"
          @click="toggleAllTasks(!allChecked)"
        ></div>
        <span>全选</span>
      </label>
    </div>
    <div class="task-items">
      <div
        v-for="task in tasks"
        :key="task.id"
        class="task-item"
        :class="taskClass(task)"
      >
        <div
          class="task-check"
          :class="{ checked: task.enabled }"
          @click="toggleTask(task.id, !task.enabled)"
        ></div>
        <span class="task-icon">{{ taskIcon(task.id) }}</span>
        <span class="task-name" :class="{ unsafe: !task.safe }">
          {{ task.name }}
        </span>
        <div v-if="(task.status || 'pending') === 'running'" class="spinner"></div>
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

const TASK_ICONS = {
  'launch_game': '🎮',
  'collect_mail': '📬',
  'buy_intel': '🛒',
  'collect_stamina_pack': '🔋',
  'shop_free_stamina': '🏪',
  'mimi_station': '🔭',
  'guild_supply': '🏰',
  'amusement_daily': '🎡',
  'joint_defense': '⚔️',
  'daily_weekly_tasks': '📋',
  'countermeasure': '📝',
}

function taskIcon(taskId) {
  return TASK_ICONS[taskId] || '📌'
}

const STATUS_MAP = {
  pending: '等待',
  running: '运行中',
  success: '✓ 完成',
  failed: '✘ 失败',
  skipped: '— 跳过',
}

function statusText(status) {
  return STATUS_MAP[status] || status
}

function taskClass(task) {
  const s = task.status || 'pending'
  if (s === 'pending') return ''
  return s
}
</script>

<style scoped>
.task-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px 20px;
}

.task-header {
  padding: 0 0 8px 0;
  margin-bottom: 4px;
}

.task-items {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* NO transition — instant hover */
.task-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 12px;
  background: rgba(255,255,255,0.025);
  border: 1px solid rgba(255,255,255,0.04);
}

.task-item:hover {
  background: rgba(255,255,255,0.06);
  border-color: rgba(255,255,255,0.1);
}

.task-item.running {
  background: rgba(102,126,234,0.1);
  border-color: rgba(102,126,234,0.35);
  box-shadow: 0 0 24px rgba(102,126,234,0.12);
  animation: glowPulse 3s ease-in-out infinite;
}

.task-item.success {
  border-color: rgba(76,175,80,0.15);
}

.task-item.failed {
  border-color: rgba(244,67,54,0.3);
}

@keyframes glowPulse {
  0%, 100% { box-shadow: 0 0 24px rgba(102,126,234,0.12); }
  50% { box-shadow: 0 0 36px rgba(102,126,234,0.22); }
}

/* Custom checkbox */
.task-check {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255,255,255,0.12);
  border-radius: 6px;
  cursor: pointer;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.task-check.checked {
  background: #667eea;
  border-color: #667eea;
}

.task-check.checked::after {
  content: '✓';
  color: white;
  font-size: 11px;
  font-weight: 700;
}

.task-check.indeterminate {
  background: rgba(102,126,234,0.4);
  border-color: rgba(102,126,234,0.6);
}

.task-check.indeterminate::after {
  content: '—';
  color: white;
  font-size: 11px;
  font-weight: 700;
}

/* Task icon */
.task-icon {
  font-size: 18px;
  width: 24px;
  text-align: center;
  flex-shrink: 0;
}

.task-item.success .task-icon {
  opacity: 0.45;
}

.task-item:not(.running):not(.success):not(.failed) .task-icon {
  opacity: 0.35;
}

.task-name {
  flex: 1;
  font-size: 13px;
  color: #c8c8d0;
}

.task-name.unsafe {
  color: #ffb74d;
}

.task-item.success .task-name {
  text-decoration: line-through;
  opacity: 0.4;
}

/* Status badges */
.task-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
  font-weight: 500;
  flex-shrink: 0;
}

.badge-pending { color: rgba(255,255,255,0.12); }
.badge-running { background: rgba(102,126,234,0.15); color: #8b9cf7; }
.badge-success { background: rgba(76,175,80,0.1); color: #66bb6a; }
.badge-failed { background: rgba(244,67,54,0.1); color: #ef5350; }
.badge-skipped { color: rgba(255,255,255,0.15); }

/* Spinner for running tasks */
.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(102,126,234,0.3);
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.task-empty {
  padding: 24px;
  text-align: center;
  color: rgba(255,255,255,0.2);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  color: rgba(255,255,255,0.35);
}
</style>
