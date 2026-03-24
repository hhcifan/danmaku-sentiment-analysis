<template>
  <el-card shadow="hover">
    <template #header>
      <div style="display: flex; align-items: center; gap: 8px;">
        <el-icon style="color: var(--accent-cyan);"><ChatDotRound /></el-icon>
        <span>实时弹幕流</span>
        <el-tag size="small" type="info">{{ danmuStore.danmuList.length }} 条</el-tag>
        <el-button size="small" text type="danger"
                   :disabled="danmuStore.danmuList.length === 0"
                   @click="clearDanmu"
                   style="margin-left: auto;">
          <el-icon style="margin-right: 2px;"><Delete /></el-icon>清空
        </el-button>
      </div>
    </template>
    <div ref="scrollContainer" class="danmu-list" style="height: 320px; overflow-y: auto;">
      <!-- 加载更多历史弹幕按钮 -->
      <div v-if="danmuStore.hasMore" style="text-align: center; padding: 8px 0;">
        <el-button size="small" text type="primary"
                   :loading="danmuStore.loadingHistory"
                   @click="loadMoreHistory">
          {{ danmuStore.loadingHistory ? '加载中...' : '加载更多历史弹幕' }}
        </el-button>
      </div>
      <div v-for="(item, idx) in danmuStore.danmuList" :key="idx" class="danmu-item"
           :class="'sentiment-' + item.sentiment">
        <span class="time">{{ item.time }}</span>
        <el-tag :type="sentimentType(item.sentiment)" size="small" style="margin: 0 6px;">
          {{ item.sentiment }}
        </el-tag>
        <span class="text">{{ item.text }}</span>
        <el-tag v-for="kw in item.keywords" :key="kw" size="small" type="warning"
                style="margin-left: 4px;">{{ kw }}</el-tag>
      </div>
      <div v-if="danmuStore.danmuList.length === 0" style="text-align: center; color: #999; padding: 40px;">
        暂无弹幕数据，请启动采集或手动输入
      </div>
    </div>
    <div style="margin-top: 12px; display: flex; gap: 8px;">
      <el-input v-model="inputText" placeholder="输入测试弹幕..." @keyup.enter="sendDanmu" />
      <el-button type="primary" @click="sendDanmu">发送</el-button>
    </div>
  </el-card>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { useDanmuStore } from '../stores/danmu'
import { useSocket } from '../composables/useSocket'
import { Delete } from '@element-plus/icons-vue'
import api from '../utils/api'

const danmuStore = useDanmuStore()
const { emit } = useSocket()
const inputText = ref('')
const scrollContainer = ref(null)
const isLoadingHistory = ref(false)

function sentimentType(s) {
  if (s === '正向') return 'success'
  if (s === '负向') return 'danger'
  return 'info'
}

function sendDanmu() {
  if (inputText.value.trim()) {
    emit('danmu:manual_input', { text: inputText.value.trim() })
    inputText.value = ''
  }
}

function clearDanmu() {
  danmuStore.clear()
  emit('danmu:clear')
}

async function loadMoreHistory() {
  if (danmuStore.loadingHistory || !danmuStore.hasMore) return
  danmuStore.loadingHistory = true
  isLoadingHistory.value = true

  const oldScrollHeight = scrollContainer.value ? scrollContainer.value.scrollHeight : 0

  try {
    const res = await api.get(`/api/dashboard/recent-danmu?limit=30&before_id=${danmuStore.oldestId}`)
    if (res.code === 0 && res.data.items && res.data.items.length > 0) {
      danmuStore.prependDanmu(res.data.items)
      danmuStore.setHistoryMeta(res.data.oldest_id, res.data.has_more)

      // 恢复滚动位置，防止视图跳动
      await nextTick()
      if (scrollContainer.value) {
        const newScrollHeight = scrollContainer.value.scrollHeight
        scrollContainer.value.scrollTop = newScrollHeight - oldScrollHeight
      }
    } else {
      danmuStore.hasMore = false
    }
  } catch (e) {
    console.error('加载历史弹幕失败:', e)
  } finally {
    danmuStore.loadingHistory = false
    isLoadingHistory.value = false
  }
}

// 自动滚动到底部（仅实时新弹幕时触发，加载历史不滚动）
watch(() => danmuStore.danmuList.length, () => {
  if (isLoadingHistory.value) return
  nextTick(() => {
    if (scrollContainer.value) {
      scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
    }
  })
})
</script>

<style scoped>
.danmu-item {
  padding: 6px 8px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.08);
  font-size: 13px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  transition: background 0.2s;
}
.danmu-item:hover {
  background: rgba(79, 172, 254, 0.06);
}
.danmu-item .time {
  color: var(--text-muted);
  font-size: 12px;
  min-width: 60px;
}
.danmu-item .text {
  flex: 1;
  color: var(--text-primary);
}
.sentiment-正向 { background: rgba(0, 242, 165, 0.06); }
.sentiment-负向 { background: rgba(255, 107, 157, 0.06); }
</style>
