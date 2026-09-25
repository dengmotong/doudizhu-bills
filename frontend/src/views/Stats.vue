<script setup>
import { computed, onMounted, ref } from 'vue'
import VChart from 'vue-echarts'
import { fetchCumulativeStats, fetchDailyStats, fetchSessionStats } from '@/api'
import WinLossPill from '@/components/WinLossPill.vue'

const loading = ref(true)
const cumulative = ref([])
const daily = ref([])
const session = ref([])
const gran = ref('day') // day / week / month

const granOptions = [
  { label: '按日', value: 'day' },
  { label: '按周', value: 'week' },
  { label: '按月', value: 'month' },
]

// ---- 日期/桶工具 ----
function fmtDate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}
function weekStartStr(dateStr) {
  const d = new Date(`${dateStr}T00:00:00`)
  const day = (d.getDay() + 6) % 7
  d.setDate(d.getDate() - day)
  return fmtDate(d)
}
function bucketOf(g, dateStr) {
  if (g === 'month') return dateStr.slice(0, 7)
  if (g === 'week') return weekStartStr(dateStr)
  return dateStr
}
function bucketLabel(g, key) {
  const [y, m, d] = key.split('-')
  if (g === 'month') return `${y}年${Number(m)}月`
  if (g === 'week') return `${y}年${Number(m)}月${Number(d)}日起`
  return `${y}年${Number(m)}月${Number(d)}日`
}

const trendKeys = computed(() => [...new Set(daily.value.map((r) => bucketOf(gran.value, r.day)))].sort())
const trendPlayers = computed(() => [...new Set(daily.value.map((r) => r.player_name))])
const trendLabels = computed(() => trendKeys.value.map((k) => bucketLabel(gran.value, k)))

function perPlayerSeries(accum) {
  const map = {}
  for (const p of trendPlayers.value) map[p] = trendKeys.value.map(() => 0)
  for (const r of daily.value) {
    const k = bucketOf(gran.value, r.day)
    const idx = trendKeys.value.indexOf(k)
    if (idx >= 0) map[r.player_name][idx] += r.total_points || 0
  }
  if (!accum) return map
  const out = {}
  for (const p of trendPlayers.value) {
    let acc = 0
    out[p] = map[p].map((v) => (acc += v))
  }
  return out
}

const baseGrid = { left: 44, right: 20, top: 44, bottom: 44 }

const trendLine = computed(() => {
  const s = perPlayerSeries(false)
  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 0, type: 'scroll' },
    grid: baseGrid,
    xAxis: { type: 'category', data: trendLabels.value },
    yAxis: { type: 'value', name: '分数' },
    series: trendPlayers.value.map((p) => ({ name: p, type: 'line', smooth: false, data: s[p] })),
  }
})

const cumLine = computed(() => {
  const s = perPlayerSeries(true)
  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 0, type: 'scroll' },
    grid: baseGrid,
    xAxis: { type: 'category', data: trendLabels.value },
    yAxis: { type: 'value', name: '累计分数' },
    series: trendPlayers.value.map((p) => ({ name: p, type: 'line', smooth: false, data: s[p] })),
  }
})

const trendBar = computed(() => {
  const s = perPlayerSeries(false)
  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 0, type: 'scroll' },
    grid: baseGrid,
    xAxis: { type: 'category', data: trendLabels.value },
    yAxis: { type: 'value', name: '分数' },
    series: trendPlayers.value.map((p) => ({ name: p, type: 'bar', data: s[p], barMaxWidth: 18 })),
  }
})

const periodNet = computed(() => {
  const s = perPlayerSeries(false)
  const totals = trendKeys.value.map((_, i) => trendPlayers.value.reduce((sum, p) => sum + (s[p][i] || 0), 0))
  return {
    tooltip: { trigger: 'axis' },
    grid: baseGrid,
    xAxis: { type: 'category', data: trendLabels.value },
    yAxis: { type: 'value', name: '净额' },
    series: [{
      type: 'bar',
      data: totals,
      barMaxWidth: 42,
      itemStyle: { borderRadius: [6, 6, 0, 0], color: (p) => (p.value >= 0 ? '#18a058' : '#d03050') },
    }],
  }
})

const trendTable = computed(() => {
  const s = perPlayerSeries(false)
  const totals = trendKeys.value.map((_, i) => trendPlayers.value.reduce((sum, p) => sum + (s[p][i] || 0), 0))
  return trendKeys.value.map((_, i) => {
    const row = { period: trendLabels.value[i], net: totals[i] }
    for (const p of trendPlayers.value) row[p] = s[p][i]
    return row
  })
})

const columns = computed(() => [
  { title: '期间', key: 'period' },
  ...trendPlayers.value.map((p) => ({ title: p, key: p })),
  { title: '总净额', key: 'net' },
])

// ---- 累计排名 ----
const cumBar = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 44, right: 20, top: 30, bottom: 44 },
  xAxis: { type: 'category', data: cumulative.value.map((s) => s.player_name), axisLabel: { interval: 0, rotate: 22 } },
  yAxis: { type: 'value', name: '累计分数' },
  series: [{
    type: 'bar',
    data: cumulative.value.map((s) => s.total_points),
    barMaxWidth: 42,
    itemStyle: { borderRadius: [6, 6, 0, 0], color: (p) => (p.value >= 0 ? '#18a058' : '#d03050') },
  }],
}))

const cumPie = computed(() => ({
  tooltip: { trigger: 'item' },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    data: cumulative.value.map((s) => ({ name: s.player_name, value: s.game_count || 0 })),
  }],
}))

// ---- 按局 ----
const sessionGroups = computed(() => {
  const map = {}
  for (const r of session.value) {
    const key = `${r.game_session_id}`
    if (!map[key]) map[key] = { id: r.game_session_id, game_date: r.game_date, game_time: r.game_time, rows: [] }
    map[key].rows.push(r)
  }
  return Object.values(map)
})

function pieFor(rows) {
  const pos = rows.filter((r) => r.win_points > 0)
  return {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '68%'],
      data: pos.map((r) => ({ name: r.player_name, value: r.win_points })),
    }],
  }
}

async function load() {
  loading.value = true
  try {
    const [c, d, s] = await Promise.all([fetchCumulativeStats(), fetchDailyStats(), fetchSessionStats()])
    cumulative.value = c
    daily.value = d
    session.value = s
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-title">
      <n-h2 style="margin: 0">📊 统计分析</n-h2>
    </div>
    <n-p style="color: #909399; margin-top: 4px">累计排名 · 日/周/月趋势 · 按局统计，多维度反映对局情况。</n-p>

    <n-spin :show="loading">
      <n-empty v-if="!cumulative.length && !daily.length" description="暂无数据，请先上传账单" style="margin-top: 60px" />

      <template v-else>
        <!-- ===== 累计排名 ===== -->
        <n-card :bordered="true" size="small" style="margin-top: 16px">
          <template #header><span class="section-title">🏆 累计排名</span></template>
          <n-grid :cols="2" :x-gap="16" :y-gap="16" responsive="screen" item-responsive>
            <n-grid-item :span="1" :xs="2">
              <n-card title="累计分数" size="small"><v-chart v-if="cumulative.length" :option="cumBar" autoresize style="height: 340px" /></n-card>
            </n-grid-item>
            <n-grid-item :span="1" :xs="2">
              <n-card title="对局数占比" size="small"><v-chart v-if="cumulative.length" :option="cumPie" autoresize style="height: 340px" /></n-card>
            </n-grid-item>
          </n-grid>
          <n-data-table
            v-if="cumulative.length"
            :columns="[
              { title: '玩家', key: 'player_name' },
              { title: '累计分数', key: 'total_points' },
              { title: '对局数', key: 'game_count' },
              { title: '地主胜率', key: 'l_rate' },
              { title: '农民胜率', key: 'f_rate' },
              { title: '首次参与', key: 'first_game' },
              { title: '最近参与', key: 'last_game' },
            ]"
            :data="cumulative.map((s) => ({
              player_name: s.player_name,
              total_points: s.total_points,
              game_count: s.game_count,
              l_rate: s.total_landlord > 0 ? `${((s.total_landlord_win / s.total_landlord) * 100).toFixed(0)}%` : '-',
              f_rate: s.total_farmer > 0 ? `${((s.total_farmer_win / s.total_farmer) * 100).toFixed(0)}%` : '-',
              first_game: s.first_game,
              last_game: s.last_game,
            }))"
            size="small"
            striped
            style="margin-top: 16px"
          />
        </n-card>

        <!-- ===== 趋势分析 ===== -->
        <n-card :bordered="true" size="small" style="margin-top: 16px">
          <template #header>
            <div class="trend-head">
              <span class="section-title">📈 趋势分析</span>
              <n-radio-group v-model:value="gran">
                <n-radio-button v-for="opt in granOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</n-radio-button>
              </n-radio-group>
            </div>
          </template>
          <n-empty v-if="!daily.length" description="暂无趋势数据" style="margin-top: 20px" />
          <template v-else>
            <n-grid :cols="2" :x-gap="16" :y-gap="16" responsive="screen" item-responsive>
              <n-grid-item :span="1" :xs="2">
                <n-card title="各玩家分数趋势" size="small"><v-chart :option="trendLine" autoresize style="height: 340px" /></n-card>
              </n-grid-item>
              <n-grid-item :span="1" :xs="2">
                <n-card title="各玩家累计趋势" size="small"><v-chart :option="cumLine" autoresize style="height: 340px" /></n-card>
              </n-grid-item>
              <n-grid-item :span="1" :xs="2">
                <n-card title="各玩家分数对比" size="small"><v-chart :option="trendBar" autoresize style="height: 320px" /></n-card>
              </n-grid-item>
              <n-grid-item :span="1" :xs="2">
                <n-card title="每期净额（全体合计）" size="small"><v-chart :option="periodNet" autoresize style="height: 320px" /></n-card>
              </n-grid-item>
            </n-grid>
            <n-card title="明细汇总" size="small" style="margin-top: 16px">
              <n-data-table v-if="trendTable.length" :columns="columns" :data="trendTable" size="small" striped />
            </n-card>
          </template>
        </n-card>

        <!-- ===== 按局统计 ===== -->
        <n-card :bordered="true" size="small" style="margin-top: 16px">
          <template #header><span class="section-title">🎮 按局统计</span></template>
          <n-empty v-if="!sessionGroups.length" description="暂无数据" style="margin-top: 20px" />
          <n-collapse v-else>
            <n-collapse-item v-for="g in sessionGroups" :key="g.id">
              <template #header>
                <div class="sess-head">
                  <span class="mono">{{ g.game_date }}</span>
                  <n-tag v-if="g.game_time" size="tiny" :bordered="false">{{ g.game_time }}</n-tag>
                </div>
              </template>
              <n-grid :cols="2" :x-gap="16" item-responsive responsive="screen">
                <n-grid-item :span="1" :xs="2">
                  <div class="sess-players">
                    <div v-for="r in [...g.rows].sort((a, b) => b.win_points - a.win_points)" :key="r.player_name" class="sess-player">
                      <span>{{ r.player_name }}</span>
                      <WinLossPill :value="r.win_points" />
                    </div>
                  </div>
                </n-grid-item>
                <n-grid-item :span="1" :xs="2">
                  <v-chart v-if="g.rows.some((r) => r.win_points > 0)" :option="pieFor(g.rows)" autoresize style="height: 220px" />
                  <n-empty v-else description="本局无赢家" size="small" style="height: 220px" />
                </n-grid-item>
              </n-grid>
            </n-collapse-item>
          </n-collapse>
        </n-card>
      </template>
    </n-spin>
  </div>
</template>

<style scoped>
.section-title {
  font-weight: 800;
  font-size: 16px;
}
.trend-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.sess-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}
.sess-players {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sess-player {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
