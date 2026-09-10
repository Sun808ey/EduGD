export function resolveApiBaseUrl(value: string | undefined, production: boolean): string {
  if (!value && !production) return '/api/v1'
  const error = () => new Error('VITE_API_BASE_URL must be an absolute HTTPS URL ending in /api/v1')
  if (!value || value !== value.trim() || value.includes('\\')) throw error()
  let url: URL
  try { url = new URL(value) } catch { throw error() }
  const localHttp = !production && url.protocol === 'http:' &&
    ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)
  if ((!localHttp && url.protocol !== 'https:') || !url.hostname || url.username ||
      url.password || url.search || url.hash || !/^\/api\/v1\/?$/.test(url.pathname)) {
    throw error()
  }
  return `${url.origin}/api/v1`
}

export function resolveSentryDsn(value: string | undefined): string | undefined {
  if (!value) return undefined
  const error = () => new Error('VITE_SENTRY_DSN must be a valid public HTTPS Sentry DSN')
  let url: URL
  try { url = new URL(value) } catch { throw error() }
  if (value !== value.trim() || url.protocol !== 'https:' || !url.hostname ||
      !url.username || url.password || url.search || url.hash || !/^\/\d+$/.test(url.pathname)) {
    throw error()
  }
  return value
}
