<template>
  <el-card shadow="hover">
    <template #header>
      <div style="display: flex; align-items: center; gap: 8px;">
        <el-icon style="color: var(--accent-blue);"><Document /></el-icon>
        <span>复盘报告内容</span>
      </div>
    </template>
    <div v-if="content" class="report-content" v-html="renderMarkdown(content)" />
    <div v-else style="text-align: center; color: var(--text-muted); padding: 40px;">
      暂无报告内容
    </div>
  </el-card>
</template>

<script setup>
const props = defineProps({
  content: { type: String, default: '' },
})

function renderMarkdown(text) {
  if (!text) return ''
  return text
    .replace(/^# (.+)$/gm, '<h2 style="margin: 16px 0 8px; color: var(--accent-cyan); text-shadow: 0 0 8px rgba(0,212,255,0.3);">$1</h2>')
    .replace(/^## (.+)$/gm, '<h3 style="margin: 12px 0 6px; color: var(--text-primary);">$1</h3>')
    .replace(/^- (.+)$/gm, '<div style="padding: 2px 0 2px 16px; color: var(--text-secondary);">&#8226; $1</div>')
    .replace(/^\d+\. (.+)$/gm, '<div style="padding: 2px 0 2px 16px; color: var(--text-secondary);">$&</div>')
    .replace(/\|(.+)\|/g, '<span style="font-family: monospace; font-size: 13px; color: var(--text-secondary);">|$1|</span>')
    .replace(/={10,}/g, '<hr style="margin: 8px 0; border-color: rgba(0, 212, 255, 0.15);">')
    .replace(/\n/g, '<br>')
}
</script>

<style scoped>
.report-content {
  font-size: 14px;
  line-height: 1.8;
  max-height: 600px;
  overflow-y: auto;
  padding: 8px;
  color: var(--text-secondary);
}
</style>
