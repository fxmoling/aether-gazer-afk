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
        @click="toggleTask(task.id, !task.enabled)"
      >
        <div
          class="task-check"
          :class="{ checked: task.enabled }"
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
  stopped: '■ 已停',
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
  border-radius: var(--radius-lg);
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  cursor: pointer;
  user-select: none;
}

.task-item:hover {
  background: var(--bg-surface-hover);
  border-color: var(--border-default);
}

.task-item.running {
  background: var(--accent-tint);
  border-color: var(--accent-border-strong);
  box-shadow: 0 0 24px var(--accent-tint-hover);
  animation: glowPulse 3s ease-in-out infinite;
}

.task-item.success {
  border-color: var(--status-success-bg);
}

.task-item.failed {
  border-color: var(--status-error-bg);
}

.task-item.stopped {
  border-color: var(--status-warning-bg);
}

@keyframes glowPulse {
  0%, 100% { box-shadow: 0 0 24px var(--accent-tint-hover); }
  50% { box-shadow: 0 0 36px var(--accent-border); }
}

/* Custom checkbox */
.task-check {
  width: 18px;
  height: 18px;
  border: 2px solid var(--checkbox-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.task-check.checked {
  background: var(--accent-1);
  border-color: var(--accent-1);
}

.task-check.checked::after {
  content: '✓';
  color: var(--text-on-accent);
  font-size: 11px;
  font-weight: 700;
}

.task-check.indeterminate {
  background: var(--accent-glow);
  border-color: var(--accent-1);
}

.task-check.indeterminate::after {
  content: '—';
  color: var(--text-on-accent);
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

.task-item:not(.running):not(.success):not(.failed):not(.stopped) .task-icon {
  opacity: 0.35;
}

.task-name {
  flex: 1;
  font-size: 13px;
  color: var(--text-secondary);
}

.task-name.unsafe {
  color: var(--status-warning-text);
}

.task-item.success .task-name {
  text-decoration: line-through;
  opacity: 0.4;
}

/* Status badges */
.task-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-weight: 500;
  flex-shrink: 0;
}

.badge-pending { color: var(--border-hover); }
.badge-running { background: var(--status-running-bg); color: var(--status-running); }
.badge-success { background: var(--status-success-bg); color: var(--status-success-text); }
.badge-failed { background: var(--status-error-bg); color: var(--status-error-text); }
.badge-stopped { background: var(--status-warning-bg); color: var(--status-warning-text); }
.badge-skipped { color: var(--checkbox-border); }

/* Spinner for running tasks */
.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--accent-border);
  border-top-color: var(--accent-1);
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
  color: var(--text-muted);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-muted);
}
</style>
