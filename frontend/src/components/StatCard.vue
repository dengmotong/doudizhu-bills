<script setup>
defineProps({
  title: { type: String, default: '' },
  value: { type: [String, Number], default: '' },
  suffix: { type: String, default: '' },
  icon: { type: String, default: '' },
  color: { type: String, default: '' },
})
</script>

<template>
  <n-card size="small" :bordered="true" class="stat-card">
    <div class="stat-header">
      <span class="stat-title">{{ title }}</span>
      <span class="stat-icon">{{ icon }}</span>
    </div>
    <div class="stat-value mono" :style="color ? { color } : {}">
      {{ value }}<span v-if="suffix" class="stat-suffix">{{ suffix }}</span>
    </div>
  </n-card>
</template>

<style scoped>
.stat-card {
  height: 100%;
}
.stat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #909399;
  font-size: 13px;
}
.stat-icon {
  font-size: 18px;
}
.stat-value {
  margin-top: 8px;
  font-size: 26px;
  font-weight: 700;
  line-height: 1.2;
}
.stat-suffix {
  margin-left: 4px;
  font-size: 14px;
  color: #909399;
  font-weight: 500;
}
</style>
