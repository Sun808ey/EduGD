import { describe, expect, it } from 'vitest'
import { scrubSentryEvent } from '@/lib/observability'

describe('browser telemetry privacy', () => {
  it('removes identity, HTTP context and arbitrary secrets', () => {
    const result = scrubSentryEvent({ type: undefined, message: 'token=secret', request: { data: 'secret' }, user: { email: 'private@example.test' }, extra: { password: 'secret' }, breadcrumbs: [{ message: 'secret' }], exception: { values: [{ type: 'Error', value: 'secret', stacktrace: { frames: [{ filename: 'https://user:secret@example.test/app.js?token=secret', lineno: 3 }] } }] } })
    expect(JSON.stringify(result)).not.toContain('secret')
    expect(result.request).toBeUndefined()
    expect(result.user).toBeUndefined()
    expect(result.exception?.values?.[0].stacktrace?.frames?.[0].lineno).toBe(3)
  })
  it('handles events and frames without exception context', () => {
    expect(scrubSentryEvent({ type: undefined, event_id: 'safe' })).toMatchObject({ event_id: 'safe', message: 'Frontend error', exception: undefined })
    const result = scrubSentryEvent({ type: undefined, exception: { values: [{ stacktrace: { frames: [{ filename: 'file:///private/path' }, {}] } }] } })
    expect(result.exception?.values?.[0].stacktrace?.frames).toEqual([{ filename: undefined, lineno: undefined, colno: undefined, function: undefined, in_app: undefined }, { filename: undefined, lineno: undefined, colno: undefined, function: undefined, in_app: undefined }])
  })
})
