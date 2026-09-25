import { computed, ref } from 'vue'
import { darkTheme, dateZhCN, zhCN } from 'naive-ui'

const STORAGE_KEY = 'dzz-theme'

const isDark = ref(localStorage.getItem(STORAGE_KEY) === 'dark')

function toggleDark() {
  isDark.value = !isDark.value
  localStorage.setItem(STORAGE_KEY, isDark.value ? 'dark' : 'light')
}

const theme = computed(() => (isDark.value ? darkTheme : null))
const locale = zhCN
const dateLocale = dateZhCN

// 统一的品牌主题（覆盖 primary 为主色调）
const themeOverrides = {
  common: {
    primaryColor: '#18a058',
    primaryColorHover: '#36ad6a',
    primaryColorPressed: '#0c7a43',
    primaryColorSuppl: '#18a058',
    borderRadius: '10px',
  },
  Button: {
    borderRadiusMedium: '8px',
  },
  Card: {
    borderRadius: '12px',
  },
}

export function useTheme() {
  return {
    isDark,
    toggleDark,
    theme,
    themeOverrides,
    locale,
    dateLocale,
  }
}
