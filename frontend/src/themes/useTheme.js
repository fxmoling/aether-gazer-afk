import { ref } from 'vue'
import { api } from '../composables/useApi'
import { themes, DEFAULT_THEME } from './registry'

const currentTheme = ref(DEFAULT_THEME)

function applyTheme(themeId) {
  document.documentElement.setAttribute('data-theme', themeId)
  currentTheme.value = themeId
}

export function useTheme() {
  async function setTheme(themeId) {
    applyTheme(themeId)
    try { await api.setTheme(themeId) } catch (e) { console.warn('[useTheme] persist failed:', e) }
  }

  async function loadTheme() {
    try {
      const settings = await api.getSettings()
      applyTheme(settings?.theme || DEFAULT_THEME)
    } catch { applyTheme(DEFAULT_THEME) }
  }

  return { currentTheme, setTheme, loadTheme, themeList: themes }
}
