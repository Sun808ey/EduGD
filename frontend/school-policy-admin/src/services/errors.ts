import axios from 'axios'

export class AppError extends Error {
  readonly code: string
  readonly status?: number
  readonly retryAfterSeconds?: number

  constructor(
    code: string,
    message: string,
    status?: number,
    retryAfterSeconds?: number,
  ) {
    super(message)
    this.name = 'AppError'
    this.code = code
    this.status = status
    this.retryAfterSeconds = retryAfterSeconds
  }
}

function parseRetryAfter(value: unknown): number | undefined {
  if (typeof value !== 'string') return undefined
  const seconds = Number(value)
  if (Number.isInteger(seconds) && seconds >= 0) return seconds
  const date = Date.parse(value)
  return Number.isNaN(date) ? undefined : Math.max(0, Math.ceil((date - Date.now()) / 1000))
}

export function normalizeApiError(error: unknown): AppError {
  if (error instanceof AppError) return error
  if (!axios.isAxiosError(error)) return new AppError('unexpected_error', 'Something went wrong. Please try again.')
  if (error.code === 'ECONNABORTED') return new AppError('request_timeout', 'The request timed out. Please try again.')
  if (!error.response) return new AppError('network_unavailable', 'The server could not be reached. Check your connection and try again.')

  const status = error.response.status
  const body = error.response.data as { error?: { code?: unknown; message?: unknown } } | undefined
  const code = typeof body?.error?.code === 'string' ? body.error.code : `http_${status}`
  const serverMessage = typeof body?.error?.message === 'string' ? body.error.message : undefined
  const message = status >= 500 ? 'The service is temporarily unavailable. Please try again.' : serverMessage ?? 'The request could not be completed.'
  const headers = error.response.headers
  const retryAfter = typeof headers?.get === 'function'
    ? headers.get('retry-after')
    : headers?.['retry-after']
  return new AppError(code, message, status, parseRetryAfter(retryAfter))
}

export function errorMessage(error: unknown) {
  return normalizeApiError(error).message
}
