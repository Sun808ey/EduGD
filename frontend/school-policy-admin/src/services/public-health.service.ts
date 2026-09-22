import { resolveApiBaseUrl } from '@/lib/environment'

export type PublicHealthStatus = 'running' | 'ready' | 'not_ready' | 'unavailable'

export interface PublicHealthResult {
  status: PublicHealthStatus
  service: string
  checkedAt: string
  detail: string
}

const requestTimeout = 5000

function getApiBaseUrl() {
  return resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL, import.meta.env.PROD)
}

async function checkEndpoint(path: 'health' | 'ready', signal?: AbortSignal): Promise<PublicHealthResult> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), requestTimeout)
  const onAbort = () => controller.abort()
  signal?.addEventListener('abort', onAbort, { once: true })

  try {
    const response = await fetch(`${getApiBaseUrl()}/${path}`, { signal: controller.signal, headers: { Accept: 'application/json' } })
    const body = await response.json() as { status?: string; service?: string }
    const status = path === 'ready' && response.ok ? 'ready' : response.ok ? 'running' : 'not_ready'
    return {
      status,
      service: body.service ?? 'EduGuard API',
      checkedAt: new Date().toISOString(),
      detail: status === 'ready' ? 'Ready for authenticated administration' : status === 'running' ? 'API process is responding' : 'API is responding but not ready',
    }
  } catch {
    return {
      status: 'unavailable',
      service: 'EduGuard API',
      checkedAt: new Date().toISOString(),
      detail: 'The local or hosted API could not be reached',
    }
  } finally {
    window.clearTimeout(timeout)
    signal?.removeEventListener('abort', onAbort)
  }
}

export const publicHealthService = {
  checkHealth: (signal?: AbortSignal) => checkEndpoint('health', signal),
  checkReadiness: (signal?: AbortSignal) => checkEndpoint('ready', signal),
}