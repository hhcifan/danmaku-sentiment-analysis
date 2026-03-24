<template>
  <el-card shadow="hover">
    <template #header>
      <div style="display: flex; align-items: center; gap: 8px;">
        <el-icon style="color: var(--accent-cyan);"><PieChart /></el-icon>
        <span>情绪分布</span>
        <el-tag size="small">总计 {{ emotionStore.stats.total }} 条</el-tag>
      </div>
    </template>
    <div style="display: flex; gap: 16px;">
      <div style="flex: 1;">
        <v-chart :option="pieOption" style="height: 260px;" autoresize />
      </div>
      <div style="flex: 1;">
        <v-chart :option="lineOption" style="height: 260px;" autoresize />
      </div>
    </div>
    <div style="display: flex; justify-content: space-around; margin-top: 12px;">
      <div style="text-align: center;">
        <div class="stat-number" style="color: var(--sentiment-pos);">{{ emotionStore.stats.positive }}</div>
        <div style="color: var(--text-secondary); font-size: 12px;">正向 ({{ emotionStore.stats.positive_rate }}%)</div>
      </div>
      <div style="text-align: center;">
        <div class="stat-number" style="color: var(--sentiment-neg);">{{ emotionStore.stats.negative }}</div>
        <div style="color: var(--text-secondary); font-size: 12px;">负向 ({{ emotionStore.stats.negative_rate }}%)</div>
      </div>
      <div style="text-align: center;">
        <div class="stat-number" style="color: var(--sentiment-neu);">{{ emotionStore.stats.neutral }}</div>
        <div style="color: var(--text-secondary); font-size: 12px;">中性 ({{ emotionStore.stats.neutral_rate }}%)</div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart as EPie, LineChart as ELine } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useEmotionStore } from '../stores/emotion'

use([EPie, ELine, TitleComponent, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer])

const emotionStore = useEmotionStore()

const pieOption = computed(() => ({
  tooltip: { trigger: 'item', backgroundColor: 'rgba(13,25,65,0.9)', borderColor: 'rgba(0,212,255,0.3)', textStyle: { color: '#e8eaed' } },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    data: [
      { value: emotionStore.stats.positive, name: '正向', itemStyle: { color: '#00f2a5' } },
      { value: emotionStore.stats.negative, name: '负向', itemStyle: { color: '#ff6b9d' } },
      { value: emotionStore.stats.neutral, name: '中性', itemStyle: { color: '#4facfe' } },
    ],
    label: { show: true, formatter: '{b}: {d}%', color: '#8892b0' },
  }],
}))

const lineOption = computed(() => ({
  tooltip: { trigger: 'axis', backgroundColor: 'rgba(13,25,65,0.9)', borderColor: 'rgba(0,212,255,0.3)', textStyle: { color: '#e8eaed' } },
  grid: { top: 20, right: 20, bottom: 30, left: 40 },
  xAxis: {
    type: 'category',
    data: emotionStore.history.map(h => h.time),
    axisLabel: { fontSize: 10, color: '#8892b0' },
    axisLine: { lineStyle: { color: 'rgba(0,212,255,0.15)' } },
    splitLine: { show: false },
  },
  yAxis: {
    type: 'value',
    max: 100,
    axisLabel: { formatter: '{value}%', color: '#8892b0' },
    axisLine: { lineStyle: { color: 'rgba(0,212,255,0.15)' } },
    splitLine: { lineStyle: { color: 'rgba(0,212,255,0.06)' } },
  },
  series: [
    {
      name: '正向', type: 'line',
      data: emotionStore.history.map(h => h.positive_rate),
      smooth: true,
      lineStyle: { color: '#00f2a5', width: 2 },
      itemStyle: { color: '#00f2a5' },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(0,242,165,0.2)' }, { offset: 1, color: 'rgba(0,242,165,0)' }] } },
    },
    {
      name: '负向', type: 'line',
      data: emotionStore.history.map(h => h.negative_rate),
      smooth: true,
      lineStyle: { color: '#ff6b9d', width: 2 },
      itemStyle: { color: '#ff6b9d' },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(255,107,157,0.2)' }, { offset: 1, color: 'rgba(255,107,157,0)' }] } },
    },
  ],
}))
</script>

<style scoped>
.stat-number {
  font-size: 26px;
  font-weight: 700;
  font-family: 'Consolas', 'Monaco', monospace;
  text-shadow: 0 0 12px currentColor;
}
</style>
