<template>
  <div class="settings-view">
    <div class="settings-section">
      <h3>关于</h3>
      <div class="info-row">
        <span class="info-label">应用名称</span>
        <span class="info-value">AetherGazer AFK</span>
      </div>
      <div class="info-row">
        <span class="info-label">版本</span>
        <span class="info-value">{{ version }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">游戏</span>
        <span class="info-value">深空之眼 (Aether Gazer)</span>
      </div>
    </div>

    <div class="settings-section">
      <h3>连接设置</h3>
      <div class="setting-row">
        <label>游戏窗口标题</label>
        <input
          type="text"
          v-model="windowTitle"
          placeholder="AetherGazer"
          class="setting-input"
        >
      </div>
      <p class="setting-hint">
        程序通过窗口标题查找游戏进程。如果游戏窗口标题不是默认的 "AetherGazer"，请在此修改。
      </p>
    </div>

    <div class="settings-section">
      <h3>运行设置</h3>
      <div class="setting-row">
        <label>任务间延迟 (秒)</label>
        <input
          type="number"
          v-model.number="taskDelay"
          min="0"
          max="10"
          step="0.5"
          class="setting-input narrow"
        >
      </div>
      <p class="setting-hint">
        每个任务完成后等待的时间，用于确保画面稳定。
      </p>
    </div>

    <div class="settings-footer">
      <span class="footer-text">
        深空之眼自动化工具 · 仅供学习交流使用
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const version = '0.1.0'
const windowTitle = ref('AetherGazer')
const taskDelay = ref(1.0)
</script>

<style scoped>
.settings-view {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.settings-section {
  margin-bottom: 28px;
}

.settings-section h3 {
  font-size: 15px;
  color: #4fc3f7;
  margin-bottom: 12px;
  padding-bottom: 6px;
  border-bottom: 1px solid #252550;
}

.info-row {
  display: flex;
  align-items: center;
  padding: 6px 0;
}

.info-label {
  width: 100px;
  color: #888;
  font-size: 13px;
}

.info-value {
  color: #e0e0e0;
  font-size: 13px;
}

.setting-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 0;
}

.setting-row label {
  width: 140px;
  color: #aaa;
  font-size: 13px;
  flex-shrink: 0;
}

.setting-input {
  flex: 1;
  max-width: 250px;
  padding: 6px 10px;
  background: #0f1129;
  color: #e0e0e0;
  border: 1px solid #333;
  border-radius: 6px;
  font-size: 13px;
}

.setting-input.narrow {
  max-width: 80px;
}

.setting-input:focus {
  outline: none;
  border-color: #4fc3f7;
}

.setting-hint {
  color: #555;
  font-size: 12px;
  margin-top: 4px;
  margin-left: 152px;
}

.settings-footer {
  margin-top: 40px;
  padding-top: 16px;
  border-top: 1px solid #252550;
  text-align: center;
}

.footer-text {
  color: #444;
  font-size: 12px;
}
</style>
