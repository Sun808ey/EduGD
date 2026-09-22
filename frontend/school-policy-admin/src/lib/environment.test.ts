import { describe, expect, it } from 'vitest'
import { resolveApiBaseUrl, resolveApiTimeout, resolveSentryDsn } from '@/lib/environment'

describe('public environment configuration', () => {
  it('requires an explicit production HTTPS API', () => {
    expect(resolveApiBaseUrl(undefined, false)).toBe('/api/v1')
    expect(resolveApiBaseUrl('https://api.example.test/api/v1/', true)).toBe('https://api.example.test/api/v1')
    expect(resolveApiBaseUrl('http://localhost/api/v1', false)).toBe('http://localhost/api/v1')
    expect(resolveApiBaseUrl('http://127.0.0.1:5000/api/v1', false)).toBe('http://127.0.0.1:5000/api/v1')
    for (const value of [undefined, '/api/v1', ' value', 'https:\\api.example.test\\api\\v1', 'http://api.example.test/api/v1', 'https://user:secret@api.example.test/api/v1', 'https://api.example.test/?token=x', 'https://api.example.test/api/v2', 'https://api.example.test/api/v1#x']) expect(() => resolveApiBaseUrl(value, true)).toThrow()
  })
  it('bounds the API timeout', () => {
    expect(resolveApiTimeout(undefined)).toBe(30_000)
    expect(resolveApiTimeout('1000')).toBe(1000)
    for (const value of ['999', '60001', '3.5', 'x']) expect(() => resolveApiTimeout(value)).toThrow()
  })
  it('accepts only public HTTPS Sentry DSNs', () => {
    expect(resolveSentryDsn(undefined)).toBeUndefined()
    expect(resolveSentryDsn('https://public@example.test/123')).toBe('https://public@example.test/123')
    for (const value of ['YOUR_DSN', ' https://public@example.test/123', 'http://public@example.test/123', 'https://public:secret@example.test/123', 'https://example.test/123', 'https://public@example.test/not-number', 'https://public@example.test/123?q=x']) expect(() => resolveSentryDsn(value)).toThrow()
  })
})
