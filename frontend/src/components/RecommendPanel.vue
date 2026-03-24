<template>
  <el-card shadow="hover">
    <template #header>
      <div style="display: flex; align-items: center; gap: 8px;">
        <el-icon style="color: var(--accent-orange);"><Star /></el-icon>
        <span>用户分层推荐</span>
      </div>
    </template>
    <div style="margin-bottom: 12px; display: flex; gap: 8px; align-items: center;">
      <el-input v-model="queryUserId" placeholder="输入用户ID查询推荐" style="width: 200px;" />
      <el-button type="primary" @click="fetchRecommend">查询推荐</el-button>
    </div>

    <div v-if="userStore.recommendation.user_id">
      <div style="margin-bottom: 12px;">
        <span style="color: var(--text-secondary);">用户：</span>
        <el-tag>{{ userStore.recommendation.user_id }}</el-tag>
        <el-tag :type="levelType" style="margin-left: 8px;">
          {{ userStore.recommendation.level_name }}
        </el-tag>
      </div>

      <div v-for="p in userStore.recommendation.recommended_products" :key="p.product_id"
           class="recommend-item">
        <div style="font-weight: 500; color: var(--text-primary);">{{ p.product_name }}</div>
        <div style="font-size: 12px; color: var(--text-secondary);">
          热度：{{ p.heat }} | 评分：{{ p.score }}
        </div>
        <div style="font-size: 12px; color: var(--accent-cyan);">{{ p.reason }}</div>
      </div>
      <div v-if="!userStore.recommendation.recommended_products?.length"
           style="text-align: center; color: var(--text-muted); padding: 20px;">
        暂无推荐结果
      </div>
    </div>
    <div v-else style="text-align: center; color: var(--text-muted); padding: 30px;">
      请输入用户ID查询个性化推荐
    </div>
  </el-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const queryUserId = ref('user_001')

const levelType = computed(() => {
  const l = userStore.recommendation.level
  if (l === 'high_value') return 'success'
  if (l === 'potential') return 'warning'
  return 'info'
})

async function fetchRecommend() {
  if (queryUserId.value) {
    userStore.currentUserId = queryUserId.value
    await userStore.fetchRecommendation(queryUserId.value)
  }
}
</script>

<style scoped>
.recommend-item {
  padding: 8px 12px;
  border: 1px solid rgba(0, 212, 255, 0.12);
  border-radius: 6px;
  margin-bottom: 8px;
  background: rgba(0, 212, 255, 0.03);
  transition: border-color 0.2s, background 0.2s;
}
.recommend-item:hover {
  border-color: rgba(0, 212, 255, 0.3);
  background: rgba(0, 212, 255, 0.06);
}
</style>
