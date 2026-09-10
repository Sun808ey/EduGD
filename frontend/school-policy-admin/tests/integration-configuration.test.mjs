import assert from 'node:assert/strict'
import test from 'node:test'
import { resolveApiBaseUrl, resolveSentryDsn } from '../src/lib/environment.ts'
import { scrubSentryEvent } from '../src/lib/observability.ts'

test('production requires an explicit HTTPS backend and local development works', () => {
  assert.equal(resolveApiBaseUrl(undefined, false), '/api/v1')
  assert.equal(resolveApiBaseUrl('https://api.example.test/api/v1/', true), 'https://api.example.test/api/v1')
  assert.equal(resolveApiBaseUrl('http://127.0.0.1:5000/api/v1', false), 'http://127.0.0.1:5000/api/v1')
  for (const value of [undefined, '/api/v1', 'http://api.example.test/api/v1', 'https://user:secret@api.example.test/api/v1', 'https://api.example.test/api/v1?token=secret', 'https://api.example.test/api/v1#secret', 'https://api.example.test/', 'https://api.example.test\\api\\v1']) {
    assert.throws(() => resolveApiBaseUrl(value, true))
  }
})

test('Sentry configuration is optional and accepts only public HTTPS DSNs', () => {
  assert.equal(resolveSentryDsn(undefined), undefined)
  assert.equal(resolveSentryDsn('https://public@example.test/123'), 'https://public@example.test/123')
  for (const value of ['YOUR_DSN', 'http://public@example.test/123', 'https://public:secret@example.test/123', 'https://example.test/123']) {
    assert.throws(() => resolveSentryDsn(value))
  }
})

test('Sentry excludes HTTP context, user information and arbitrary error values', () => {
  const event = scrubSentryEvent({
    type: undefined,
    message: 'password=secret',
    request: { data: 'secret' },
    user: { email: 'private@example.test' },
    extra: { token: 'secret' },
    breadcrumbs: [{ message: 'secret' }],
    exception: { values: [{ type: 'Error', value: 'secret', stacktrace: { frames: [{ filename: 'https://user:secret@example.test/app.js?token=secret', lineno: 3 }, { filename: 'data:text/plain,secret' }] } }] },
  })
  assert.equal(JSON.stringify(event).includes('secret'), false)
  assert.equal(event.exception.values[0].stacktrace.frames[0].lineno, 3)
  assert.equal(event.request, undefined)
  assert.equal(event.user, undefined)
})
