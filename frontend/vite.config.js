import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        // 将体积较大的第三方库拆分为独立、可缓存的 chunk
        manualChunks: {
          vue: ['vue', 'vue-router'],
          naive: ['naive-ui', '@vicons/ionicons5'],
          echarts: ['echarts', 'vue-echarts'],
        },
      },
    },
  },
})
