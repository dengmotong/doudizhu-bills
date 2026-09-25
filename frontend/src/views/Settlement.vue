<script setup>
import { computed, onMounted, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { batchSettle, fetchSessions, settleSingle, unsettleSingle } from '@/api'
import WinLossPill from '@/components/WinLossPill.vue'

const message = useMessage()
const sessions = ref([])
const loading = ref(true)
const ppp = ref(5)
const batchIds = ref([])
const batchResult = ref(null)
const working = ref(false)

const unsettled = computed(() => sessions.value.filter((s) => !s.session.settled))
const settled = computed(() => sessions.value.filter((s) => s.session.settled))

const batchOptions = computed(() =>
  unsettled.value.map((s) => ({
    label: `${s.session.game_date} ${s.session.game_time || ''} (ID:${s.session.id})`,
    value: s.session.id,
  })),
)

function toggleSelectAll() {
  if (batchIds.value.length && batchIds.value.length === unsettled.value.length) {
    batchIds.value = []
  } else {
    batchIds.value = unsettled.value.map((s) => s.session.id)
  }
}

function getScores(bills) {
  const scores = {}
  for (const b of bills) scores[b.player_name] = (scores[b.player_name] || 0) + (Number(b.win_points) || 0)
  return Object.fromEntries(Object.entries(scores).filter(([, v]) => Math.abs(v) > 0.001))
}

function calcTransfers(scores, price) {
  const winners = Object.entries(scores)
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1])
  const losers = Object.entries(scores)
    .filter(([, v]) => v < 0)
    .map(([k, v]) => [k, -v])
    .sort((a, b) => b[1] - a[1])
  const transfers = []
  let wi = 0
  let li = 0
  while (wi < winners.length && li < losers.length) {
    let [wn, wp] = winners[wi]
    let [ln, lp] = losers[li]
    const t = Math.min(wp, lp)
    if (t > 0.001) transfers.push({ from: ln, to: wn, points: t, money: Math.round(t * price * 100) / 100 })
    winners[wi] = [wn, wp - t]
    losers[li] = [ln, lp - t]
    if (winners[wi][1] < 0.001) wi++
    if (losers[li][1] < 0.001) li++
  }
  return transfers
}

const batchScores = computed(() => {
  if (!batchIds.value.length) return null
  const bills = []
  for (const sid of batchIds.value) {
    const s = sessions.value.find((x) => x.session.id === sid)
    if (s) bills.push(...s.bills)
  }
  return getScores(bills)
})

const batchTransfers = computed(() =>
  batchScores.value ? calcTransfers(batchScores.value, ppp.value) : [],
)

function sessResult(s) {
  const scores = getScores(s.bills)
  const transfers = calcTransfers(scores, s.session.settled ? s.session.price_per_point : ppp.value)
  return { scores, transfers }
}

async function refresh() {
  loading.value = true
  try {
    sessions.value = await fetchSessions()
  } finally {
    loading.value = false
  }
}

async function doSettle(s) {
  working.value = true
  try {
    await settleSingle(s.session.id, ppp.value)
    message.success('已结账')
    batchIds.value = []
    batchResult.value = null
    await refresh()
  } catch (e) {
    message.error(e.message)
  } finally {
    working.value = false
  }
}

async function doBatchSettle() {
  if (!batchIds.value.length) return message.warning('请选择对局')
  working.value = true
  try {
    await batchSettle(batchIds.value, ppp.value)
    message.success(`已结账 ${batchIds.value.length} 局`)
    batchIds.value = []
    batchResult.value = null
    await refresh()
  } catch (e) {
    message.error(e.message)
  } finally {
    working.value = false
  }
}

async function doUnsettle(s) {
  try {
    await unsettleSingle(s.session.id)
    message.success('已取消结账')
    await refresh()
  } catch (e) {
    message.error(e.message)
  }
}

function sortedScores(scores) {
  return Object.entries(scores).sort((a, b) => b[1] - a[1])
}

onMounted(refresh)
</script>

<template>
  <div>
    <div class="page-title">
      <n-h2 style="margin: 0">💰 结账</n-h2>
      <n-tag round type="warning" size="small">{{ unsettled.length }} 待结账</n-tag>
    </div>
    <n-p style="color: #909399; margin-top: 4px">选择对局，计算最优转账方案，标记已结账。</n-p>

    <n-spin :show="loading">
      <n-empty v-if="!sessions.length" description="暂无对局记录" style="margin-top: 60px" />

      <template v-else>
        <!-- 待结账 -->
        <n-card :bordered="true" size="small" style="margin-top: 16px" title="⏳ 待结账对局">
          <n-space align="center" style="margin-bottom: 12px">
            <n-select
              v-model:value="batchIds"
              multiple
              :options="batchOptions"
              placeholder="选择要合并结账的对局"
              clearable
              style="min-width: 340px"
            />
            <n-button size="small" secondary @click="toggleSelectAll">
              {{ batchIds.length && batchIds.length === unsettled.length ? '清空' : '全选' }}
            </n-button>
            <n-input-number v-model:value="ppp" :min="0.1" :step="0.5" size="small" style="width: 140px" footer="每分单价" />
            <n-button type="success" :loading="working" :disabled="!batchIds.length" @click="doBatchSettle">
              ✅ 确认批量结账
            </n-button>
          </n-space>

          <template v-if="batchIds.length && batchScores">
            <n-divider style="margin: 8px 0" />
            <n-grid :cols="2" :x-gap="16" item-responsive responsive="screen">
              <n-grid-item :span="1" :xs="2">
                <n-text depth="3" size="small" style="font-weight: 700">各玩家总分数</n-text>
                <div v-for="[name, pts] in sortedScores(batchScores)" :key="name" class="score-line">
                  <span>{{ name }}</span>
                  <WinLossPill :value="pts" :money="Math.round(pts * ppp * 100) / 100" />
                </div>
              </n-grid-item>
              <n-grid-item :span="1" :xs="2">
                <n-text depth="3" size="small" style="font-weight: 700">最优转账方案（{{ batchTransfers.length }} 笔）</n-text>
                <div v-for="(t, i) in batchTransfers" :key="i" class="transfer-line">
                  <span class="transfer-arrow">{{ t.from }} → {{ t.to }}</span>
                  <span class="mono">{{ t.points.toFixed(0) }}分 (¥{{ t.money.toFixed(2) }})</span>
                </div>
                <n-empty v-if="!batchTransfers.length" description="分数相同，无需转账" size="small" />
              </n-grid-item>
            </n-grid>
          </template>

          <n-divider style="margin: 12px 0" />

          <n-empty v-if="!unsettled.length" description="没有待结账的对局" />
          <div v-for="s in unsettled" :key="s.session.id" class="settle-item">
            <n-collapse>
              <n-collapse-item>
                <template #header>
                  <div class="settle-head">
                    <span class="mono">{{ s.session.game_date }}</span>
                    <n-tag v-if="s.session.game_time" size="tiny" :bordered="false">{{ s.session.game_time }}</n-tag>
                  </div>
                </template>
                <template #header-extra>
                  <n-button size="tiny" type="success" :loading="working" @click.stop="doSettle(s)">✅ 结账</n-button>
                </template>
                <n-grid :cols="2" :x-gap="16" item-responsive responsive="screen">
                  <n-grid-item :span="1" :xs="2">
                    <n-text depth="3" size="small" style="font-weight: 700">各玩家分数</n-text>
                    <div v-for="[name, pts] in sortedScores(sessResult(s).scores)" :key="name" class="score-line">
                      <span>{{ name }}</span>
                      <WinLossPill :value="pts" :money="Math.round(pts * ppp * 100) / 100" />
                    </div>
                  </n-grid-item>
                  <n-grid-item :span="1" :xs="2">
                    <n-text depth="3" size="small" style="font-weight: 700">转账方案</n-text>
                    <div v-for="(t, i) in sessResult(s).transfers" :key="i" class="transfer-line">
                      <span class="transfer-arrow">{{ t.from }} → {{ t.to }}</span>
                      <span class="mono">{{ t.points.toFixed(0) }}分 (¥{{ t.money.toFixed(2) }})</span>
                    </div>
                    <n-empty v-if="!sessResult(s).transfers.length" description="分数相同，无需转账" size="small" />
                  </n-grid-item>
                </n-grid>
              </n-collapse-item>
            </n-collapse>
          </div>
        </n-card>

        <!-- 已结账 -->
        <n-card :bordered="true" size="small" style="margin-top: 16px" title="✅ 已结账对局">
          <n-empty v-if="!settled.length" description="暂无已结账对局" />
          <div v-for="s in settled" :key="s.session.id" class="settle-item">
            <n-collapse>
              <n-collapse-item>
                <template #header>
                  <div class="settle-head">
                    <span class="mono">{{ s.session.game_date }}</span>
                    <n-tag v-if="s.session.game_time" size="tiny" :bordered="false">{{ s.session.game_time }}</n-tag>
                    <n-tag size="tiny" type="success" :bordered="false">✅ 已结账</n-tag>
                  </div>
                </template>
                <template #header-extra>
                  <n-button size="tiny" quaternary type="warning" @click.stop="doUnsettle(s)">↩️ 取消结账</n-button>
                </template>
                <div v-for="(t, i) in sessResult(s).transfers" :key="i" class="transfer-line">
                  <span class="transfer-arrow">{{ t.from }} → {{ t.to }}</span>
                  <span class="mono">{{ t.points.toFixed(0) }}分 (¥{{ t.money.toFixed(2) }})</span>
                </div>
                <n-text depth="3" size="small">结账时间：{{ s.session.settled_at || '-' }} · 单价 ¥{{ s.session.price_per_point }}/分</n-text>
              </n-collapse-item>
            </n-collapse>
          </div>
        </n-card>
      </template>
    </n-spin>
  </div>
</template>

<style scoped>
.settle-item {
  margin-bottom: 8px;
}
.settle-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
}
.score-line,
.transfer-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 5px 0;
  border-bottom: 1px solid rgba(128, 128, 128, 0.08);
}
.score-line:last-child,
.transfer-line:last-child {
  border-bottom: none;
}
.transfer-arrow {
  font-weight: 600;
}
</style>
