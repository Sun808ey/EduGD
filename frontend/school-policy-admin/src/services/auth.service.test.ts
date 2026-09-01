import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from '@/services/api'
import { authService } from '@/services/auth.service'

vi.mock('@/services/api', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}))

describe('authService', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('persists the administrator session after login', async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: {
        access_token: 'test-token',
        token_type: 'Bearer',
        expires_in: 900,
        administrator: {
          administrator_uuid: 'admin-uuid',
          username: 'admin',
          display_name: 'School Admin',
        },
      },
    })

    await authService.login('admin', 'secret')

    expect(api.post).toHaveBeenCalledWith('/admin/auth/login', {
      username: 'admin',
      password: 'secret',
    })
    expect(authService.getStoredToken()).toBe('test-token')
    expect(authService.getStoredUser()).toEqual({
      administrator_uuid: 'admin-uuid',
      username: 'admin',
      display_name: 'School Admin',
    })
  })

  it('revokes the server session and clears local credentials on logout', async () => {
    localStorage.setItem('edu_admin_token', 'test-token')
    localStorage.setItem('edu_admin_user', JSON.stringify({ username: 'admin' }))

    vi.mocked(api.post).mockResolvedValue({ data: { message: 'administrator logged out' } })

    await authService.logout()

    expect(api.post).toHaveBeenCalledWith('/admin/auth/logout')
    expect(authService.getStoredToken()).toBeNull()
    expect(authService.getStoredUser()).toBeNull()
  })

  it('clears local credentials when server logout fails', async () => {
    localStorage.setItem('edu_admin_token', 'test-token')
    vi.mocked(api.post).mockRejectedValue(new Error('network unavailable'))

    await expect(authService.logout()).rejects.toThrow('network unavailable')

    expect(authService.getStoredToken()).toBeNull()
  })
})