<template>
  <div class="logs-view">
    <LogOutput />
  </div>
</template>

<script setup>
import LogOutput from '../components/LogOutput.vue'
</script>

<style scoped>
.logs-view {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}
</style>
