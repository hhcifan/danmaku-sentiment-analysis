<template>
  <el-card shadow="hover">
    <template #header>
      <div style="display: flex; align-items: center; gap: 8px;">
        <el-icon style="color: var(--accent-green);"><Goods /></el-icon>
        <span>商品管理</span>
      </div>
    </template>
    <el-form :inline="true" size="default" style="margin-bottom: 12px;">
      <el-form-item label="商品ID">
        <el-input-number v-model="newId" :min="1" style="width: 100px;" />
      </el-form-item>
      <el-form-item label="商品名称">
        <el-input v-model="newName" placeholder="如: 连衣裙" style="width: 140px;" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="handleAdd">添加商品</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="productStore.products" size="small" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="mention_count" label="提及次数" width="80" />
      <el-table-column prop="heat" label="热度" width="80" />
      <el-table-column label="操作" width="80">
        <template #default="{ row }">
          <el-button size="small" type="danger" text @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useProductStore } from '../stores/product'

const productStore = useProductStore()
const newId = ref(1)
const newName = ref('')

async function handleAdd() {
  if (!newName.value.trim()) {
    ElMessage.warning('请输入商品名称')
    return
  }
  try {
    const res = await productStore.addProduct(newId.value, newName.value.trim())
    if (res.code === 0) {
      ElMessage.success('添加成功')
      newId.value++
      newName.value = ''
      await productStore.fetchProducts()
    } else {
      ElMessage.warning(res.msg)
    }
  } catch (e) {
    ElMessage.error('添加失败')
  }
}

async function handleDelete(productId) {
  try {
    await productStore.deleteProduct(productId)
    ElMessage.success('删除成功')
    await productStore.fetchProducts()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

onMounted(() => {
  productStore.fetchProducts()
})
</script>
