import { computed, ref } from 'vue'

/**
 * 响应式断点（px），与各视图 <style> 中的 @media (max-width: 768px) 保持一致。
 *
 * - mobile   : <= 768px  手机。侧栏改为抽屉；栅格单列；表格横向滚动。
 * - tablet   : 768-1024px 平板。侧栏保留；栅格两列。
 * - desktop  : > 1024px  桌面。完整布局。
 */
export const MOBILE_MAX_WIDTH = 768
export const TABLET_MAX_WIDTH = 1024

const mobileQuery = `(max-width: ${MOBILE_MAX_WIDTH}px)`
const tabletQuery = `(min-width: ${MOBILE_MAX_WIDTH + 1}px) and (max-width: ${TABLET_MAX_WIDTH}px)`

/** 应用级共享状态，避免每个组件各建一个 MediaQueryList */
const isMobile = ref(false)
const isTablet = ref(false)
const isTouch = ref(false)
let initialized = false

function watchQuery(query, target) {
  const mql = window.matchMedia(query)
  target.value = mql.matches
  const onChange = (e) => {
    target.value = e.matches
  }
  // 兼容旧版 Safari 的 addListener
  if (mql.addEventListener) mql.addEventListener('change', onChange)
  else if (mql.addListener) mql.addListener(onChange)
}

function init() {
  if (initialized || typeof window === 'undefined' || !window.matchMedia) return
  initialized = true

  watchQuery(mobileQuery, isMobile)
  watchQuery(tabletQuery, isTablet)
  isTouch.value = window.matchMedia('(hover: none), (pointer: coarse)').matches
}

/**
 * 响应式布局信息。返回的是共享 ref，多处调用不会重复注册监听。
 * isNarrow = mobile || tablet，用于「窄屏统一降级」的场景。
 */
export function useIsMobile() {
  init()
  const isNarrow = computed(() => isMobile.value || isTablet.value)
  return { isMobile, isTablet, isNarrow, isTouch }
}
