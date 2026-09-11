import api from '@/services/api'
import { loginSchema, meSchema, messageSchema } from '@/schemas/api'

export const authService = {
  async login(username: string, password: string) {
    const { data } = await api.post('/admin/auth/login', {
      username,
      password,
    })
    return loginSchema.parse(data)
  },

  async getCurrentAdministrator(signal?: AbortSignal) {
    const { data } = await api.get('/admin/auth/me', { signal })
    return meSchema.parse(data).administrator
  },

  async logout() {
    const { data } = await api.post('/admin/auth/logout')
    return messageSchema.parse(data)
  },
}
