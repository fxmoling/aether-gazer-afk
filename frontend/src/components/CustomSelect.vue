<template>
  <div class="custom-select" :class="{ open: isOpen, disabled: disabled }" ref="root">
    <div class="display" @click="toggle">
      <span class="display-text">{{ displayText }}</span>
    </div>
    <Transition name="dropdown">
      <div class="menu" v-if="isOpen">
        <div
          v-for="opt in options"
          :key="opt.value"
          class="menu-item"
          :class="{ selected: opt.value === modelValue }"
          @click="select(opt.value)"
        >
          {{ opt.label }}
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  options: { type: Array, default: () => [] },  // [{ value, label }]
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const isOpen = ref(false)
const root = ref(null)

const displayText = computed(() => {
  const opt = props.options.find(o => o.value === props.modelValue)
  return opt ? opt.label : props.modelValue || '—'
})

function toggle() {
  if (!props.disabled) isOpen.value = !isOpen.value
}

function select(val) {
  emit('update:modelValue', val)
  isOpen.value = false
}

function onClickOutside(e) {
  if (root.value && !root.value.contains(e.target)) {
    isOpen.value = false
  }
}

onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))
</script>

<style scoped>
.custom-select {
  position: relative;
  display: inline-block;
  min-width: 100px;
}

.custom-select.disabled {
  opacity: 0.45;
  pointer-events: none;
}

.display {
  padding: 8px 30px 8px 12px;
  font-size: 12px;
  cursor: pointer;
  border-radius: var(--radius-lg);
  white-space: nowrap;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  position: relative;
  transition: border-color 0.15s;
}

.display::after {
  content: '';
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 5px solid var(--text-muted);
  transition: transform 0.15s;
}

.open .display::after {
  transform: translateY(-50%) rotate(180deg);
}

.display:hover {
  border-color: var(--border-hover);
}

.open .display {
  border-color: var(--accent-glow);
}

.menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  min-width: 100%;
  background: var(--bg-dropdown);
  border: 1px solid var(--accent-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-glow), var(--shadow-md);
  overflow: hidden;
  z-index: 100;
}

.menu-item {
  padding: 9px 12px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
}

.menu-item:hover {
  background: var(--select-item-hover);
  color: var(--text-primary);
}

.menu-item.selected {
  background: var(--select-item-active);
  color: var(--accent-1);
  font-weight: 600;
}

/* Dropdown transition */
.dropdown-enter-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.dropdown-leave-active {
  transition: opacity 0.1s ease, transform 0.1s ease;
}
.dropdown-enter-from {
  opacity: 0;
  transform: translateY(-4px);
}
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
