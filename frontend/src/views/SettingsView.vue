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
        <span class="info-value">{{ settings.version || '0.1.0' }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">游戏</span>
        <span class="info-value">深空之眼 (Aether Gazer)</span>
      </div>
    </div>

    <div class="settings-section">
      <h3>游戏设置</h3>
      <div class="setting-row">
        <label>游戏窗口标题</label>
        <input
          type="text"
          v-model="form.windowTitle"
          placeholder="AetherGazer"
          class="setting-input"
        >
      </div>
      <div class="setting-row">
        <label>游戏路径</label>
        <div class="path-row">
          <input
            type="text"
            :value="settings.game_exe_path || '(未设置，将自动检测)'"
            readonly
            class="setting-input path-input"
          >
          <button class="btn btn-secondary" @click="detectGamePath">
            {{ detecting ? '检测中...' : '自动检测' }}
          </button>
        </div>
      </div>
      <p class="setting-hint">
        程序通过窗口标题查找游戏。游戏路径用于自动启动游戏。
      </p>
    </div>

    <div class="settings-section">
      <h3>运行设置</h3>
      <div class="setting-row">
        <label>任务间延迟 (秒)</label>
        <input
          type="number"
          v-model.number="form.taskDelay"
          min="0"
          max="10"
          step="0.5"
          class="setting-input narrow"
        >
      </div>
    </div>

    <div class="settings-actions">
      <button class="btn btn-primary" @click="saveAll" :disabled="saving">
        {{ saving ? '保存中...' : '💾 保存设置' }}
      </button>
      <span v-if="saveMsg" class="save-msg" :class="saveOk ? 'ok' : 'err'">
        {{ saveMsg }}
      </span>
    </div>

    <div class="settings-footer">
      <span class="footer-text">
        深空之眼自动化工具 · 仅供学习交流使用
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api } from '../composables/useApi'

const settings = reactive({
  version: '0.1.0',
  game_exe_path: '',
})

const form = reactive({
  windowTitle: 'AetherGazer',
  taskDelay: 1.0,
})

const saving = ref(false)
const saveMsg = ref('')
const saveOk = ref(false)
const detecting = ref(false)

onMounted(async () => {
  const data = await api.getSettings()
  if (data) {
    settings.version = data.version || '0.1.0'
    settings.game_exe_path = data.game_exe_path || ''
    form.windowTitle = data.window_title || 'AetherGazer'
    form.taskDelay = data.task_delay ?? 1.0
  }
})

async function saveAll() {
  saving.value = true
  saveMsg.value = ''
  const result = await api.saveSettings(form.windowTitle, form.taskDelay)
  saving.value = false
  if (result && result.ok) {
    saveMsg.value = '✔ 已保存'
    saveOk.value = true
  } else {
    saveMsg.value = result?.error || '保存失败'
    saveOk.value = false
  }
  setTimeout(() => { saveMsg.value = '' }, 3000)
}

async function detectGamePath() {
  detecting.value = true
  const result = await api.detectGame()
  detecting.value = false
  if (result && result.game_exe) {
    settings.game_exe_path = result.game_exe
  } else {
    alert('未找到游戏安装路径。请确认游戏已安装。')
  }
}
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
  width: 120px;
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

.path-row {
  display: flex;
  gap: 8px;
  flex: 1;
}

.path-input {
  max-width: 400px;
  color: #888;
}

.setting-hint {
  color: #555;
  font-size: 12px;
  margin-top: 4px;
  margin-left: 132px;
}

.settings-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #252550;
}

.save-msg {
  font-size: 13px;
}

.save-msg.ok { color: #4caf50; }
.save-msg.err { color: #f44336; }

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
