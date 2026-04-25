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
  border-radius: 10px;
  white-space: nowrap;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.07);
  color: #c8c8d0;
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
  border-top: 5px solid rgba(255,255,255,0.3);
  transition: transform 0.15s;
}

.open .display::after {
  transform: translateY(-50%) rotate(180deg);
}

.display:hover {
  border-color: rgba(255,255,255,0.15);
}

.open .display {
  border-color: rgba(102,126,234,0.4);
}

.menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  min-width: 100%;
  background: linear-gradient(180deg, #1a1545, #130f30);
  border: 1px solid rgba(102,126,234,0.2);
  border-radius: 10px;
  box-shadow: 0 8px 40px rgba(102,126,234,0.15), 0 2px 10px rgba(0,0,0,0.4);
  overflow: hidden;
  z-index: 100;
}

.menu-item {
  padding: 9px 12px;
  font-size: 12px;
  color: rgba(255,255,255,0.55);
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
}

.menu-item:hover {
  background: linear-gradient(90deg, rgba(102,126,234,0.12), transparent);
  color: #e0e0e8;
}

.menu-item.selected {
  background: linear-gradient(90deg, rgba(102,126,234,0.2), transparent);
  color: #667eea;
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
