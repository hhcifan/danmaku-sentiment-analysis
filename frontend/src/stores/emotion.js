import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useEmotionStore = defineStore('emotion', () => {
  const stats = ref({
    positive: 0, negative: 0, neutral: 0, total: 0,
    positive_rate: 0, negative_rate: 0, neutral_rate: 0,
  })

  const history = ref([])
  const maxHistory = 30

  function update(data) {
    stats.value = { ...stats.value, ...data }
    history.value.push({
      time: new Date().toLocaleTimeString(),
      positive_rate: data.positive_rate || 0,
      negative_rate: data.negative_rate || 0,
      neutral_rate: data.neutral_rate || 0,
    })
    if (history.value.length > maxHistory) {
      history.value = history.value.slice(-maxHistory)
    }
  }

  return { stats, history, update }
})
