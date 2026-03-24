<template>
  <el-card shadow="hover">
    <template #header>
      <div style="display: flex; align-items: center; gap: 8px;">
        <el-icon style="color: var(--accent-blue);"><User /></el-icon>
        <span>用户行为录入</span>
      </div>
    </template>
    <el-form :inline="true" size="default">
      <el-form-item label="用户ID">
        <el-input v-model="userId" placeholder="如: user_001" style="width: 130px;" />
      </el-form-item>
      <el-form-item label="商品">
        <el-select v-model="productId" placeholder="选择商品" style="width: 150px;">
          <el-option v-for="p in productStore.products" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button-group>
          <el-button @click="record('click')" type="primary" plain>
            <el-icon><View /></el-icon> 点击
          </el-button>
          <el-button @click="record('cart')" type="warning" plain>
            <el-icon><ShoppingCart /></el-icon> 加购
          </el-button>
          <el-button @click="record('order')" type="success" plain>
            <el-icon><Coin /></el-icon> 下单
          </el-button>
        </el-button-group>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useProductStore } from '../stores/product'
import { useUserStore } from '../stores/user'
import { useSocket } from '../composables/useSocket'

const productStore = useProductStore()
const userStore = useUserStore()
const { emit } = useSocket()

const userId = ref('user_001')
const productId = ref(null)

async function record(actionType) {
  if (!userId.value || !productId.value) {
    ElMessage.warning('请填写用户ID并选择商品')
    return
  }
  try {
    await userStore.recordBehavior(userId.value, productId.value, actionType)
    emit('behavior:record', { user_id: userId.value, product_id: productId.value, action_type: actionType })
    ElMessage.success(`${actionType} 行为记录成功`)
    userStore.currentUserId = userId.value
    await userStore.fetchRecommendation(userId.value)
  } catch (e) {
    ElMessage.error('记录失败')
  }
}
</script>
