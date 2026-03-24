<template>
  <el-card shadow="hover">
    <template #header>
      <div style="display: flex; align-items: center; gap: 8px;">
        <el-icon style="color: var(--accent-purple, #a855f7);"><DataLine /></el-icon>
        <span>商品转化数据录入</span>
      </div>
    </template>
    <el-form :inline="true" size="default">
      <el-form-item label="商品">
        <el-select v-model="form.product_id" placeholder="选择商品" style="width: 130px;">
          <el-option v-for="p in productStore.products" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="点击数">
        <el-input-number v-model="form.click_count" :min="0" size="default" style="width: 100px;" />
      </el-form-item>
      <el-form-item label="加购数">
        <el-input-number v-model="form.cart_count" :min="0" size="default" style="width: 100px;" />
      </el-form-item>
      <el-form-item label="下单数">
        <el-input-number v-model="form.order_count" :min="0" size="default" style="width: 100px;" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="submit">保存</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="productStore.conversions" size="small" style="margin-top: 12px;" v-if="productStore.conversions.length">
      <el-table-column prop="product_name" label="商品" width="100" />
      <el-table-column prop="click_count" label="点击" width="70" />
      <el-table-column prop="cart_count" label="加购" width="70" />
      <el-table-column prop="order_count" label="下单" width="70" />
      <el-table-column label="下单率" width="80">
        <template #default="{ row }">
          {{ (row.order_rate * 100).toFixed(1) }}%
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useProductStore } from '../stores/product'

const productStore = useProductStore()

const form = reactive({
  product_id: null,
  click_count: 0,
  cart_count: 0,
  order_count: 0,
})

async function submit() {
  if (!form.product_id) {
    ElMessage.warning('请选择商品')
    return
  }
  try {
    await productStore.upsertConversion({ ...form })
    ElMessage.success('转化数据保存成功')
    await productStore.fetchConversions()
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

onMounted(() => {
  productStore.fetchConversions()
})
</script>
