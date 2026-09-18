import { describe, expect, it } from 'vitest'
import { resolveApiBaseUrl } from '@/lib/environment.ts'

describe('resolveApiBaseUrl', () => {
  it('allows the local development default and canonicalizes valid URLs', () => {
    expect(resolveApiBaseUrl(undefined, false)).toBe('/api/v1')
    expect(resolveApiBaseUrl('https://api.example.test/api/v1/', true)).toBe(
      'https://api.example.test/api/v1',
    )
  })

  it('requires an explicit HTTPS API URL for production', () => {
    for (const value of [
      undefined,
      '/api/v1',
      'http://api.example.test/api/v1',
      'https://user:secret@api.example.test/api/v1',
      'https://api.example.test/api/v1?token=secret',
      'https://api.example.test/api/v1#secret',
      'https://api.example.test/',
      'https://api.example.test\\api\\v1',
    ]) {
      expect(() => resolveApiBaseUrl(value, true)).toThrow(
        'VITE_API_BASE_URL must be an absolute HTTPS URL ending in /api/v1',
      )
    }
  })
})
