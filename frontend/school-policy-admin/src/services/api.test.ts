import axios, { AxiosHeaders } from 'axios'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from '@/services/api'
import { setUnauthorizedHandler } from '@/services/api'
import { clearSessionToken, setSessionToken } from '@/auth/session'

describe('API authentication', () => {
  beforeEach(() => { clearSessionToken(); setUnauthorizedHandler(undefined) })
  it('attaches the in-memory Bearer token', async () => {
    setSessionToken('test-token', 900)
    let authorization: string | undefined
    await api.get('/admin/auth/me', { adapter: async (config) => { authorization = config.headers.get('Authorization') as string; return { data: {}, status: 200, statusText: 'OK', headers: {}, config } } })
    expect(authorization).toBe('Bearer test-token')
  })
  it('does not attach an Authorization header without a session', async () => {
    let authorization: string | undefined
    await api.get('/admin/auth/me', { adapter: async (config) => { authorization = config.headers.get('Authorization') as string | undefined; return { data: {}, status: 200, statusText: 'OK', headers: {}, config } } })
    expect(authorization).toBeUndefined()
  })
  it('normalizes protected 401 responses and ends the session', async () => {
    const unauthorized = vi.fn()
    setUnauthorizedHandler(unauthorized)
    const config = { headers: new AxiosHeaders(), url: '/admin/auth/me' }
    await expect(api.get('/admin/auth/me', { adapter: async () => { throw new axios.AxiosError('raw', 'ERR_BAD_REQUEST', config, undefined, { data: { error: { code: 'authentication_required', message: 'authentication required' } }, status: 401, statusText: 'Unauthorized', headers: {}, config }) } })).rejects.toMatchObject({ code: 'authentication_required', status: 401 })
    expect(unauthorized).toHaveBeenCalledOnce()
  })
  it('leaves login failures for the login form to handle', async () => {
    const unauthorized = vi.fn()
    setUnauthorizedHandler(unauthorized)
    const config = { headers: new AxiosHeaders(), url: '/admin/auth/login' }
    await expect(api.post('/admin/auth/login', {}, { adapter: async () => { throw new axios.AxiosError('raw', 'ERR_BAD_REQUEST', config, undefined, { data: { error: { code: 'authentication_failed', message: 'authentication failed' } }, status: 401, statusText: 'Unauthorized', headers: {}, config }) } })).rejects.toMatchObject({ status: 401 })
    expect(unauthorized).not.toHaveBeenCalled()
  })
})
