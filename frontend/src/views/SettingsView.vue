<template>
  <div class="settings-view">
    <div class="settings-section">
      <h3>主题</h3>
      <div class="theme-grid">
        <div
          v-for="t in themeList"
          :key="t.id"
          class="theme-chip"
          :class="{ active: currentTheme === t.id }"
          @click="setTheme(t.id)"
        >{{ t.name }}</div>
      </div>
    </div>

    <div class="settings-section">
      <h3>游戏路径</h3>
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
        未设置时将自动检测正在运行的游戏进程。
      </p>
    </div>

    <div class="settings-section">
      <h3>战斗按键</h3>
      <p class="setting-hint" style="margin-left: 0; margin-bottom: 10px">
        如果你修改了游戏内的战斗快捷键，请在此处同步配置。<br>
        <b>注意：</b>请勿修改其他便利性快捷键（如邮箱、开始作战等），否则自动化流程可能异常。
      </p>
      <div class="keybind-grid">
        <div class="keybind-row" v-for="(label, key) in keybindLabels" :key="key">
          <label>{{ label }}</label>
          <input
            type="text"
            :value="form.keybinds[key]"
            maxlength="1"
            class="setting-input keybind-input"
            @keydown.prevent="onKeybindKey(key, $event)"
            readonly
          >
        </div>
      </div>
      <div v-if="keybindSaved" class="save-hint" style="margin-top: 6px">✔ 已保存</div>
    </div>

    <div class="settings-section">
      <h3>全局快捷键</h3>
      <p class="setting-hint" style="margin-bottom: 8px">仅在游戏窗口前台时生效，不影响其他应用</p>
      <div
        v-for="item in hotkeyItems"
        :key="item.action"
        class="setting-row"
      >
        <label>{{ item.label }}</label>
        <button
          ref="hotkeyBtnRefs"
          class="btn btn-secondary hotkey-btn"
          :class="{ capturing: capturingAction === item.action }"
          :data-action="item.action"
          @click.stop="startCapture(item.action)"
        >
          {{ capturingAction === item.action ? '按下新组合键（Esc 取消）…' : (hotkeys[item.action] || '未设置') }}
        </button>
      </div>
      <div v-if="hotkeyMsg" class="save-hint">{{ hotkeyMsg }}</div>
    </div>

    <div class="settings-section">
      <h3>通知</h3>
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
      <h3>关于</h3>
      <div class="info-row">
        <span class="info-label">版本</span>
        <span class="info-value">{{ settings.version || '-' }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">QQ 群</span>
        <span class="info-value">
          <a :href="qqGroupUrl" target="_blank" class="footer-link">915233498</a>
        </span>
      </div>
      <div class="qr-row">
        <img :src="qqGroupQr" class="qr-img" alt="QQ群二维码">
      </div>
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
import { useTheme } from '../themes/useTheme'
import qqGroupQrSrc from '../assets/group_qr.jpg'

const { currentTheme, setTheme, themeList } = useTheme()

const qqGroupUrl = 'https://qm.qq.com/q/W9LZqg9NG'
const qqGroupQr = qqGroupQrSrc

const settings = reactive({
  version: '',
  game_exe_path: '',
})

const form = reactive({
  autoUpdate: true,
  notifyOnComplete: true,
  keybinds: {
    attack: 'J',
    skill1: 'U',
    skill2: 'I',
    skill3: 'O',
    ultimate: 'R',
    dodge: 'Space',
    qte1: '1',
    qte2: '2',
  },
})

const detecting = ref(false)
const checking = ref(false)
const updateMsg = ref('')
const updateMsgClass = ref('')
const updateInfo = ref(null)
const keybindSaved = ref(false)

const hotkeyItems = [
  { action: 'toggle_auto_battle', label: '切换自动战斗' },
  { action: 'stop_all', label: '停止当前任务' },
]
const hotkeys = reactive({ toggle_auto_battle: '', stop_all: '' })
const capturingAction = ref('')
const hotkeyMsg = ref('')
let hotkeyMsgTimer = null

function showHotkeyMsg(text) {
  hotkeyMsg.value = text
  if (hotkeyMsgTimer) clearTimeout(hotkeyMsgTimer)
  hotkeyMsgTimer = setTimeout(() => { hotkeyMsg.value = '' }, 1800)
}

const keybindLabels = {
  attack: '攻击',
  skill1: '技能1',
  skill2: '技能2',
  skill3: '技能3',
  ultimate: '大招',
  dodge: '闪避',
  qte1: 'QTE1',
  qte2: 'QTE2',
}

onMounted(async () => {
  const data = await api.getSettings()
  if (data) {
    settings.version = data.version || ''
    settings.game_exe_path = data.game_exe_path || ''
    form.autoUpdate = data.auto_update !== false
    form.notifyOnComplete = data.notify_on_complete !== false
    if (data.combat_keybinds) {
      Object.assign(form.keybinds, data.combat_keybinds)
    }
    if (data.hotkeys) {
      for (const k of Object.keys(hotkeys)) {
        if (typeof data.hotkeys[k] === 'string') hotkeys[k] = data.hotkeys[k]
      }
    }
  }
})

function startCapture(action) {
  capturingAction.value = action
  // Install document listeners for this capture session.
  // Use capture phase so we beat the browser's default Alt-menu handling.
  document.addEventListener('keydown', _captureKeydown, true)
  document.addEventListener('mousedown', _captureMousedown, true)
}

function cancelCapture() {
  if (!capturingAction.value) return
  capturingAction.value = ''
  document.removeEventListener('keydown', _captureKeydown, true)
  document.removeEventListener('mousedown', _captureMousedown, true)
}

function _captureMousedown(ev) {
  // Cancel if user clicks anywhere outside the active hotkey button.
  const action = capturingAction.value
  if (!action) return
  const target = ev.target
  if (target && target.closest && target.closest(`[data-action="${action}"]`)) {
    return
  }
  cancelCapture()
}

function _captureKeydown(ev) {
  if (!capturingAction.value) return
  ev.preventDefault()
  ev.stopPropagation()
  // Esc cancels (only when pressed alone)
  if (ev.key === 'Escape' && !ev.ctrlKey && !ev.altKey && !ev.shiftKey && !ev.metaKey) {
    cancelCapture()
    return
  }
  // Wait for a real main key — ignore lone modifier presses
  if (['Control', 'Alt', 'Shift', 'Meta', 'AltGraph'].includes(ev.key)) return
  const combo = _vkLabel(ev)
  if (!combo) return
  _submitCapture(capturingAction.value, combo)
}

async function _submitCapture(action, combo) {
  const prev = hotkeys[action]
  hotkeys[action] = combo  // optimistic display
  cancelCapture()
  const result = await api.setHotkey(action, combo)
  if (result && result.ok) {
    hotkeys[action] = result.combo || combo
    showHotkeyMsg(`✔ 已保存: ${hotkeys[action]}`)
  } else {
    hotkeys[action] = prev
    showHotkeyMsg((result && result.error) || '设置失败')
  }
}

function _vkLabel(ev) {
  // Build a combo string from KeyboardEvent
  const mods = []
  if (ev.ctrlKey) mods.push('Ctrl')
  if (ev.altKey) mods.push('Alt')
  if (ev.shiftKey) mods.push('Shift')
  if (ev.metaKey) mods.push('Win')
  let main = ''
  const code = ev.code || ''
  const key = ev.key || ''
  if (/^Key[A-Z]$/.test(code)) main = code.slice(3)
  else if (/^Digit[0-9]$/.test(code)) main = code.slice(5)
  else if (/^F([1-9]|1\d|2[0-4])$/.test(code)) main = code
  else if (code === 'Space') main = 'Space'
  else if (code === 'Enter' || code === 'NumpadEnter') main = 'Enter'
  else if (code === 'Tab') main = 'Tab'
  else if (code === 'Escape') main = 'Esc'
  else if (code === 'Backspace') main = 'Backspace'
  else if (code === 'Delete') main = 'Delete'
  else if (code === 'Insert') main = 'Insert'
  else if (code === 'Home') main = 'Home'
  else if (code === 'End') main = 'End'
  else if (code === 'PageUp') main = 'PageUp'
  else if (code === 'PageDown') main = 'PageDown'
  else if (code === 'ArrowUp') main = 'Up'
  else if (code === 'ArrowDown') main = 'Down'
  else if (code === 'ArrowLeft') main = 'Left'
  else if (code === 'ArrowRight') main = 'Right'
  else if (key && key.length === 1) main = key.toUpperCase()
  if (!main) return ''
  return [...mods, main].join('+')
}

async function onCaptureKey(ev, action) {
  // Deprecated: capture now happens via document-level listener installed
  // by startCapture(). Left as a no-op for backwards compatibility.
  return
}

async function clearHotkey(action) {
  // Deprecated: no clear button in UI anymore.
  return
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

function onKeybindKey(key, event) {
  let ch
  if (event.code === 'Space') {
    ch = 'Space'
  } else {
    ch = event.key.toUpperCase()
    if (!/^[A-Z0-9]$/.test(ch)) return
  }
  form.keybinds[key] = ch
  saveKeybinds()
}

async function saveKeybinds() {
  const binds = JSON.parse(JSON.stringify(form.keybinds))
  const result = await api.saveCombatKeybinds(binds)
  if (result && result.ok) {
    keybindSaved.value = true
    setTimeout(() => { keybindSaved.value = false }, 2000)
  }
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
  color: var(--section-header);
  margin-bottom: 12px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border-separator);
}

.info-row {
  display: flex;
  align-items: center;
  padding: 6px 0;
}

.info-label {
  width: 100px;
  color: var(--text-muted);
  font-size: 13px;
}

.info-value {
  color: var(--text-primary);
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
  color: var(--text-muted);
  font-size: 13px;
  flex-shrink: 0;
}

.setting-input {
  flex: 1;
  max-width: 250px;
  padding: 6px 10px;
  background: var(--bg-input);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: 13px;
}

.setting-input.narrow {
  max-width: 80px;
}

.setting-input:focus {
  outline: none;
  border-color: var(--status-info);
}

.keybind-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 24px;
}

.keybind-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.keybind-row label {
  width: 50px;
  color: var(--text-muted);
  font-size: 13px;
  text-align: right;
}

.keybind-input {
  width: 40px !important;
  max-width: 40px !important;
  text-align: center;
  text-transform: uppercase;
  font-weight: 600;
  font-size: 14px !important;
}

.path-row {
  display: flex;
  gap: 8px;
  flex: 1;
}

.path-input {
  max-width: 400px;
  color: var(--text-muted);
}

.setting-hint {
  color: var(--text-secondary);
  font-size: 12px;
  margin-top: 4px;
  margin-left: 132px;
}

.save-hint {
  color: var(--status-success);
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
  background: var(--toggle-off-bg);
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
  background: var(--toggle-knob-off);
  border-radius: 50%;
  transition: 0.2s;
}

.toggle-switch input:checked + .toggle-slider {
  background: var(--toggle-on-bg);
}

.toggle-switch input:checked + .toggle-slider::before {
  transform: translateX(18px);
  background: var(--toggle-knob-on);
}

/* Update banner */
.update-banner {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 10px;
  padding: 10px 14px;
  background: var(--status-success-bg);
  border: 1px solid var(--status-success);
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--status-success-text);
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

.update-msg.ok { color: var(--status-success); }
.update-msg.err { color: var(--status-error); }

.btn-sm {
  padding: 4px 12px;
  font-size: 12px;
}

.qr-row {
  margin-top: 10px;
  margin-left: 100px;
}

.qr-img {
  width: 120px;
  height: auto;
  max-height: 200px;
  object-fit: contain;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
}

.settings-footer {
  margin-top: 40px;
  padding-top: 16px;
  border-top: 1px solid var(--border-separator);
  text-align: center;
}

.footer-text {
  color: var(--text-secondary);
  font-size: 12px;
}

.footer-link {
  color: var(--text-link);
  text-decoration: none;
}

.footer-link:hover {
  text-decoration: underline;
}

/* Theme selector */
.theme-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 4px 0;
}

.theme-chip {
  padding: 5px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.theme-chip:hover {
  border-color: var(--border-hover);
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}

.theme-chip.active {
  border-color: var(--accent-1);
  background: var(--accent-tint);
  color: var(--accent-text);
}

.hotkey-btn {
  min-width: 160px;
  font-family: var(--font-mono, ui-monospace, monospace);
}

.hotkey-btn.capturing {
  outline: 2px solid var(--accent-1);
  outline-offset: 2px;
}
</style>
