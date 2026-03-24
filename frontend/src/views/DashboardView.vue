<template>
  <div class="dashboard">
    <el-row :gutter="16" style="margin-bottom: 16px;">
      <el-col :span="12">
        <DanmuStream />
      </el-col>
      <el-col :span="12">
        <EmotionChart />
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-bottom: 16px;">
      <el-col :span="12">
        <HeatRanking />
      </el-col>
      <el-col :span="12">
        <SuggestionPanel />
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-bottom: 16px;">
      <el-col :span="12">
        <BehaviorInput />
      </el-col>
      <el-col :span="12">
        <ConversionInput />
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-bottom: 16px;">
      <el-col :span="12">
        <RecommendPanel />
      </el-col>
      <el-col :span="12">
        <SensitiveLog />
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="24">
        <ProductManager />
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import api from '../utils/api'
import { useProductStore } from '../stores/product'
import { useEmotionStore } from '../stores/emotion'
import DanmuStream from '../components/DanmuStream.vue'
import EmotionChart from '../components/EmotionChart.vue'
import HeatRanking from '../components/HeatRanking.vue'
import SuggestionPanel from '../components/SuggestionPanel.vue'
import BehaviorInput from '../components/BehaviorInput.vue'
import ConversionInput from '../components/ConversionInput.vue'
import RecommendPanel from '../components/RecommendPanel.vue'
import SensitiveLog from '../components/SensitiveLog.vue'
import ProductManager from '../components/ProductManager.vue'

const productStore = useProductStore()
const emotionStore = useEmotionStore()

onMounted(async () => {
  try {
    const res = await api.get('/api/dashboard/snapshot')
    if (res.code === 0) {
      const data = res.data
      if (data.emotion) emotionStore.update(data.emotion)
      if (data.heat_ranking) productStore.updateHeatRanking(data.heat_ranking)
      if (data.suggestions) productStore.updateSuggestions(data.suggestions)
    }
  } catch (e) {
    console.error('加载快照失败:', e)
  }
  await productStore.fetchProducts()
})
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
}
</style>
