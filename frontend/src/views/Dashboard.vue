<script setup>
import { computed, onMounted, ref } from 'vue'
import VChart from 'vue-echarts'
import { fetchBills, fetchCumulativeStats, fetchPlayers, fetchSessions } from '@/api'
import StatCard from '@/components/StatCard.vue'
import WinLossPill from '@/components/WinLossPill.vue'

const players = ref([])
const bills = ref([])
const stats = ref([])
const sessions = ref([])
const loading = ref(true)

const playerCount = computed(() => players.value.length)
const billCount = computed(() => bills.value.length)
const totalScore = computed(() => bills.value.reduce((s, b) => s + (b.win_points || 0), 0))
const unsettledCount = computed(() => sessions.value.filter((s) => !s.session.settled).length)
const maxAbs = computed(() => Math.max(1, ...stats.value.map((s) => Math.abs(s.total_points || 0))))

const medal = (i) => (i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i + 1}`)

const barOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 44, right: 20, top: 30, bottom: 40 },
  xAxis: {
    type: 'category',
    data: stats.value.map((s) => s.player_name),
    axisLabel: { interval: 0, rotate: 22 },
  },
  yAxis: { type: 'value', name: '累计分数' },
  series: [
    {
      type: 'bar',
      data: stats.value.map((s) => s.total_points),
      barMaxWidth: 42,
      itemStyle: {
        borderRadius: [6, 6, 0, 0],
        color: (p) => (p.value >= 0 ? '#18a058' : '#d03050'),
      },
    },
  ],
}))

async function load() {
  loading.value = true
  try {
    const [p, b, st, ss] = await Promise.all([
      fetchPlayers(),
      fetchBills(),
      fetchCumulativeStats(),
      fetchSessions(),
    ])
    players.value = p
    bills.value = b
    stats.value = st
    sessions.value = ss
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-title">
      <n-h2 style="margin: 0">📊 概览</n-h2>
      <n-tag round type="success" size="small">斗地主账单系统</n-tag>
    </div>
    <n-p style="color: #909399; margin-top: 4px">上传结算截图、跟踪分数、一键结账。</n-p>

    <n-spin :show="loading">
      <n-grid :cols="4" :x-gap="14" :y-gap="14" responsive="screen" item-responsive style="margin-top: 16px">
        <n-grid-item :span="1" :m="2" :s="4" :xs="2">
          <StatCard title="玩家总数" :value="playerCount" icon="👥" color="#18a058" />
        </n-grid-item>
        <n-grid-item :span="1" :m="2" :s="4" :xs="2">
          <StatCard title="账单总数" :value="billCount" icon="📋" color="#2080f0" />
        </n-grid-item>
        <n-grid-item :span="1" :m="2" :s="4" :xs="2">
          <StatCard title="总分数" :value="totalScore.toFixed(0)" :suffix="totalScore >= 0 ? '分' : '分'" icon="🎯" color="#f0a020" />
        </n-grid-item>
        <n-grid-item :span="1" :m="2" :s="4" :xs="2">
          <StatCard title="待结账对局" :value="unsettledCount" icon="💰" color="#d03050" />
        </n-grid-item>
      </n-grid>

      <n-grid :cols="2" :x-gap="16" :y-gap="16" responsive="screen" item-responsive style="margin-top: 16px">
        <n-grid-item :span="1" :s="1" :xs="1">
          <n-card title="🏆 玩家排名" size="small">
            <template v-if="stats.length">
              <div v-for="(s, i) in stats" :key="s.player_name" class="rank-row">
                <span class="rank-col" :style="{ background: i < 3 ? 'rgba(24,160,88,.16)' : 'rgba(128,128,128,.12)' }">
                  {{ medal(i) }}
                </span>
                <div class="rank-main">
                  <div class="rank-line">
                    <span class="rank-name">{{ s.player_name }}</span>
                    <span class="rank-score mono" :style="{ color: s.total_points >= 0 ? '#18a058' : '#d03050' }">
                      {{ s.total_points >= 0 ? '+' : '' }}{{ s.total_points.toFixed(0) }} 分
                    </span>
                  </div>
                  <div class="rank-bar">
                    <div
                      class="rank-bar-fill"
                      :style="{
                        width: (Math.abs(s.total_points) / maxAbs) * 100 + '%',
                        background: s.total_points >= 0 ? 'linear-gradient(90deg,#18a058,#36ad6a)' : 'linear-gradient(90deg,#d03050,#e88080)',
                      }"
                    />
                  </div>
                </div>
              </div>
            </template>
            <n-empty v-else description="暂无数据，请先上传账单" />
          </n-card>
        </n-grid-item>

        <n-grid-item :span="1" :s="1" :xs="1">
          <n-card title="📈 累计分数对比" size="small">
            <v-chart v-if="stats.length" :option="barOption" autoresize style="height: 320px" />
            <n-empty v-else description="暂无图表数据" style="height: 320px" />
          </n-card>
        </n-grid-item>
      </n-grid>

      <n-card title="🕐 最近对局" size="small" style="margin-top: 16px">
        <n-empty v-if="!sessions.length" description="暂无对局记录" />
        <div v-for="s in sessions.slice(0, 6)" :key="s.session.id" class="recent-row">
          <div class="recent-date">
            <span class="recent-day">{{ s.session.game_date }}</span>
            <n-tag v-if="s.session.game_time" size="tiny" :bordered="false">{{ s.session.game_time }}</n-tag>
            <n-tag v-if="s.session.settled" size="tiny" type="success" :bordered="false">已结账</n-tag>
          </div>
          <div class="recent-players">
            <WinLossPill
              v-for="b in s.bills"
              :key="b.id"
              :value="b.win_points"
              :money="s.session.settled ? b.win_points * s.session.price_per_point : null"
            />
          </div>
        </div>
      </n-card>
    </n-spin>
  </div>
</template>

<style scoped>
.rank-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--n-divider-color, rgba(128, 128, 128, 0.1));
}
.rank-row:last-child {
  border-bottom: none;
}
.rank-main {
  flex: 1;
  min-width: 0;
}
.rank-line {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.rank-name {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rank-score {
  font-weight: 700;
  font-size: 14px;
}
.rank-bar {
  height: 6px;
  margin-top: 6px;
  border-radius: 6px;
  background: rgba(128, 128, 128, 0.12);
  overflow: hidden;
}
.rank-bar-fill {
  height: 100%;
  border-radius: 6px;
  transition: width 0.5s ease;
}
.recent-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--n-divider-color, rgba(128, 128, 128, 0.1));
}
.recent-row:last-child {
  border-bottom: none;
}
.recent-date {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 160px;
}
.recent-day {
  font-weight: 600;
}
.recent-players {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: flex-end;
}
</style>
