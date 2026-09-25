<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { deleteBill, deleteSession, fetchPlayers, fetchSessions, imageUrl, updateBill } from '@/api'
import WinLossPill from '@/components/WinLossPill.vue'

const message = useMessage()

const sessions = ref([])
const players = ref([])
const loading = ref(true)

const filters = reactive({ players: [], dateRange: null, sort: 'newest' })

// 每局：详情状态 / 整局编辑状态 / 整局草稿 { date, time, bills }
const showDetail = reactive({})
const sessionEdit = reactive({})
const sessionDrafts = reactive({})

const playerChoices = computed(() => players.value.map((p) => ({ label: p.name, value: p.name })))
const playerNameToId = computed(() => Object.fromEntries(players.value.map((p) => [p.name, p.id])))

function normDate(v) {
  if (typeof v === 'number') {
    const d = new Date(v)
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${dd}`
  }
  return v
}

const filteredSessions = computed(() => {
  let list = sessions.value
  if (filters.players.length) {
    list = list
      .map((s) => ({ ...s, bills: s.bills.filter((b) => filters.players.includes(b.player_name)) }))
      .filter((s) => s.bills.length)
  }
  if (filters.dateRange && filters.dateRange.length === 2) {
    const start = normDate(filters.dateRange[0])
    const end = normDate(filters.dateRange[1])
    list = list
      .map((s) => ({ ...s, bills: s.bills.filter((b) => b.game_date >= start && b.game_date <= end) }))
      .filter((s) => s.bills.length)
  }
  if (filters.sort === 'oldest') list = [...list].reverse()
  return list
})

const totalBills = computed(() => filteredSessions.value.reduce((s, x) => s + x.bills.length, 0))

function rate(lw, lc) {
  return lc > 0 ? `${((lw / lc) * 100).toFixed(0)}%` : '-'
}

async function refresh() {
  loading.value = true
  try {
    const [sess, pl] = await Promise.all([fetchSessions(), fetchPlayers()])
    sessions.value = sess
    players.value = pl
    const ids = new Set(sessions.value.map((s) => s.session.id))
    Object.keys(sessionEdit).forEach((k) => {
      if (!ids.has(Number(k))) {
        delete sessionEdit[k]
        delete sessionDrafts[k]
      }
    })
  } finally {
    loading.value = false
  }
}

function startSessionEdit(sess) {
  sessionEdit[sess.session.id] = true
  sessionDrafts[sess.session.id] = {
    date: sess.session.game_date,
    time: sess.session.game_time,
    bills: sess.bills.map((b) => ({ ...b })),
  }
  showDetail[sess.session.id] = true
}
function cancelSessionEdit(sess) {
  sessionEdit[sess.session.id] = false
  delete sessionDrafts[sess.session.id]
}

async function saveSession(sess) {
  const dra = sessionDrafts[sess.session.id]
  const date = normDate(dra.date) || sess.session.game_date
  const total = dra.bills.reduce((s, b) => s + (Number(b.win_points) || 0), 0)
  if (Math.abs(total) > 0.001) return message.error(`本局总分必须为 0，当前为 ${total.toFixed(1)} 分`)
  try {
    for (const b of dra.bills) {
      const pid = playerNameToId.value[b.player_name]
      if (!pid) return message.error(`玩家「${b.player_name}」不存在，请检查`)
      await updateBill(b.id, {
        player_id: pid,
        game_date: date,
        win_points: Number(b.win_points) || 0,
        landlord_count: Number(b.landlord_count) || 0,
        landlord_win: Number(b.landlord_win) || 0,
        farmer_count: Number(b.farmer_count) || 0,
        farmer_win: Number(b.farmer_win) || 0,
        remark: b.remark || '',
      })
    }
    message.success('已更新本局')
    cancelSessionEdit(sess)
    await refresh()
  } catch (e) {
    message.error(e.message)
  }
}

async function removeBillRow(sess, bill) {
  const dra = sessionDrafts[sess.session.id]
  if (dra.bills.length <= 1) return message.warning('该局至少保留一条记录')
  try {
    await deleteBill(bill.id)
    const idx = dra.bills.findIndex((b) => b.id === bill.id)
    if (idx >= 0) dra.bills.splice(idx, 1)
  } catch (e) {
    message.error(e.message)
  }
}

async function removeSession(sess) {
  if (!sess.session.id) return
  try {
    await deleteSession(sess.session.id)
    message.success('已删除整局')
    await refresh()
  } catch (e) {
    message.error(e.message)
  }
}

onMounted(refresh)
</script>

<template>
  <div>
    <div class="page-title">
      <n-h2 style="margin: 0">📋 账单记录</n-h2>
      <n-tag round type="info" size="small">{{ filteredSessions.length }} 局</n-tag>
      <n-tag round type="default" size="small">{{ totalBills }} 条记录</n-tag>
    </div>
    <n-p style="color: #909399; margin-top: 4px">每局直接展示参与者得分；点击「详情」查看地主/农民局数·胜率及原始截图；「编辑本局」按整局修改。</n-p>

    <!-- 筛选 -->
    <n-card :bordered="true" size="small" style="margin-top: 16px">
      <n-grid :cols="3" :x-gap="12" item-responsive responsive="screen">
        <n-grid-item :span="1" :xs="3">
          <n-form-item label="按玩家筛选" :show-feedback="false">
            <n-select v-model:value="filters.players" multiple :options="playerChoices" clearable placeholder="全部" />
          </n-form-item>
        </n-grid-item>
        <n-grid-item :span="1" :xs="3">
          <n-form-item label="日期范围" :show-feedback="false">
            <n-date-picker v-model:value="filters.dateRange" type="daterange" clearable style="width: 100%" />
          </n-form-item>
        </n-grid-item>
        <n-grid-item :span="1" :xs="3">
          <n-form-item label="排序" :show-feedback="false">
            <n-select v-model:value="filters.sort" :options="[{ label: '最新优先', value: 'newest' }, { label: '最早优先', value: 'oldest' }]" />
          </n-form-item>
        </n-grid-item>
      </n-grid>
      <n-text depth="3">共 {{ filteredSessions.length }} 局，{{ totalBills }} 条记录</n-text>
    </n-card>

    <n-spin :show="loading">
      <n-empty v-if="!filteredSessions.length" description="暂无账单记录，请先上传截图" style="margin-top: 60px" />

      <n-card
        v-for="s in filteredSessions"
        :key="s.session.id ?? 'orphan'"
        size="small"
        :bordered="true"
        class="session-card"
        style="margin-top: 16px"
      >
        <!-- 头部：日期(一次) + 操作 -->
        <template #header>
          <div class="sess-header">
            <div class="sess-title">
              <span class="mono sess-date">{{ s.session.game_date }}</span>
              <n-tag v-if="s.session.game_time" size="tiny" :bordered="false">{{ s.session.game_time }}</n-tag>
              <n-tag v-if="s.session.settled" size="tiny" type="success" :bordered="false">✅ 已结账</n-tag>
              <n-tag v-else size="tiny" type="warning" :bordered="false">待结账</n-tag>
              <n-tag v-if="s.session.price_per_point" size="tiny" :bordered="false">¥{{ s.session.price_per_point }}/分</n-tag>
            </div>
            <div class="sess-actions">
              <n-button
                v-if="!sessionEdit[s.session.id]"
                size="small"
                secondary
                @click="showDetail[s.session.id] = !showDetail[s.session.id]"
              >
                {{ showDetail[s.session.id] ? '收起详情' : '📋 详情' }}
              </n-button>
              <n-button
                v-if="!sessionEdit[s.session.id]"
                size="small"
                type="primary"
                secondary
                @click="startSessionEdit(s)"
              >✏️ 编辑本局</n-button>
              <n-button
                v-if="sessionEdit[s.session.id]"
                size="small"
                type="success"
                @click="saveSession(s)"
              >💾 保存本局</n-button>
              <n-button
                v-if="sessionEdit[s.session.id]"
                size="small"
                secondary
                @click="cancelSessionEdit(s)"
              >取消</n-button>
              <n-button
                v-if="s.session.id"
                size="tiny"
                quaternary
                type="error"
                @click="removeSession(s)"
              >🗑️ 删除整局</n-button>
            </div>
          </div>
        </template>

        <!-- 参与者得分（含用户名） -->
        <div class="score-summary">
          <div v-for="b in s.bills" :key="b.id" class="score-chip">
            <span class="chip-name">{{ b.player_name }}</span>
            <WinLossPill :value="b.win_points" :money="s.session.settled ? b.win_points * s.session.price_per_point : null" />
          </div>
        </div>

        <!-- 详情：截图 + 详细信息（点击即展示） -->
        <div v-if="showDetail[s.session.id] && !sessionEdit[s.session.id]" class="detail-area">
          <div v-if="s.session.image_path" style="margin-bottom: 12px">
            <n-image
              :src="imageUrl(s.session.image_path)"
              width="520"
              object-fit="contain"
              :show-toolbar="true"
              style="border-radius: 8px; display: block"
            />
          </div>

          <div class="detail-table">
            <div class="d-row d-head">
              <span class="c-name">玩家</span>
              <span class="c-score">得分</span>
              <span class="c-land">地主</span>
              <span class="c-farm">农民</span>
              <span class="c-remark">备注</span>
            </div>
            <div v-for="b in s.bills" :key="b.id" class="d-row">
              <span class="c-name">{{ b.player_name }}</span>
              <span class="c-score" :class="b.win_points >= 0 ? 'green' : 'red'">
                {{ b.win_points >= 0 ? '+' : '' }}{{ b.win_points.toFixed(1) }}
              </span>
              <span class="c-land">{{ b.landlord_count }}次 · 胜{{ rate(b.landlord_win, b.landlord_count) }}</span>
              <span class="c-farm">{{ b.farmer_count }}次 · 胜{{ rate(b.farmer_win, b.farmer_count) }}</span>
              <span class="c-remark">{{ b.remark || '-' }}</span>
            </div>
          </div>
        </div>

        <!-- 编辑态：日期(一次) + 整局所有记录 -->
        <div v-if="sessionEdit[s.session.id]" class="edit-area">
          <n-grid :cols="4" :x-gap="8" item-responsive responsive="screen" style="margin-bottom: 10px">
            <n-grid-item :span="2" :xs="2">
              <n-form-item label="游戏日期" :show-feedback="false" label-placement="top" style="margin-bottom: 0">
                <n-date-picker v-model:value="sessionDrafts[s.session.id].date" size="small" type="date" value-format="yyyy-MM-dd" clearable style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item :span="2" :xs="2">
              <n-form-item label="游戏时间" :show-feedback="false" label-placement="top" style="margin-bottom: 0">
                <n-input v-model:value="sessionDrafts[s.session.id].time" size="small" placeholder="HH:MM" clearable />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <div v-for="b in sessionDrafts[s.session.id].bills" :key="b.id" class="edit-row">
            <n-grid :cols="12" :x-gap="8" item-responsive responsive="screen" :y-gap="6">
              <n-grid-item :span="3" :xs="12">
                <n-select v-model:value="b.player_name" size="small" :options="playerChoices" />
              </n-grid-item>
              <n-grid-item :span="2" :xs="6">
                <n-input-number v-model:value="b.win_points" size="small" :step="1" style="width: 100%" placeholder="得分" />
              </n-grid-item>
              <n-grid-item :span="2" :xs="6">
                <n-input-number v-model:value="b.landlord_count" size="small" :min="0" placeholder="地主" style="width: 100%" />
              </n-grid-item>
              <n-grid-item :span="2" :xs="6">
                <n-input-number v-model:value="b.farmer_count" size="small" :min="0" placeholder="农民" style="width: 100%" />
              </n-grid-item>
              <n-grid-item :span="2" :xs="8">
                <n-input v-model:value="b.remark" size="small" placeholder="备注" clearable />
              </n-grid-item>
              <n-grid-item :span="1" :xs="4">
                <n-button size="tiny" type="error" quaternary @click="removeBillRow(s, b)">删除</n-button>
              </n-grid-item>
            </n-grid>
          </div>
          <n-text depth="3" size="small">保存时整局合计必须为 0。</n-text>
        </div>
      </n-card>
    </n-spin>
  </div>
</template>

<style scoped>
.session-card {
  border-radius: 12px;
}
.sess-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}
.sess-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-weight: 700;
}
.sess-date {
  font-weight: 800;
  font-size: 15px;
}
.sess-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.score-summary {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}
.score-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.chip-name {
  font-weight: 600;
}
.detail-area {
  margin-top: 14px;
  border-top: 1px dashed rgba(128, 128, 128, 0.15);
  padding-top: 12px;
}
.detail-table {
  border: 1px solid rgba(128, 128, 128, 0.12);
  border-radius: 8px;
  overflow: hidden;
}
.d-row {
  display: grid;
  grid-template-columns: 1.2fr 1fr 1fr 1fr 1.3fr;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(128, 128, 128, 0.08);
  font-size: 13px;
  align-items: center;
  margin: 0;
}
.d-row:last-child {
  border-bottom: none;
}
.d-head {
  background: rgba(128, 128, 128, 0.06);
  font-weight: 700;
  color: #909399;
}
.c-name,
.c-score,
.c-land,
.c-farm,
.c-remark {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.c-name {
  font-weight: 600;
}
.c-score {
  font-variant-numeric: tabular-nums;
  font-weight: 700;
}
.c-land,
.c-farm,
.c-remark {
  color: #606266;
}
.edit-area {
  margin-top: 12px;
  border-top: 1px dashed rgba(128, 128, 128, 0.2);
  padding-top: 10px;
}
.edit-row {
  padding: 4px 0;
}
.green {
  color: #18a058;
}
.red {
  color: #d03050;
}
</style>
