import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useDanmuStore = defineStore('danmu', () => {
  const danmuList = ref([])
  const maxItems = 500
  const oldestId = ref(0)
  const hasMore = ref(false)
  const loadingHistory = ref(false)

  function addDanmu(items) {
    danmuList.value.push(...items)
    if (danmuList.value.length > maxItems) {
      danmuList.value = danmuList.value.slice(-maxItems)
    }
  }

  function prependDanmu(items) {
    danmuList.value.unshift(...items)
    if (danmuList.value.length > maxItems) {
      danmuList.value = danmuList.value.slice(0, maxItems)
    }
  }

  function setHistoryMeta(oid, more) {
    oldestId.value = oid
    hasMore.value = more
  }

  function clear() {
    danmuList.value = []
    oldestId.value = 0
    hasMore.value = false
  }

  return { danmuList, oldestId, hasMore, loadingHistory, addDanmu, prependDanmu, setHistoryMeta, clear }
})
