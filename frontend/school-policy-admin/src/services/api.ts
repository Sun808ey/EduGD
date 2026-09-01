import axios, { AxiosHeaders } from 'axios'

const api = axios.create({
  baseURL: (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:5000/api/v1').replace(/\/$/, ''),
  timeout: Number(import.meta.env.VITE_API_TIMEOUT ?? 30000),
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('edu_admin_token')

  if (token) {
    const headers = config.headers ?? new AxiosHeaders()
    headers.set('Authorization', `Bearer ${token}`)
    config.headers = headers
  }

  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem('edu_admin_token')
      localStorage.removeItem('edu_admin_user')
      window.location.href = '/login'
    }

    return Promise.reject(error)
  },
)

export default api


