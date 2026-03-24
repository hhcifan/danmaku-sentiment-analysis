import axios from 'axios'

const api = axios.create({
  baseURL: '',
  timeout: 10000,
})

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    console.error('API Error:', err)
    return Promise.reject(err)
  }
)

export default api
