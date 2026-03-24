<template>
  <el-card shadow="hover">
    <template #header>
      <div style="display: flex; align-items: center; gap: 8px;">
        <el-icon style="color: var(--accent-green);"><Notification /></el-icon>
        <span>主播优化建议</span>
      </div>
    </template>
    <div>
      <el-alert v-if="productStore.suggestions.general"
                :title="productStore.suggestions.general"
                type="info" show-icon :closable="false" style="margin-bottom: 12px;" />
      <div style="max-height: 260px; overflow-y: auto;">
        <div v-for="(s, idx) in productStore.suggestions.product_suggestions" :key="idx"
             class="suggestion-item">
          <el-tag :type="s.sentiment === '负向' ? 'danger' : s.sentiment === '正向' ? 'success' : 'info'"
                  size="small" style="margin-right: 8px;">
            {{ s.keyword }} ({{ s.count }}次)
          </el-tag>
          <span style="font-size: 13px; color: var(--text-secondary);">{{ s.advice }}</span>
        </div>
        <div v-if="!productStore.suggestions.product_suggestions?.length"
             style="text-align: center; color: var(--text-muted); padding: 30px;">
          暂无建议，等待弹幕数据积累...
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { useProductStore } from '../stores/product'

const productStore = useProductStore()
</script>

<style scoped>
.suggestion-item {
  padding: 8px 0;
  border-bottom: 1px solid rgba(0, 212, 255, 0.08);
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}
</style>
