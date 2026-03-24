import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../utils/api'

export const useUserStore = defineStore('user', () => {
  const currentUserId = ref('')
  const recommendation = ref({ user_id: '', level: '', level_name: '', recommended_products: [] })
  const behaviors = ref([])

  async function recordBehavior(userId, productId, actionType) {
    return api.post('/api/behaviors', {
      user_id: userId,
      product_id: productId,
      action_type: actionType,
    })
  }

  async function fetchBehaviors(userId) {
    const res = await api.get('/api/behaviors', { params: { user_id: userId } })
    if (res.code === 0) behaviors.value = res.data
  }

  async function fetchRecommendation(userId) {
    const res = await api.get('/api/dashboard/recommend', { params: { user_id: userId } })
    if (res.code === 0) recommendation.value = res.data
  }

  function updateRecommendation(data) {
    recommendation.value = data
  }

  return {
    currentUserId, recommendation, behaviors,
    recordBehavior, fetchBehaviors, fetchRecommendation, updateRecommendation,
  }
})
