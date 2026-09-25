<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { fetchPlayers, imageUrl, recognize, saveSessionBatch } from '@/api'

const message = useMessage()

const CONFIG_KEY = 'dzz-llm-config'

const config = reactive({ api_key: '', base_url: 'https://api.xiaomimimo.com/v1', model: 'mimo-v2.5' })
const existingPlayers = ref([])
const rawFiles = ref([])
const items = ref([])
const recognizing = ref(false)
const saving = ref(false)
const previewIndex = ref(null)
const previewZoom = ref(false)
const previewTarget = computed(() => (previewIndex.value === null ? null : items.value[previewIndex.value] || null))

function openPreview(item) {
  previewIndex.value = items.value.indexOf(item)
  previewZoom.value = false
}

function movePreview(step) {
  if (previewIndex.value === null) return
  previewIndex.value = (previewIndex.value + step + items.value.length) % items.value.length
  previewZoom.value = false
}

function loadConfig() {
  try {
    const saved = JSON.parse(localStorage.getItem(CONFIG_KEY) || '{}')
    Object.assign(config, saved)
  } catch {
    /* ignore */
  }
}
function saveConfigNow() {
  localStorage.setItem(CONFIG_KEY, JSON.stringify(config))
  message.success('配置已保存到浏览器')
}

function reconcile(newFiles) {
  const names = new Set(newFiles.map((f) => f.name))
  const kept = items.value.filter((i) => names.has(i.name))
  const keptNames = new Set(kept.map((i) => i.name))
  const added = newFiles
    .filter((f) => !keptNames.has(f.name))
    .map((f) => ({
      name: f.name,
      file: f,
      // 预先生成预览地址，避免模板里反复 createObjectURL 造成内存泄漏
      url: URL.createObjectURL(f),
      status: 'pending',
      result: null,
      fn_date: null,
      fn_time: '',
      error: '',
      players: [],
    }))
  // 释放被移除文件的预览地址
  items.value
    .filter((i) => !names.has(i.name))
    .forEach((i) => {
      if (i.url) URL.revokeObjectURL(i.url)
    })
  items.value = [...kept, ...added]
  rawFiles.value = newFiles
}

function handleUpload({ fileList }) {
  const files = fileList.map((i) => i.file).filter(Boolean)
  reconcile(files)
}

function pendingItems() {
  return items.value.filter((i) => i.status === 'pending')
}

async function startRecognize() {
  const pending = pendingItems()
  if (!pending.length) return message.info('没有待识别的截图')
  recognizing.value = true
  try {
    // 先标记状态
    pending.forEach((i) => (i.status = 'recognizing'))
    const fs = pending.map((i) => i.file)
    const res = await recognize(fs, config)
    const byName = {}
    res.results.forEach((r) => (byName[r.file_name] = r))
    for (const item of pending) {
      const r = byName[item.name]
      if (!r) {
        item.status = 'error'
        item.error = '未返回结果'
        continue
      }
      if (r.status === 'done') {
        item.status = 'done'
        item.result = r.result
        item.fn_date = r.fn_date
        item.game_date = r.fn_date || null
        item.game_time = r.fn_time || ''
        // 初始化可编辑 players（胜负盘数由本地按「盘数 × 胜率」推导，不可直接编辑）
        item.players = (r.result.players || []).map((p) => ({
          name: p.name,
          win_points: p.win_points ?? 0,
          landlord_count: p.landlord_count ?? 0,
          landlord_rate: p.landlord_rate ?? 0,
          landlord_win: p.landlord_win ?? 0,
          farmer_count: p.farmer_count ?? 0,
          farmer_rate: p.farmer_rate ?? 0,
          farmer_win: p.farmer_win ?? 0,
          remark: '',
        }))
        syncWins(item)
      } else {
        item.status = 'error'
        item.error = r.error || '识别失败'
      }
    }
    message.success('识别完成')
  } catch (e) {
    message.error(`识别失败：${e.message}`)
    pending.forEach((i) => (i.status = 'pending'))
  } finally {
    recognizing.value = false
  }
}

function totalOf(item) {
  return item.players.reduce((s, p) => s + (Number(p.win_points) || 0), 0)
}

/** 按「盘数 × 胜率」推导胜负盘数，夹在 [0, 盘数] 之间。 */
function deriveWin(count, rate) {
  const c = Math.max(0, Math.round(Number(count) || 0))
  const r = Math.min(100, Math.max(0, Number(rate) || 0))
  return Math.min(c, Math.round((c * r) / 100))
}

function syncWins(item) {
  for (const p of item.players) {
    p.landlord_win = deriveWin(p.landlord_count, p.landlord_rate)
    p.farmer_win = deriveWin(p.farmer_count, p.farmer_rate)
  }
}

/** 汇总整局的盘数与胜盘，用于面板说明。 */
function sessionSummary(item) {
  const acc = { landlord_count: 0, landlord_win: 0, farmer_count: 0, farmer_win: 0 }
  for (const p of item.players) {
    acc.landlord_count += Number(p.landlord_count) || 0
    acc.landlord_win += Number(p.landlord_win) || 0
    acc.farmer_count += Number(p.farmer_count) || 0
    acc.farmer_win += Number(p.farmer_win) || 0
  }
  return acc
}

function buildPayload(item) {
  syncWins(item)
  return {
    file_name: item.name,
    game_date: item.game_date || item.fn_date || new Date().toISOString().slice(0, 10),
    game_time: item.game_time || item.fn_time || '',
    raw_text: JSON.stringify(item.result || {}),
    players: item.players.map((p) => ({
      name: p.name,
      win_points: Number(p.win_points) || 0,
      landlord_count: Number(p.landlord_count) || 0,
      landlord_rate: Number(p.landlord_rate) || 0,
      landlord_win: Number(p.landlord_win) || 0,
      farmer_count: Number(p.farmer_count) || 0,
      farmer_rate: Number(p.farmer_rate) || 0,
      farmer_win: Number(p.farmer_win) || 0,
      remark: p.remark || '',
    })),
  }
}

async function saveOne(item) {
  const total = totalOf(item)
  if (Math.abs(total) > 0.001) return message.error(`「${item.name}」总分必须为 0，当前 ${total.toFixed(1)} 分`)
  saving.value = true
  try {
    await saveSessionBatch([item.file], [buildPayload(item)])
    item.status = 'saved'
    message.success(`「${item.name}」已保存`)
  } catch (e) {
    message.error(`保存失败：${e.message}`)
  } finally {
    saving.value = false
  }
}

async function saveAll() {
  const done = items.value.filter((i) => i.status === 'done')
  if (!done.length) return message.info('没有待保存的识别结果')
  const invalid = done.find((i) => Math.abs(totalOf(i)) > 0.001)
  if (invalid) return message.error(`「${invalid.name}」总分必须为 0，请先修正`)
  saving.value = true
  try {
    await saveSessionBatch(done.map((i) => i.file), done.map(buildPayload))
    done.forEach((i) => (i.status = 'saved'))
    message.success(`已保存 ${done.length} 条记录`)
  } catch (e) {
    message.error(`保存失败：${e.message}`)
  } finally {
    saving.value = false
  }
}

function previewUrl(item) {
  return item.url
}

const statusMap = {
  pending: { label: '待识别', type: 'default' },
  recognizing: { label: '识别中', type: 'warning' },
  done: { label: '待保存', type: 'info' },
  error: { label: '失败', type: 'error' },
  saved: { label: '已保存', type: 'success' },
}

onMounted(async () => {
  loadConfig()
  existingPlayers.value = await fetchPlayers()
})
</script>

<template>
  <div>
    <div class="page-title">
      <n-h2 style="margin: 0">📤 账单上传</n-h2>
      <n-tag round type="info" size="small">AI 截图识别</n-tag>
    </div>
    <n-p style="color: #909399; margin-top: 4px">上传斗地主结算截图，AI 自动识别玩家输赢，编辑后保存。</n-p>

    <!-- API 配置 -->
    <n-collapse style="margin-top: 16px">
      <n-collapse-item title="🧠 API 配置（OpenAI 兼容 / Mimo）">
        <n-grid :cols="3" :x-gap="12" responsive="screen" item-responsive>
          <n-grid-item :span="1" :xs="3">
            <n-form-item label="API Key" :show-feedback="false">
              <n-input v-model:value="config.api_key" type="password" show-password-on="click" placeholder="sk-..." />
            </n-form-item>
          </n-grid-item>
          <n-grid-item :span="1" :xs="3">
            <n-form-item label="Base URL" :show-feedback="false">
              <n-input v-model:value="config.base_url" placeholder="https://api.xiaomimimo.com/v1" />
            </n-form-item>
          </n-grid-item>
          <n-grid-item :span="1" :xs="3">
            <n-form-item label="模型" :show-feedback="false">
              <n-input v-model:value="config.model" placeholder="mimo-v2.5" />
            </n-form-item>
          </n-grid-item>
        </n-grid>
        <n-button size="small" secondary @click="saveConfigNow">💾 保存配置</n-button>
        <n-text depth="3" style="margin-left: 12px; font-size: 12px">配置保存在浏览器本地，也可通过环境变量设置。</n-text>
      </n-collapse-item>
    </n-collapse>

    <!-- 上传 -->
    <n-card :bordered="true" size="small" style="margin-top: 16px">
      <template #header><span style="font-weight: 700">🖼️ 上传结算截图</span></template>
      <n-upload
        :default-upload="false"
        accept="image/png,image/jpeg,image/webp"
        multiple
        :show-file-list="false"
        @change="handleUpload"
      >
        <n-upload-dragger>
          <div style="padding: 20px 0">
            <div style="font-size: 40px">📷</div>
            <n-p style="margin: 8px 0 0; font-weight: 600">点击或拖拽多张结算截图到此处</n-p>
            <n-p style="margin: 4px 0 0; color: #909399; font-size: 13px">支持 png / jpg / webp，可批量上传</n-p>
          </div>
        </n-upload-dragger>
      </n-upload>
    </n-card>

    <!-- 文件卡片 -->
    <div v-if="items.length" class="upload-cards">
      <n-card
        v-for="(item, idx) in items"
        :key="item.name"
        size="small"
        :bordered="true"
        class="upload-card"
        :style="{ borderColor: item.status === 'error' ? '#d03050' : undefined }"
      >
        <template #header>
          <div class="card-header">
            <span class="card-file">{{ item.name }}</span>
            <n-tag :type="statusMap[item.status].type" size="small" :bordered="false">{{ statusMap[item.status].label }}</n-tag>
          </div>
        </template>

        <div class="card-body">
          <div class="card-img" @click="openPreview(item)">
            <img :src="previewUrl(item)" class="thumb" alt="结算截图缩略图" />
            <div class="thumb-hint">🔍 点击放大核对</div>
          </div>

          <div class="card-main">
            <!-- 错误 -->
            <n-alert v-if="item.status === 'error'" type="error" :bordered="false">
              识别失败：{{ item.error }}
              <template #action>
                <n-button size="tiny" @click="item.status = 'pending'">重试</n-button>
              </template>
            </n-alert>

            <!-- 识别中 -->
            <n-skeleton v-else-if="item.status === 'recognizing'" text :repeat="3" />

            <!-- 待识别 -->
            <n-empty v-else-if="item.status === 'pending'" description="等待识别" size="small" />

            <!-- 编辑区 -->
            <template v-else-if="item.status === 'done'">
              <n-grid :cols="3" :x-gap="10" item-responsive responsive="screen">
                <n-grid-item :span="1" :xs="3">
                  <n-form-item label="游戏日期" :show-feedback="false" label-placement="top" style="margin-bottom: 10px">
                    <n-date-picker
                      v-model:value="item.game_date"
                      type="date"
                      value-format="yyyy-MM-dd"
                      clearable
                      style="width: 100%"
                    />
                  </n-form-item>
                </n-grid-item>
                <n-grid-item :span="1" :xs="3">
                  <n-form-item label="游戏时间" :show-feedback="false" label-placement="top" style="margin-bottom: 10px">
                    <n-input v-model:value="item.game_time" placeholder="HH:MM" clearable />
                  </n-form-item>
                </n-grid-item>
                <n-grid-item :span="1" :xs="3">
                  <n-form-item label="总分" :show-feedback="false" label-placement="top" style="margin-bottom: 10px">
                    <n-input-number
                      :value="totalOf(item)"
                      readonly
                      :status="Math.abs(totalOf(item)) > 0.001 ? 'error' : 'success'"
                      style="width: 100%"
                    />
                  </n-form-item>
                </n-grid-item>
              </n-grid>

              <n-divider style="margin: 8px 0" />

              <div v-for="(p, pi) in item.players" :key="pi" class="player-row">
                <n-auto-complete
                  v-model:value="p.name"
                  :options="existingPlayers.map((e) => ({ value: e.name, label: e.name })).filter((o) => o.value !== p.name)"
                  :input-props="{ placeholder: '玩家昵称' }"
                  size="small"
                  style="flex: 1; min-width: 120px"
                />
                <n-input-number v-model:value="p.win_points" size="small" :step="1" style="width: 130px">
                  <template #prefix>分数</template>
                </n-input-number>
                <n-button text size="small" type="error" @click="item.players.splice(pi, 1)">移除</n-button>
              </div>

              <n-collapse :default-expanded-names="[]" style="margin-top: 4px">
                <n-collapse-item name="advanced">
                  <template #header>
                    <span style="font-size: 13px; font-weight: 600">📊 高级统计（地主 / 农民）</span>
                  </template>
                  <div v-if="item.players.length" class="advanced-area">
                    <n-alert type="info" :bordered="false" style="margin-bottom: 8px">
                      <div style="font-size: 12px; line-height: 1.7">
                        <b>地主</b>：该玩家抢到地主、一个人打两个农民的盘数；<b>农民</b>：该玩家当农民、与另一名农民合作的盘数。<br />
                        <b>胜率</b>：截图上显示的胜率，可直接修改；<b>胜盘</b>由程序按「盘数 × 胜率」自动算出，不取 AI 结果，无需手填。
                      </div>
                    </n-alert>

                    <div v-for="(p, pi) in item.players" :key="pi" class="adv-player">
                      <div class="adv-player-name">{{ p.name || '未命名' }}</div>

                      <div class="adv-line">
                        <span class="adv-role adv-role-landlord">地主</span>
                        <n-input-number
                          v-model:value="p.landlord_count"
                          size="tiny"
                          :min="0"
                          placeholder="0"
                          class="adv-input"
                          @update:value="syncWins(item)"
                        >
                          <template #suffix>盘</template>
                        </n-input-number>
                        <n-input-number
                          v-model:value="p.landlord_rate"
                          size="tiny"
                          :min="0"
                          :max="100"
                          placeholder="0"
                          class="adv-input"
                          @update:value="syncWins(item)"
                        >
                          <template #suffix>%</template>
                        </n-input-number>
                        <span class="adv-win">胜 <b>{{ p.landlord_win }}</b> 盘</span>
                      </div>

                      <div class="adv-line">
                        <span class="adv-role adv-role-farmer">农民</span>
                        <n-input-number
                          v-model:value="p.farmer_count"
                          size="tiny"
                          :min="0"
                          placeholder="0"
                          class="adv-input"
                          @update:value="syncWins(item)"
                        >
                          <template #suffix>盘</template>
                        </n-input-number>
                        <n-input-number
                          v-model:value="p.farmer_rate"
                          size="tiny"
                          :min="0"
                          :max="100"
                          placeholder="0"
                          class="adv-input"
                          @update:value="syncWins(item)"
                        >
                          <template #suffix>%</template>
                        </n-input-number>
                        <span class="adv-win">胜 <b>{{ p.farmer_win }}</b> 盘</span>
                      </div>
                    </div>

                    <n-divider style="margin: 8px 0" />
                    <div class="adv-total">
                      本局合计：地主 {{ sessionSummary(item).landlord_count }} 盘 / 胜 {{ sessionSummary(item).landlord_win }} 盘 ·
                      农民 {{ sessionSummary(item).farmer_count }} 盘 / 胜 {{ sessionSummary(item).farmer_win }} 盘
                    </div>
                  </div>
                </n-collapse-item>
              </n-collapse>

              <n-space style="margin-top: 12px" justify="space-between" align="center">
                <div>
                  <n-button size="small" secondary @click="item.status = 'pending'">重新识别</n-button>
                </div>
                <n-button size="small" type="primary" :loading="saving" @click="saveOne(item)">💾 保存此条</n-button>
              </n-space>
            </template>
          </div>
        </div>
      </n-card>
    </div>

    <!-- 底部操作 -->
    <div v-if="items.length" class="action-bar">
      <n-space :size="12" align="center">
        <n-button type="primary" :loading="recognizing" :disabled="!pendingItems().length" @click="startRecognize">
          🔍 开始识别（{{ pendingItems().length }} 张待识别）
        </n-button>
        <n-button type="success" :loading="saving" :disabled="!items.some((i) => i.status === 'done')" @click="saveAll">
          💾 一键保存全部待保存结果
        </n-button>
        <n-text depth="3" v-if="items.some((i) => i.status === 'done')">已识别，编辑后可保存</n-text>
      </n-space>
    </div>

    <!-- 放大核对：左侧原图 + 右侧识别数据，两者同屏对照 -->
    <n-modal
      :show="previewIndex !== null"
      preset="card"
      title="🔍 放大核对（左图右数据）"
      style="width: 96vw; max-width: 1600px"
      :bordered="false"
      @update:show="(v) => !v && (previewIndex = null)"
    >
      <template v-if="previewTarget">
        <!-- 多张截图时可直接切换 -->
        <div v-if="items.length > 1" class="pv-picker">
          <n-button size="tiny" secondary :disabled="items.length < 2" @click="movePreview(-1)">← 上一张</n-button>
          <n-radio-group v-model:value="previewIndex" size="small">
            <n-radio-button v-for="(it, i) in items" :key="it.name" :value="i">
              {{ i + 1 }}
            </n-radio-button>
          </n-radio-group>
          <n-button size="tiny" secondary :disabled="items.length < 2" @click="movePreview(1)">下一张 →</n-button>
          <n-text depth="3" style="font-size: 12px">
            第 {{ previewIndex + 1 }} / {{ items.length }} 张 · {{ statusMap[previewTarget.status].label }}
          </n-text>
        </div>

        <div class="pv-body">
          <!-- 左：原图 -->
          <div class="pv-image-col">
            <div class="pv-toolbar">
              <n-button size="tiny" secondary @click="previewZoom = !previewZoom">
                {{ previewZoom ? '适应窗口' : '原始大小（可拖动查看）' }}
              </n-button>
              <n-button size="tiny" secondary tag="a" :href="previewUrl(previewTarget)" target="_blank">在新标签页打开</n-button>
            </div>
            <div class="pv-image-scroll" :class="{ zoomed: previewZoom }">
              <img :src="previewUrl(previewTarget)" class="pv-img" alt="结算截图原图" />
            </div>
          </div>

          <!-- 右：识别数据（与左图逐项对照，可直接修正） -->
          <div class="pv-data-col">
            <div class="pv-file">{{ previewTarget.name }}</div>

            <n-alert v-if="previewTarget.status !== 'done'" type="warning" :bordered="false" style="margin-bottom: 10px">
              该截图当前状态为「{{ statusMap[previewTarget.status].label }}」，暂无识别数据。
            </n-alert>

            <template v-else>
              <div class="pv-grid">
                <div class="pv-field">
                  <span class="pv-label">游戏日期</span>
                  <n-date-picker v-model:value="previewTarget.game_date" size="small" type="date" value-format="yyyy-MM-dd" clearable style="width: 130px" />
                </div>
                <div class="pv-field">
                  <span class="pv-label">游戏时间</span>
                  <n-input v-model:value="previewTarget.game_time" size="small" placeholder="HH:MM" style="width: 110px" />
                </div>
                <div class="pv-field">
                  <span class="pv-label">总分</span>
                  <n-input-number
                    :value="totalOf(previewTarget)"
                    readonly
                    size="small"
                    :status="Math.abs(totalOf(previewTarget)) > 0.001 ? 'error' : 'success'"
                    style="width: 100px"
                  />
                </div>
              </div>

              <div class="pv-table">
                <div class="pv-tr pv-th">
                  <span class="pv-name">玩家</span>
                  <span class="pv-score">得分</span>
                  <span class="pv-stat">地主 盘 / 率</span>
                  <span class="pv-win">地主胜</span>
                  <span class="pv-stat">农民 盘 / 率</span>
                  <span class="pv-win">农民胜</span>
                </div>
                <div v-for="(p, pi) in previewTarget.players" :key="pi" class="pv-tr">
                  <span class="pv-name">{{ p.name }}</span>
                  <n-input-number v-model:value="p.win_points" size="tiny" :step="1" class="pv-score" />
                  <span class="pv-stat">
                    <n-input-number v-model:value="p.landlord_count" size="tiny" :min="0" class="pv-num" @update:value="syncWins(previewTarget)" />
                    <span class="pv-slash">/</span>
                    <n-input-number v-model:value="p.landlord_rate" size="tiny" :min="0" :max="100" class="pv-num" @update:value="syncWins(previewTarget)" />
                  </span>
                  <span class="pv-win pv-calc">{{ p.landlord_win }}</span>
                  <span class="pv-stat">
                    <n-input-number v-model:value="p.farmer_count" size="tiny" :min="0" class="pv-num" @update:value="syncWins(previewTarget)" />
                    <span class="pv-slash">/</span>
                    <n-input-number v-model:value="p.farmer_rate" size="tiny" :min="0" :max="100" class="pv-num" @update:value="syncWins(previewTarget)" />
                  </span>
                  <span class="pv-win pv-calc">{{ p.farmer_win }}</span>
                </div>
              </div>

              <div class="pv-total">
                本局合计：地主 {{ sessionSummary(previewTarget).landlord_count }} 盘 / 胜 {{ sessionSummary(previewTarget).landlord_win }} 盘 ·
                农民 {{ sessionSummary(previewTarget).farmer_count }} 盘 / 胜 {{ sessionSummary(previewTarget).farmer_win }} 盘
              </div>
              <n-text depth="3" style="font-size: 12px; display: block; margin-top: 6px">
                表中「盘 / 率」可直接对照左图修改，胜盘由程序按「盘数 × 胜率」自动算出；修改会同步到卡片。
              </n-text>
            </template>
          </div>
        </div>
      </template>

      <template #footer>
        <n-space justify="space-between" align="center" style="width: 100%">
          <n-text depth="3" style="font-size: 12px">点「原始大小」可放大到 100% 并拖动查看细节</n-text>
          <n-button size="small" type="primary" @click="previewIndex = null">关闭</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.upload-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 14px;
  margin-top: 16px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.card-file {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-body {
  display: flex;
  gap: 12px;
}
.card-img {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: zoom-in;
}
.thumb {
  height: 104px;
  width: 104px;
  /* contain：完整显示截图，不裁切，便于核对 */
  object-fit: contain;
  border-radius: 8px;
  border: 1px solid var(--n-border-color, rgba(128, 128, 128, 0.24));
  background: rgba(128, 128, 128, 0.08);
  transition: transform 0.15s ease;
}
.card-img:hover .thumb {
  transform: scale(1.04);
}
.thumb-hint {
  font-size: 11px;
  color: #909399;
  white-space: nowrap;
}
.card-main {
  flex: 1;
  min-width: 0;
}
.player-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.advanced-area {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--n-color, rgba(128, 128, 128, 0.06));
}
.adv-player {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-bottom: 6px;
  border-bottom: 1px dashed var(--n-border-color, rgba(128, 128, 128, 0.2));
}
.adv-player:last-of-type {
  border-bottom: none;
}
.adv-player-name {
  font-weight: 600;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.adv-line {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.adv-role {
  flex-shrink: 0;
  width: 34px;
  font-size: 12px;
  text-align: center;
  border-radius: 4px;
  padding: 1px 0;
}
.adv-role-landlord {
  color: #d03050;
  background: rgba(208, 48, 80, 0.12);
}
.adv-role-farmer {
  color: #18a058;
  background: rgba(24, 160, 88, 0.12);
}
.adv-input {
  width: 96px;
}
.adv-win {
  font-size: 12px;
  color: #606266;
  white-space: nowrap;
}
.adv-win b {
  color: #18a058;
  font-size: 13px;
}
.adv-total {
  font-size: 12px;
  color: #606266;
}
/* ---- 放大核对弹窗：左图右数据 ---- */
.pv-picker {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.pv-body {
  display: flex;
  gap: 16px;
  align-items: stretch;
}
.pv-image-col {
  flex: 0 1 54%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.pv-toolbar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.pv-image-scroll {
  overflow: auto;
  max-height: 72vh;
  border-radius: 8px;
  border: 1px solid var(--n-border-color, rgba(128, 128, 128, 0.24));
  background: #1b1b1f;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 6px;
}
.pv-img {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
  border-radius: 6px;
}
.pv-image-scroll.zoomed {
  justify-content: flex-start;
}
.pv-image-scroll.zoomed .pv-img {
  max-width: none;
  max-height: none;
  width: auto;
  height: auto;
}
.pv-data-col {
  flex: 1 1 46%;
  min-width: 0;
  max-height: 72vh;
  overflow-y: auto;
  padding-right: 4px;
}
.pv-file {
  font-weight: 600;
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
  word-break: break-all;
}
.pv-grid {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.pv-field {
  display: flex;
  align-items: center;
  gap: 6px;
}
.pv-label {
  font-size: 12px;
  color: #606266;
  white-space: nowrap;
}
.pv-table {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.pv-tr {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 0;
  border-bottom: 1px dashed var(--n-border-color, rgba(128, 128, 128, 0.18));
}
.pv-th {
  font-size: 12px;
  color: #909399;
  border-bottom: 1px solid var(--n-border-color, rgba(128, 128, 128, 0.28));
}
.pv-name {
  flex: 0 0 72px;
  font-weight: 600;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pv-th .pv-name {
  font-weight: 400;
}
.pv-score {
  flex: 0 0 110px;
  width: 110px;
}
.pv-stat {
  flex: 1 1 auto;
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}
.pv-num {
  width: 88px;
  flex-shrink: 0;
}
.pv-slash {
  color: #c0c4cc;
}
.pv-win {
  flex: 0 0 56px;
  text-align: center;
  font-size: 12px;
}
.pv-calc {
  color: #18a058;
  font-weight: 700;
  font-size: 15px;
}
.pv-total {
  font-size: 12px;
  color: #606266;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--n-border-color, rgba(128, 128, 128, 0.2));
}
@media (max-width: 900px) {
  .pv-body {
    flex-direction: column;
  }
  .pv-image-col,
  .pv-data-col {
    flex: 1 1 100%;
    max-height: 50vh;
  }
}
.action-bar {
  margin-top: 18px;
  padding: 14px;
  border-radius: 12px;
  background: var(--n-color, rgba(128, 128, 128, 0.06));
}
</style>
