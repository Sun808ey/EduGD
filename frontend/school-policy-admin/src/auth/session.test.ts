import { beforeEach, describe, expect, it, vi } from 'vitest'
import { clearSessionToken, getSessionExpiry, getSessionToken, setSessionToken } from '@/auth/session'

describe('memory-only session', () => {
  beforeEach(() => { clearSessionToken(); localStorage.clear(); sessionStorage.clear(); vi.useRealTimers() })
  it('holds the token only in module memory', () => {
    setSessionToken('secret-token', 900)
    expect(getSessionToken()).toBe('secret-token')
    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
    expect(getSessionExpiry()).toBeGreaterThan(Date.now())
  })
  it('clears an expired token', () => {
    vi.useFakeTimers(); vi.setSystemTime(new Date('2026-09-11T00:00:00Z'))
    setSessionToken('secret-token', 1); vi.advanceTimersByTime(1001)
    expect(getSessionToken()).toBeNull()
  })
})
