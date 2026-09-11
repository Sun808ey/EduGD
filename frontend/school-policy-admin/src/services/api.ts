import axios, { AxiosHeaders } from 'axios'
import { resolveApiBaseUrl } from '@/lib/environment.ts'

const api = axios.create({
  baseURL: resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL, import.meta.env.PROD),
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


