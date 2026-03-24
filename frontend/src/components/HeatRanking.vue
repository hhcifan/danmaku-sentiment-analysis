<template>
  <el-card shadow="hover">
    <template #header>
      <div style="display: flex; align-items: center; gap: 8px;">
        <el-icon style="color: var(--accent-orange);"><TrendCharts /></el-icon>
        <span>商品热度排行</span>
      </div>
    </template>
    <div style="max-height: 320px; overflow-y: auto;">
      <div v-for="(item, idx) in productStore.heatRanking" :key="item.id"
           class="heat-item" :class="{ pinned: item.pinned }">
        <div style="display: flex; align-items: center; gap: 8px; flex: 1;">
          <span class="rank" :class="{ top3: idx < 3 }">{{ idx + 1 }}</span>
          <span v-if="item.pinned" style="color: var(--accent-orange); font-size: 16px;">&#128293;</span>
          <span style="font-weight: 500; color: var(--text-primary);">{{ item.name }}</span>
        </div>
        <div style="flex: 1;">
          <el-progress :percentage="heatPercent(item.heat)" :color="heatColor(idx)"
                       :stroke-width="14" :show-text="false" />
        </div>
        <div style="min-width: 160px; text-align: right; font-size: 12px; color: var(--text-secondary);">
          热度 {{ item.heat }} | 提及 {{ item.mention_count }}
          <span style="color: var(--sentiment-pos);">+{{ item.positive_mention }}</span>
          <span style="color: var(--sentiment-neg);">-{{ item.negative_mention }}</span>
        </div>
        <el-button size="small" :type="item.pinned ? 'warning' : 'default'"
                   @click="togglePin(item)" style="margin-left: 8px;">
          {{ item.pinned ? '取消置顶' : '置顶' }}
        </el-button>
      </div>
      <div v-if="productStore.heatRanking.length === 0"
           style="text-align: center; color: var(--text-muted); padding: 40px;">
        暂无商品数据
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { useProductStore } from '../stores/product'

const productStore = useProductStore()

function heatPercent(heat) {
  const max = Math.max(...productStore.heatRanking.map(p => p.heat), 1)
  return Math.min(Math.round(heat / max * 100), 100)
}

function heatColor(idx) {
  if (idx === 0) return '#ff6b9d'
  if (idx === 1) return '#ffa940'
  if (idx === 2) return '#4facfe'
  return 'rgba(0, 212, 255, 0.5)'
}

async function togglePin(item) {
  const originalPinned = item.pinned
  const newPinned = !item.pinned
  item.pinned = newPinned ? 1 : 0

  productStore.heatRanking.sort((a, b) => {
    if (b.pinned !== a.pinned) return b.pinned - a.pinned
    return b.heat - a.heat
  })

  try {
    await productStore.pinProduct(item.id, newPinned)
  } catch (e) {
    item.pinned = originalPinned
    productStore.heatRanking.sort((a, b) => {
      if (b.pinned !== a.pinned) return b.pinned - a.pinned
      return b.heat - a.heat
    })
  }
}
</script>

<style scoped>
.heat-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.08);
  gap: 12px;
  transition: background 0.2s;
}
.heat-item:hover {
  background: rgba(79, 172, 254, 0.06);
}
.heat-item.pinned {
  background: rgba(255, 169, 64, 0.08);
  border-left: 3px solid var(--accent-orange);
}
.rank {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  background: rgba(0, 212, 255, 0.1);
  color: var(--text-secondary);
}
.rank.top3 {
  background: linear-gradient(135deg, #ff6b9d, #ff4d4f);
  color: #fff;
  box-shadow: 0 0 8px rgba(255, 107, 157, 0.4);
}
</style>
