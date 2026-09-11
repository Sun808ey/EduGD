import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from '@/services/api'
import { authService } from '@/services/auth.service'

vi.mock('@/services/api', () => ({ default: { get: vi.fn(), post: vi.fn() } }))

const administratorUuid = '11111111-1111-4111-8111-111111111111'

describe('authentication service contracts', () => {
  beforeEach(() => vi.clearAllMocks())

  it('validates login, identity and logout responses', async () => {
    vi.mocked(api.post)
      .mockResolvedValueOnce({ data: { access_token: 'token', token_type: 'Bearer', expires_in: 900, administrator: { administrator_uuid: administratorUuid, username: 'admin', display_name: 'Admin' } } })
      .mockResolvedValueOnce({ data: { message: 'administrator logged out' } })
    vi.mocked(api.get).mockResolvedValueOnce({ data: { administrator: { administrator_uuid: administratorUuid, username: 'admin', display_name: 'Admin', permissions: ['policy.assign'] } } })

    await expect(authService.login('admin', 'password')).resolves.toMatchObject({ access_token: 'token' })
    await expect(authService.getCurrentAdministrator()).resolves.toMatchObject({ permissions: ['policy.assign'] })
    await expect(authService.logout()).resolves.toEqual({ message: 'administrator logged out' })
    expect(api.post).toHaveBeenNthCalledWith(1, '/admin/auth/login', { username: 'admin', password: 'password' })
  })

  it('rejects a response that violates the backend contract', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ data: { access_token: '', token_type: 'Basic' } })
    await expect(authService.login('admin', 'password')).rejects.toThrow()
  })
})
