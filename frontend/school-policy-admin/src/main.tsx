import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import * as Sentry from '@sentry/react'
import { BrowserRouter } from 'react-router-dom'
import { MutationCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'

import './index.css'
import App from './App.tsx'
import { AuthProvider } from '@/context/AuthContext'
import { resolveSentryDsn } from '@/lib/environment'
import { scrubSentryEvent } from '@/lib/observability'
import { OfflineProvider } from '@/context/OfflineContext'
import { ThemeModeProvider } from '@/context/ThemeModeProvider'
import { LiveActionProvider } from '@/context/LiveActionContext'
import { announceLiveAction } from '@/context/liveActionEvents'

const sentryDsn = resolveSentryDsn(import.meta.env.VITE_SENTRY_DSN)

if (sentryDsn && sentryDsn !== 'YOUR_DSN') {
  Sentry.init({ dsn: sentryDsn, environment: import.meta.env.MODE, release: import.meta.env.VITE_APP_RELEASE, sendDefaultPii: false, sampleRate: 0.25, tracesSampleRate: 0, beforeSend: scrubSentryEvent })
}

const actionLabel = (mutation: { options: { meta?: Record<string, unknown> } }) => typeof mutation.options.meta?.actionLabel === 'string' ? mutation.options.meta.actionLabel : 'Administrator action'
const queryClient = new QueryClient({ mutationCache: new MutationCache({
  onMutate: (_variables, mutation) => announceLiveAction({ state: 'pending', label: actionLabel(mutation) }),
  onSuccess: (_data, _variables, _result, mutation) => announceLiveAction({ state: 'success', label: actionLabel(mutation) }),
  onError: (error, _variables, _result, mutation) => announceLiveAction({ state: 'error', label: actionLabel(mutation), detail: error instanceof Error ? error.message : 'The service rejected the action.' }),
}), defaultOptions: { queries: { staleTime: 15_000, retry: (count, error) => { const status = error instanceof Error && 'status' in error ? (error as { status?: unknown }).status : undefined; return count < 2 && (typeof status !== 'number' || !Number.isFinite(status) || status >= 500) } }, mutations: { retry: false } } })

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Sentry.ErrorBoundary fallback={<main className="grid min-h-screen place-items-center p-6"><div role="alert">The application encountered an unexpected error. Reload to continue.</div></main>}>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ThemeModeProvider><AuthProvider><OfflineProvider><LiveActionProvider><App /></LiveActionProvider></OfflineProvider></AuthProvider></ThemeModeProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </Sentry.ErrorBoundary>
  </StrictMode>,
)
