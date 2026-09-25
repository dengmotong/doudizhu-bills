<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  suffix: { type: String, default: '分' },
  money: { type: [Number, null], default: null },
})

const isPos = computed(() => props.value >= 0)
</script>

<template>
  <span class="pill mono" :class="isPos ? 'pill--pos' : 'pill--neg'">
    {{ isPos ? '+' : '' }}{{ value.toFixed(0) }}{{ suffix }}
    <span v-if="money != null" class="pill-money">¥{{ money.toFixed(0) }}</span>
  </span>
</template>

<style scoped>
.pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 999px;
  font-weight: 700;
  font-size: 13px;
  line-height: 1.2;
  white-space: nowrap;
}
.pill--pos {
  color: #18a058;
  background: rgba(24, 160, 88, 0.12);
}
.pill--neg {
  color: #d03050;
  background: rgba(208, 48, 80, 0.12);
}
.pill-money {
  font-weight: 500;
  opacity: 0.82;
  font-size: 12px;
}
</style>
