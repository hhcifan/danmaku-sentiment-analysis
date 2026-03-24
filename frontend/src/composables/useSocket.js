import { ref, onMounted, onUnmounted } from 'vue'
import socket from '../utils/socket'

export function useSocket() {
  const connected = ref(false)

  onMounted(() => {
    connected.value = socket.connected
    socket.on('connect', () => { connected.value = true })
    socket.on('disconnect', () => { connected.value = false })
  })

  const on = (event, handler) => {
    socket.on(event, handler)
    onUnmounted(() => socket.off(event, handler))
  }

  const emit = (event, data) => {
    socket.emit(event, data)
  }

  return { socket, connected, on, emit }
}
