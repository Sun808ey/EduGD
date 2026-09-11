import axios, { AxiosHeaders } from 'axios'
import { describe, expect, it, vi } from 'vitest'
import { AppError, errorMessage, normalizeApiError } from '@/services/errors'

describe('API error normalization', () => {
  it('preserves structured safe client errors and retry timing', () => {
    const error = new axios.AxiosError('raw secret', 'ERR_BAD_REQUEST', undefined, undefined, { status: 429, statusText: 'Too Many Requests', headers: { 'retry-after': '30' }, config: { headers: new AxiosHeaders() }, data: { error: { code: 'rate_limit_exceeded', message: 'rate limit exceeded' } } })
    expect(normalizeApiError(error)).toMatchObject({ code: 'rate_limit_exceeded', status: 429, retryAfterSeconds: 30, message: 'rate limit exceeded' })
  })
  it('withholds server error details', () => {
    const error = new axios.AxiosError('password=secret', 'ERR_BAD_RESPONSE', undefined, undefined, { status: 503, statusText: 'Unavailable', headers: {}, config: { headers: new AxiosHeaders() }, data: { error: { code: 'read_unavailable', message: 'database secret' } } })
    expect(normalizeApiError(error).message).toBe('The service is temporarily unavailable. Please try again.')
  })
  it('classifies timeouts, network failures and unexpected errors', () => {
    const timeout = new axios.AxiosError('timeout', 'ECONNABORTED')
    const network = new axios.AxiosError('network')
    expect(normalizeApiError(timeout)).toMatchObject({ code: 'request_timeout' })
    expect(normalizeApiError(network)).toMatchObject({ code: 'network_unavailable' })
    expect(normalizeApiError(new Error('secret'))).toMatchObject({ code: 'unexpected_error' })
    const existing = new AppError('safe', 'Safe message', 400)
    expect(normalizeApiError(existing)).toBe(existing)
    expect(errorMessage(existing)).toBe('Safe message')
  })
  it('parses HTTP-date Retry-After and supplies fallbacks for malformed bodies', () => {
    vi.useFakeTimers(); vi.setSystemTime(new Date('2026-09-11T00:00:00Z'))
    const error = new axios.AxiosError('raw', 'ERR_BAD_REQUEST', undefined, undefined, { status: 409, statusText: 'Conflict', headers: { 'retry-after': 'Fri, 11 Sep 2026 00:00:02 GMT' }, config: { headers: new AxiosHeaders() }, data: {} })
    expect(normalizeApiError(error)).toMatchObject({ code: 'http_409', retryAfterSeconds: 2, message: 'The request could not be completed.' })
    vi.useRealTimers()
  })
})
