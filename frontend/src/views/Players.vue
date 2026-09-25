<script setup>
import { onMounted, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { createPlayer, deletePlayer, fetchPlayers, renamePlayer } from '@/api'

const message = useMessage()
const players = ref([])
const loading = ref(true)
const newName = ref('')
const adding = ref(false)

async function refresh() {
  loading.value = true
  try {
    players.value = await fetchPlayers()
  } finally {
    loading.value = false
  }
}

async function add() {
  const name = newName.value.trim()
  if (!name) return message.warning('请输入玩家昵称')
  adding.value = true
  try {
    await createPlayer(name)
    message.success(`玩家「${name}」添加成功`)
    newName.value = ''
    await refresh()
  } catch (e) {
    message.error(e.message)
  } finally {
    adding.value = false
  }
}

async function rename(p) {
  const name = p.name.trim()
  if (!name) return message.warning('昵称不能为空')
  try {
    await renamePlayer(p.id, name)
    message.success('已重命名')
    await refresh()
  } catch (e) {
    message.error(e.message)
  }
}

async function remove(p) {
  try {
    await deletePlayer(p.id)
    message.success(`已删除「${p.name}」`)
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
      <n-h2 style="margin: 0">👥 玩家管理</n-h2>
      <n-tag round type="info" size="small">{{ players.length }} 人</n-tag>
    </div>
    <n-p style="color: #909399; margin-top: 4px">新增、重命名、删除玩家。</n-p>

    <n-card :bordered="true" size="small" style="margin-top: 16px">
      <n-space align="center">
        <n-input
          v-model:value="newName"
          placeholder="输入玩家昵称"
          style="max-width: 320px"
          @keyup.enter="add"
        >
          <template #prefix>🃏</template>
        </n-input>
        <n-button type="primary" :loading="adding" @click="add">添加</n-button>
      </n-space>
    </n-card>

    <n-spin :show="loading">
      <n-empty v-if="!players.length" description="暂无玩家，请先添加" style="margin-top: 60px" />
      <n-grid :cols="3" :x-gap="14" :y-gap="14" responsive="screen" item-responsive style="margin-top: 16px">
        <n-grid-item v-for="p in players" :key="p.id" :span="1" :xs="2" :m="2" :s="3">
          <n-card size="small" :bordered="true" class="player-card">
            <div class="player-head">
              <span class="player-avatar">{{ p.name.slice(0, 1) }}</span>
              <div class="player-meta">
                <span class="player-name">{{ p.name }}</span>
                <span class="player-id">ID {{ p.id }} · {{ p.created_at }}</span>
              </div>
              <n-popconfirm @positive-click="remove(p)">
                <template #trigger>
                  <n-button size="tiny" quaternary type="error">删除</n-button>
                </template>
                确认删除玩家「{{ p.name }}」及其所有账单？
              </n-popconfirm>
            </div>
            <n-space style="margin-top: 10px" align="center">
              <n-input v-model:value="p.name" size="small" placeholder="新昵称">
                <template #prefix>✏️</template>
              </n-input>
              <n-button size="small" secondary @click="rename(p)">重命名</n-button>
            </n-space>
          </n-card>
        </n-grid-item>
      </n-grid>
    </n-spin>
  </div>
</template>

<style scoped>
.player-card {
  border-radius: 12px;
}
.player-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.player-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #18a058, #36ad6a);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
  flex-shrink: 0;
}
.player-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.player-name {
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.player-id {
  font-size: 12px;
  color: #909399;
}
</style>
