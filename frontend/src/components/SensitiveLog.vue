<template>
  <el-card shadow="hover">
    <template #header>
      <div style="display: flex; align-items: center; justify-content: space-between;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <el-icon style="color: var(--accent-magenta);"><Warning /></el-icon>
          <span>敏感弹幕屏蔽日志</span>
        </div>
        <el-button type="danger" size="small" plain :disabled="logs.length === 0" @click="clearLogs">
          <el-icon style="margin-right: 4px;"><Delete /></el-icon>清空
        </el-button>
      </div>
    </template>
    <div style="max-height: 280px; overflow-y: auto;">
      <div v-for="(log, idx) in logs" :key="idx" class="log-item">
        <span style="color: var(--text-muted); font-size: 12px;">{{ log.time || log.created_at }}</span>
        <el-tag type="danger" size="small" style="margin: 0 6px;">屏蔽</el-tag>
        <span style="text-decoration: line-through; color: var(--text-muted); font-size: 13px;">{{ log.original_text }}</span>
        <span style="font-size: 12px; color: var(--accent-magenta); margin-left: 8px;">
          命中：{{ Array.isArray(log.matched_words) ? log.matched_words.join(', ') : log.matched_words }}
        </span>
      </div>
      <div v-if="logs.length === 0" style="text-align: center; color: var(--text-muted); padding: 30px;">
        暂无敏感弹幕记录
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../utils/api'
import { useSocket } from '../composables/useSocket'

const logs = ref([])
const { on } = useSocket()

on('sensitive:blocked', (data) => {
  logs.value.unshift(data)
  if (logs.value.length > 100) logs.value = logs.value.slice(0, 100)
})

async function clearLogs() {
  try {
    const res = await api.delete('/api/dashboard/sensitive-log')
    if (res.code === 0) {
      logs.value = []
      ElMessage.success('敏感日志已清空')
    }
  } catch (e) {
    ElMessage.error('清空失败')
  }
}

onMounted(async () => {
  try {
    const res = await api.get('/api/dashboard/sensitive-log')
    if (res.code === 0) logs.value = res.data
  } catch (e) {
    console.error(e)
  }
})
</script>

<style scoped>
.log-item {
  padding: 6px 0;
  border-bottom: 1px solid rgba(0, 212, 255, 0.08);
  font-size: 13px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}
</style>
