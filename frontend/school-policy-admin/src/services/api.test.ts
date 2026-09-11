import { beforeEach, describe, expect, it } from 'vitest'
import api from '@/services/api.ts'

describe('API request authentication', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('attaches the stored administrator Bearer token', async () => {
    localStorage.setItem('edu_admin_token', 'test-token')
    let authorization: string | undefined

    await api.get('/admin/auth/me', {
      adapter: async (config) => {
        authorization = config.headers.get('Authorization') as string | undefined
        return {
          data: {},
          status: 200,
          statusText: 'OK',
          headers: {},
          config,
        }
      },
    })

    expect(authorization).toBe('Bearer test-token')
  })
})
