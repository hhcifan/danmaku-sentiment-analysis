<template>
  <div style="max-width: 1000px; margin: 0 auto;">
    <el-card shadow="hover" style="margin-bottom: 16px;">
      <template #header>
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <el-icon style="color: var(--accent-cyan);"><Document /></el-icon>
            <span>复盘报告管理</span>
          </div>
          <div style="display: flex; gap: 8px;">
            <el-button type="danger" plain size="small"
                       :disabled="selectedRows.length === 0"
                       @click="batchDelete">
              删除选中 ({{ selectedRows.length }})
            </el-button>
            <el-button type="danger" size="small"
                       :disabled="reportList.length === 0"
                       @click="clearAll">
              清空所有
            </el-button>
            <el-button type="primary" @click="generateReport" :loading="generating">
              生成新报告
            </el-button>
          </div>
        </div>
      </template>

      <div v-if="reportList.length" style="margin-bottom: 16px;">
        <el-table :data="reportList" size="small" stripe
                  @selection-change="handleSelectionChange"
                  @row-click="loadReport"
                  highlight-current-row>
          <el-table-column type="selection" width="45" />
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="create_time" label="生成时间" />
          <el-table-column prop="total_danmu" label="弹幕总数" width="90" />
          <el-table-column prop="positive_count" label="正向" width="70" />
          <el-table-column prop="negative_count" label="负向" width="70" />
          <el-table-column prop="neutral_count" label="中性" width="70" />
          <el-table-column label="操作" width="80" align="center">
            <template #default="{ row }">
              <el-button size="small" type="danger" text @click.stop="deleteReport(row.id)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div v-else style="text-align: center; color: #999; padding: 20px;">
        暂无报告，点击"生成新报告"创建
      </div>
    </el-card>

    <ReportContent :content="reportContent" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../utils/api'
import ReportContent from '../components/ReportContent.vue'

const reportList = ref([])
const reportContent = ref('')
const generating = ref(false)
const selectedRows = ref([])

function handleSelectionChange(rows) {
  selectedRows.value = rows
}

async function loadReportList() {
  try {
    const res = await api.get('/api/reports')
    if (res.code === 0) reportList.value = res.data
  } catch (e) {
    console.error(e)
  }
}

async function loadReport(row) {
  try {
    const res = await api.get(`/api/reports/${row.id}`)
    if (res.code === 0 && res.data) {
      reportContent.value = res.data.report_content || ''
    }
  } catch (e) {
    console.error(e)
  }
}

async function generateReport() {
  generating.value = true
  try {
    const res = await api.post('/api/reports/generate')
    if (res.code === 0) {
      ElMessage.success('报告生成成功')
      reportContent.value = res.data?.content || ''
      await loadReportList()
    }
  } catch (e) {
    ElMessage.error('报告生成失败')
  } finally {
    generating.value = false
  }
}

async function deleteReport(id) {
  try {
    await ElMessageBox.confirm('确定删除此报告？', '提示', { type: 'warning' })
    const res = await api.delete(`/api/reports/${id}`)
    if (res.code === 0) {
      ElMessage.success('报告已删除')
      await loadReportList()
      reportContent.value = ''
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

async function batchDelete() {
  if (selectedRows.value.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selectedRows.value.length} 条报告？`,
      '批量删除', { type: 'warning' }
    )
    const ids = selectedRows.value.map(r => r.id)
    const res = await api.post('/api/reports/batch-delete', { ids })
    if (res.code === 0) {
      ElMessage.success(res.msg)
      selectedRows.value = []
      reportContent.value = ''
      await loadReportList()
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('批量删除失败')
  }
}

async function clearAll() {
  try {
    await ElMessageBox.confirm(
      '确定清空所有报告？此操作不可恢复！',
      '清空所有', { type: 'error', confirmButtonText: '确认清空', cancelButtonText: '取消' }
    )
    const res = await api.delete('/api/reports')
    if (res.code === 0) {
      ElMessage.success('所有报告已清空')
      reportList.value = []
      reportContent.value = ''
      selectedRows.value = []
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('清空失败')
  }
}

onMounted(async () => {
  await loadReportList()
  if (reportList.value.length > 0) {
    await loadReport(reportList.value[0])
  }
})
</script>
