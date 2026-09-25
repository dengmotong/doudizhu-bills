import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '概览', icon: 'home' } },
  { path: '/upload', name: 'upload', component: () => import('@/views/BillUpload.vue'), meta: { title: '账单上传', icon: 'upload' } },
  { path: '/records', name: 'records', component: () => import('@/views/BillRecords.vue'), meta: { title: '账单记录', icon: 'records' } },
  { path: '/players', name: 'players', component: () => import('@/views/Players.vue'), meta: { title: '玩家管理', icon: 'players' } },
  { path: '/stats', name: 'stats', component: () => import('@/views/Stats.vue'), meta: { title: '统计分析', icon: 'stats' } },
  { path: '/settlement', name: 'settlement', component: () => import('@/views/Settlement.vue'), meta: { title: '结账', icon: 'cash' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  document.title = to.meta?.title ? `${to.meta.title} · 斗地主账单系统` : '斗地主账单系统'
  window.scrollTo(0, 0)
})

export default router
