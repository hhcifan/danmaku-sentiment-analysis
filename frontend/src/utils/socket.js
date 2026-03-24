import { io } from 'socket.io-client'

const socket = io('/', {
  transports: ['websocket', 'polling'],
  autoConnect: true,
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionAttempts: 10,
})

socket.on('connect', () => {
  console.log('SocketIO connected')
})

socket.on('disconnect', () => {
  console.log('SocketIO disconnected')
})

export default socket
