<script setup>
import { computed, h, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  BarChartOutline,
  CashOutline,
  CloudUploadOutline,
  HomeOutline,
  ListOutline,
  MenuOutline,
  MoonOutline,
  PeopleOutline,
  SunnyOutline,
} from '@vicons/ionicons5'
import { NIcon } from 'naive-ui'
import { useTheme } from '@/composables/useTheme'
import { useIsMobile } from '@/composables/useIsMobile'

const route = useRoute()
const router = useRouter()
const { isDark, toggleDark, theme, themeOverrides, locale, dateLocale } = useTheme()
const { isMobile } = useIsMobile()

const collapsed = ref(false)
const drawerOpen = ref(false)

// 切到桌面端时收起抽屉，避免状态残留
watch(isMobile, (m) => {
  if (!m) drawerOpen.value = false
})

const iconMap = {
  home: HomeOutline,
  upload: CloudUploadOutline,
  records: ListOutline,
  players: PeopleOutline,
  stats: BarChartOutline,
  cash: CashOutline,
}

const renderIcon = (name) => {
  const comp = iconMap[name]
  return () => h(NIcon, null, { default: () => h(comp) })
}

const navItems = [
  { path: '/', title: '概览', icon: 'home' },
  { path: '/upload', title: '账单上传', icon: 'upload' },
  { path: '/records', title: '账单记录', icon: 'records' },
  { path: '/players', title: '玩家管理', icon: 'players' },
  { path: '/stats', title: '统计分析', icon: 'stats' },
  { path: '/settlement', title: '结账', icon: 'cash' },
]

const menuOptions = navItems.map((item) => ({
  label: item.title,
  key: item.path,
  icon: renderIcon(item.icon),
}))

const activeKey = computed(() => route.path)
const currentTitle = computed(() => route.meta?.title || '概览')
const siderBg = computed(() =>
  isDark.value
    ? 'linear-gradient(180deg, #17171c 0%, #101014 100%)'
    : 'linear-gradient(180deg, #fbfcfe 0%, #f1f4f9 100%)',
)

function handleMenuSelect(key) {
  drawerOpen.value = false
  if (key !== route.path) router.push(key)
}
</script>

<template>
  <n-config-provider
    :theme="theme"
    :theme-overrides="themeOverrides"
    :locale="locale"
    :date-locale="dateLocale"
  >
    <n-message-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <n-layout has-sider position="absolute" style="height: 100vh">
            <!-- 桌面端：常驻侧栏 -->
            <n-layout-sider
              v-if="!isMobile"
              bordered
              collapse-mode="width"
              :collapsed-width="64"
              :width="220"
              :collapsed="collapsed"
              show-trigger
              :native-scrollbar="false"
              :style="{ background: siderBg }"
              @collapse="collapsed = true"
              @expand="collapsed = false"
            >
              <div class="sider-logo" :class="{ 'sider-logo--collapsed': collapsed }">
                <span class="logo-emoji">🃏</span>
                <span v-if="!collapsed" class="logo-text">斗地主账单</span>
              </div>
              <n-menu
                :value="activeKey"
                :options="menuOptions"
                :collapsed="collapsed"
                :collapsed-width="64"
                :collapsed-icon-size="20"
                @update:value="handleMenuSelect"
              />
            </n-layout-sider>

            <n-layout :native-scrollbar="false" style="height: 100vh">
              <n-layout-header bordered class="app-header">
                <!-- 移动端：汉堡菜单唤起抽屉导航 -->
                <n-button
                  v-if="isMobile"
                  quaternary
                  circle
                  class="header-menu-btn"
                  aria-label="打开导航菜单"
                  @click="drawerOpen = true"
                >
                  <template #icon>
                    <n-icon :component="MenuOutline" />
                  </template>
                </n-button>

                <div class="header-title">{{ currentTitle }}</div>
                <div class="header-actions">
                  <n-tooltip>
                    <template #trigger>
                      <n-button quaternary circle @click="toggleDark">
                        <template #icon>
                          <n-icon :component="isDark ? SunnyOutline : MoonOutline" />
                        </template>
                      </n-button>
                    </template>
                    {{ isDark ? '切换到浅色模式' : '切换到深色模式' }}
                  </n-tooltip>
                </div>
              </n-layout-header>

              <n-layout-content
                :native-scrollbar="false"
                :content-style="isMobile ? 'padding: 12px 12px 32px;' : 'padding: 22px 24px 40px;'"
              >
                <router-view v-slot="{ Component }">
                  <transition name="fade-in" mode="out-in">
                    <component :is="Component" />
                  </transition>
                </router-view>
              </n-layout-content>
            </n-layout>

            <!-- 移动端抽屉导航 -->
            <n-drawer v-model:show="drawerOpen" :width="260" placement="left">
              <n-drawer-content :native-scrollbar="false" body-content-style="padding: 0;">
                <div class="drawer-logo">
                  <span class="logo-emoji">🃏</span>
                  <span class="logo-text">斗地主账单</span>
                </div>
                <n-menu
                  :value="activeKey"
                  :options="menuOptions"
                  :indent="20"
                  @update:value="handleMenuSelect"
                />
              </n-drawer-content>
            </n-drawer>
          </n-layout>
        </n-notification-provider>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<style scoped>
.sider-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 56px;
  padding: 0 18px;
  overflow: hidden;
  white-space: nowrap;
}
.sider-logo--collapsed {
  justify-content: center;
  padding: 0;
}
.logo-emoji {
  font-size: 24px;
  flex-shrink: 0;
}
.logo-text {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 1px;
}
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 24px;
  backdrop-filter: saturate(1.6) blur(20px);
}
.header-title {
  font-size: 17px;
  font-weight: 700;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.drawer-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 56px;
  padding: 0 20px;
  border-bottom: 1px solid var(--n-border-color, rgba(128, 128, 128, 0.16));
}
.header-menu-btn {
  margin-right: 4px;
}

/* ---- 移动端适配 ---- */
@media (max-width: 768px) {
  .app-header {
    /* 固定 52px 内容区 + 刘海屏安全区 */
    height: calc(52px + env(safe-area-inset-top, 0px));
    padding: 0 12px;
    padding-top: env(safe-area-inset-top, 0px);
  }
  .header-title {
    font-size: 16px;
    /* 让标题在汉堡按钮与主题按钮之间居中，过长时省略 */
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    padding: 0 8px;
  }
  .drawer-logo {
    padding-top: env(safe-area-inset-top, 0);
    height: calc(56px + env(safe-area-inset-top, 0px));
  }
}
</style>
