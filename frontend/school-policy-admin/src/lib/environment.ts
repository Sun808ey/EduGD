export function resolveApiBaseUrl(value: string | undefined, production: boolean): string {
  if (!value && !production) return '/api/v1'

  const invalidConfiguration = () =>
    new Error('VITE_API_BASE_URL must be an absolute HTTPS URL ending in /api/v1')

  if (!value || value !== value.trim() || value.includes('\\')) {
    throw invalidConfiguration()
  }

  let url: URL
  try {
    url = new URL(value)
  } catch {
    throw invalidConfiguration()
  }

  const localDevelopmentHttp =
    !production &&
    url.protocol === 'http:' &&
    ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)

  if (
    (!localDevelopmentHttp && url.protocol !== 'https:') ||
    !url.hostname ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    !/^\/api\/v1\/?$/.test(url.pathname)
  ) {
    throw invalidConfiguration()
  }

  return `${url.origin}/api/v1`
}
