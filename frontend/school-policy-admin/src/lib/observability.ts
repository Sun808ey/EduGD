import type { ErrorEvent } from '@sentry/react'

function safeFilename(filename: string | undefined): string | undefined {
  if (!filename) return undefined
  try {
    const url = new URL(filename)
    if (url.protocol !== 'https:' && url.protocol !== 'http:') return undefined
    return `${url.origin}${url.pathname}`
  } catch {
    return undefined
  }
}

// Keep only operational error fields. Never forward HTTP context, breadcrumbs,
// user identity, extras or arbitrary exception text from API responses.
export function scrubSentryEvent(event: ErrorEvent): ErrorEvent {
  return {
    type: event.type,
    event_id: event.event_id,
    timestamp: event.timestamp,
    platform: event.platform,
    level: event.level,
    environment: event.environment,
    release: event.release,
    message: 'Frontend error',
    exception: event.exception ? {
      values: event.exception.values?.map(value => ({
        type: value.type,
        value: 'Frontend exception details withheld',
        stacktrace: value.stacktrace ? {
          frames: value.stacktrace.frames?.map(frame => ({
            filename: safeFilename(frame.filename),
            lineno: frame.lineno,
            colno: frame.colno,
            function: frame.function,
            in_app: frame.in_app,
          })),
        } : undefined,
      })),
    } : undefined,
  }
}
