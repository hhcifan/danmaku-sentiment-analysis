<template>
  <el-container style="min-height: 100vh">
    <el-header class="tech-header">
      <div style="display: flex; align-items: center; gap: 12px;">
        <el-icon :size="24" style="color: var(--accent-cyan);"><DataAnalysis /></el-icon>
        <span class="tech-title">弹幕情绪感知商品推荐系统</span>
      </div>
      <div style="display: flex; align-items: center; gap: 16px;">
        <el-tag :type="connected ? 'success' : 'danger'" size="small">
          {{ connected ? '已连接' : '未连接' }}
        </el-tag>
        <el-tag v-if="systemRunning" type="success" size="small" effect="dark">
          {{ runMode === 'crawl' ? '爬虫采集中' : '手动模式' }}
        </el-tag>

        <!-- 采集模式控制 -->
        <el-dropdown @command="handleStart" v-if="!systemRunning" trigger="click">
          <el-button type="success" size="small" plain>
            启动采集 <el-icon style="margin-left:4px"><CaretRight /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="crawl">爬虫模式（自动抓取抖音弹幕）</el-dropdown-item>
              <el-dropdown-item command="manual">手动模式（前端输入弹幕）</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button v-else type="danger" size="small" plain @click="handleStop">
          停止采集
        </el-button>

        <router-link to="/" custom v-slot="{ navigate }">
          <el-button text class="nav-btn" @click="navigate">仪表盘</el-button>
        </router-link>
        <router-link to="/report" custom v-slot="{ navigate }">
          <el-button text class="nav-btn" @click="navigate">复盘报告</el-button>
        </router-link>
      </div>
    </el-header>
    <el-main style="padding: 16px; background: var(--bg-primary);">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from './utils/api'
import { useSocket } from './composables/useSocket'
import { useDanmuStore } from './stores/danmu'
import { useEmotionStore } from './stores/emotion'
import { useProductStore } from './stores/product'
import { useUserStore } from './stores/user'

const { connected, on } = useSocket()
const danmuStore = useDanmuStore()
const emotionStore = useEmotionStore()
const productStore = useProductStore()
const userStore = useUserStore()

const systemRunning = ref(false)
const runMode = ref('manual')

on('danmu:new', (data) => danmuStore.addDanmu(data))
on('emotion:update', (data) => emotionStore.update(data))
on('heat:update', (data) => productStore.updateHeatRanking(data))
on('suggestion:update', (data) => productStore.updateSuggestions(data))
on('recommend:update', (data) => userStore.updateRecommendation(data))
on('product:list', (data) => { productStore.products = data })
on('system:status', (data) => { systemRunning.value = data.running })

async function handleStart(mode) {
  if (mode === 'crawl') {
    try {
      const { value: url } = await ElMessageBox.prompt(
        '请输入抖音直播间的完整地址',
        '请输入直播间地址',
        {
          inputValue: 'https://live.douyin.com/646454278948',
          inputPattern: /^https?:\/\/.+/,
          inputErrorMessage: '请输入有效的 URL（以 http:// 或 https:// 开头）',
          confirmButtonText: '开始采集',
          cancelButtonText: '取消',
        }
      )
      try {
        const res = await api.post('/api/system/start', { mode, url })
        if (res.code === 0) {
          systemRunning.value = true
          runMode.value = mode
          ElMessage.success('爬虫模式已启动，正在抓取弹幕...')
        }
      } catch (e) {
        ElMessage.error('启动失败')
      }
    } catch {
      // 用户取消，不做任何操作
    }
  } else {
    try {
      const res = await api.post('/api/system/start', { mode })
      if (res.code === 0) {
        systemRunning.value = true
        runMode.value = mode
        ElMessage.success('手动模式已启动，请在弹幕面板输入弹幕')
      }
    } catch (e) {
      ElMessage.error('启动失败')
    }
  }
}

async function handleStop() {
  try {
    const res = await api.post('/api/system/stop')
    if (res.code === 0) {
      systemRunning.value = false
      ElMessage.info('采集已停止')
    }
  } catch (e) {
    ElMessage.error('停止失败')
  }
}

onMounted(async () => {
  try {
    const res = await api.get('/api/system/status')
    if (res.code === 0) systemRunning.value = res.data.running
  } catch (e) { /* ignore */ }

  // 初始加载最近20条弹幕（不再一次性导入全部）
  try {
    const res = await api.get('/api/dashboard/recent-danmu?limit=20')
    if (res.code === 0 && res.data.items && res.data.items.length > 0) {
      danmuStore.addDanmu(res.data.items)
      danmuStore.setHistoryMeta(res.data.oldest_id, res.data.has_more)
    }
  } catch (e) { /* ignore */ }
})
</script>

<style scoped>
.tech-header {
  background: linear-gradient(135deg, #0a0e27 0%, #1a1f4e 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.25);
  box-shadow: 0 2px 20px rgba(0, 212, 255, 0.12);
}
.tech-title {
  font-size: 18px;
  font-weight: 600;
  background: linear-gradient(90deg, #00d4ff, #4facfe);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.nav-btn {
  color: var(--text-secondary) !important;
  transition: color 0.2s;
}
.nav-btn:hover {
  color: var(--accent-cyan) !important;
}
</style>
