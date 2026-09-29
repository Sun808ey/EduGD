import axios, { AxiosHeaders } from 'axios'
import { resolveApiBaseUrl, resolveApiTimeout } from '@/lib/environment'
import { getSessionToken } from '@/auth/session'
import { normalizeApiError } from '@/services/errors'

let unauthorizedHandler: (() => void) | undefined

export function setUnauthorizedHandler(handler: (() => void) | undefined) {
  unauthorizedHandler = handler
}

const api = axios.create({
  baseURL: resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL, import.meta.env.PROD),
  timeout: resolveApiTimeout(import.meta.env.VITE_API_TIMEOUT),
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  const token = getSessionToken()

  if (token) {
    const headers = config.headers ?? new AxiosHeaders()
    headers.set('Authorization', `Bearer ${token}`)
    config.headers = headers
  }

  const csrfToken = document.cookie.split('; ').find((cookie) => cookie.startsWith('csrf_access_token='))?.split('=').slice(1).join('=')
  if (csrfToken) {
    const headers = config.headers ?? new AxiosHeaders()
    headers.set('X-CSRF-TOKEN', decodeURIComponent(csrfToken))
    config.headers = headers
  }

  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const normalized = normalizeApiError(error)
    if (normalized.status === 401 && error?.config?.url !== '/admin/auth/login') unauthorizedHandler?.()
    return Promise.reject(normalized)
  },
)

export default api
