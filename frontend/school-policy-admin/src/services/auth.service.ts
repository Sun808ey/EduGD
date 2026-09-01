import api from '@/services/api'
import type { CurrentAdministratorResponse, LoginResponse } from '@/types/api'

const AUTH_TOKEN_KEY = 'edu_admin_token'
const AUTH_USER_KEY = 'edu_admin_user'

export const authService = {
  async login(username: string, password: string) {
    const { data } = await api.post<LoginResponse>('/admin/auth/login', {
      username,
      password,
    })

    localStorage.setItem(AUTH_TOKEN_KEY, data.access_token)
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(data.administrator))

    return data
  },

  async getCurrentAdministrator() {
    const { data } = await api.get<CurrentAdministratorResponse>('/admin/auth/me')
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(data.administrator))
    return data.administrator
  },

  async logout() {
    try {
      await api.post('/admin/auth/logout')
    } finally {
      localStorage.removeItem(AUTH_TOKEN_KEY)
      localStorage.removeItem(AUTH_USER_KEY)
    }
  },

  getStoredToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY)
  },

  getStoredUser() {
    const raw = localStorage.getItem(AUTH_USER_KEY)
    if (!raw) {
      return null
    }

    try {
      return JSON.parse(raw)
    } catch {
      return null
    }
  },
}

export { AUTH_TOKEN_KEY, AUTH_USER_KEY }
