import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../utils/api'

export const useProductStore = defineStore('product', () => {
  const products = ref([])
  const heatRanking = ref([])
  const suggestions = ref({ general: '', product_suggestions: [] })
  const conversions = ref([])

  async function fetchProducts() {
    const res = await api.get('/api/products')
    if (res.code === 0) products.value = res.data
  }

  async function addProduct(productId, productName) {
    return api.post('/api/products', { product_id: productId, product_name: productName })
  }

  async function deleteProduct(productId) {
    return api.delete(`/api/products/${productId}`)
  }

  async function pinProduct(productId, pinned) {
    const res = await api.put(`/api/products/${productId}/pin`, { pinned })
    // 使用响应中的排名数据直接更新，无需再次请求
    if (res.code === 0 && res.data) {
      updateHeatRanking(res.data)
    }
    return res
  }

  function updateHeatRanking(data) {
    heatRanking.value = data
  }

  function updateSuggestions(data) {
    suggestions.value = data
  }

  async function fetchConversions() {
    const res = await api.get('/api/conversions')
    if (res.code === 0) conversions.value = res.data
  }

  async function upsertConversion(data) {
    return api.post('/api/conversions', data)
  }

  return {
    products, heatRanking, suggestions, conversions,
    fetchProducts, addProduct, deleteProduct, pinProduct,
    updateHeatRanking, updateSuggestions, fetchConversions, upsertConversion,
  }
})
