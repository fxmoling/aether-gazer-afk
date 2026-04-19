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
        <span class="info-value">{{ settings.version || '-' }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">游戏</span>
        <span class="info-value">深空之眼 (Aether Gazer)</span>
      </div>
    </div>

    <div class="settings-section">
      <h3>更新</h3>
      <div class="setting-row">
        <label>自动检查更新</label>
        <label class="toggle-switch">
          <input type="checkbox" v-model="form.autoUpdate" @change="onAutoUpdateToggle">
          <span class="toggle-slider"></span>
        </label>
      </div>
      <div class="setting-row">
        <label></label>
        <button class="btn btn-secondary" @click="checkUpdate" :disabled="checking">
          {{ checking ? '检查中...' : '🔍 检查更新' }}
        </button>
        <span v-if="updateMsg" class="update-msg" :class="updateMsgClass">
          {{ updateMsg }}
        </span>
      </div>
      <div v-if="updateInfo && updateInfo.has_update" class="update-banner">
        <span>🎉 新版本 <b>v{{ updateInfo.latest_version }}</b> 可用！当前版本: v{{ updateInfo.current_version }}</span>
        <a class="btn btn-primary btn-sm" :href="updateInfo.release_url" target="_blank" @click="openRelease">
          前往下载
        </a>
      </div>
    </div>

    <div class="settings-section">
      <h3>运行模式</h3>
      <div class="setting-row">
        <label>🖥️ 后台模式 (虚拟桌面)</label>
        <label class="toggle-switch">
          <input type="checkbox" v-model="form.backgroundMode" @change="onBackgroundModeToggle">
          <span class="toggle-slider"></span>
        </label>
      </div>
      <p class="setting-hint">在独立桌面运行游戏，不影响鼠标操作</p>
      <div class="setting-row">
        <label>🔔 完成通知</label>
        <label class="toggle-switch">
          <input type="checkbox" v-model="form.notifyOnComplete" @change="onNotifyToggle">
          <span class="toggle-slider"></span>
        </label>
      </div>
      <p class="setting-hint">任务完成或失败时显示系统通知</p>
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
          @blur="saveWindowTitle"
          @keyup.enter="$event.target.blur()"
        >
        <span v-if="savedHint === 'windowTitle'" class="save-hint">✔</span>
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

    <div class="settings-footer">
      <span class="footer-text">
        深空之眼自动化工具 ·
        <a href="https://github.com/fxmoling/anime-game-afk" target="_blank" class="footer-link">GitHub</a>
        · 仅供学习交流使用
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api } from '../composables/useApi'

const settings = reactive({
  version: '',
  game_exe_path: '',
})

const form = reactive({
  windowTitle: 'AetherGazer',
  autoUpdate: true,
  backgroundMode: false,
  notifyOnComplete: true,
})

const detecting = ref(false)
const checking = ref(false)
const updateMsg = ref('')
const updateMsgClass = ref('')
const updateInfo = ref(null)
const savedHint = ref('')

onMounted(async () => {
  const data = await api.getSettings()
  if (data) {
    settings.version = data.version || ''
    settings.game_exe_path = data.game_exe_path || ''
    form.windowTitle = data.window_title || 'AetherGazer'
    form.autoUpdate = data.auto_update !== false
    form.backgroundMode = data.background_mode === true
    form.notifyOnComplete = data.notify_on_complete !== false
  }
})

async function saveWindowTitle() {
  const result = await api.saveSettings(form.windowTitle)
  if (result && result.ok) {
    savedHint.value = 'windowTitle'
    setTimeout(() => { savedHint.value = '' }, 2000)
  }
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

async function onAutoUpdateToggle() {
  await api.setAutoUpdate(form.autoUpdate)
}

async function onBackgroundModeToggle() {
  await api.setBackgroundMode(form.backgroundMode)
}

async function onNotifyToggle() {
  await api.setNotifyOnComplete(form.notifyOnComplete)
}

async function checkUpdate() {
  checking.value = true
  updateMsg.value = ''
  updateInfo.value = null

  const result = await api.checkUpdate()
  checking.value = false

  if (!result || !result.ok) {
    updateMsg.value = result?.error || '检查失败'
    updateMsgClass.value = 'err'
    setTimeout(() => { updateMsg.value = '' }, 5000)
    return
  }

  if (result.has_update) {
    updateInfo.value = result
    updateMsg.value = ''
  } else {
    updateMsg.value = '✔ 已是最新版本'
    updateMsgClass.value = 'ok'
    setTimeout(() => { updateMsg.value = '' }, 5000)
  }
}

function openRelease() {
  // pywebview will handle target="_blank" as external browser
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

.save-hint {
  color: #4caf50;
  font-size: 13px;
  animation: fade-out 2s forwards;
}

@keyframes fade-out {
  0%, 70% { opacity: 1; }
  100% { opacity: 0; }
}

/* Toggle switch */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 40px !important;
  height: 22px;
  flex-shrink: 0;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0; left: 0; right: 0; bottom: 0;
  background: #333;
  border-radius: 22px;
  transition: 0.2s;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background: #999;
  border-radius: 50%;
  transition: 0.2s;
}

.toggle-switch input:checked + .toggle-slider {
  background: #2196f3;
}

.toggle-switch input:checked + .toggle-slider::before {
  transform: translateX(18px);
  background: white;
}

/* Update banner */
.update-banner {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 10px;
  padding: 10px 14px;
  background: #1a2a1a;
  border: 1px solid #2e7d32;
  border-radius: 8px;
  font-size: 13px;
  color: #c8e6c9;
}

.update-banner a {
  white-space: nowrap;
  text-decoration: none;
  font-size: 12px;
  padding: 4px 12px;
}

.update-msg {
  font-size: 13px;
}

.update-msg.ok { color: #4caf50; }
.update-msg.err { color: #f44336; }

.btn-sm {
  padding: 4px 12px;
  font-size: 12px;
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

.footer-link {
  color: #4fc3f7;
  text-decoration: none;
}

.footer-link:hover {
  text-decoration: underline;
}
</style>
