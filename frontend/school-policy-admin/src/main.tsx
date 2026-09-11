import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import * as Sentry from '@sentry/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import './index.css'
import App from './App.tsx'
import { AuthProvider } from '@/context/AuthContext'
import { resolveSentryDsn } from '@/lib/environment'
import { scrubSentryEvent } from '@/lib/observability'

const sentryDsn = resolveSentryDsn(import.meta.env.VITE_SENTRY_DSN)

if (sentryDsn && sentryDsn !== 'YOUR_DSN') {
  Sentry.init({ dsn: sentryDsn, environment: import.meta.env.MODE, release: import.meta.env.VITE_APP_RELEASE, sendDefaultPii: false, sampleRate: 0.25, tracesSampleRate: 0, beforeSend: scrubSentryEvent })
}

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 15_000, retry: (count, error) => count < 2 && (!(error instanceof Error) || !('status' in error) || Number((error as { status?: number }).status) >= 500) }, mutations: { retry: false } } })

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Sentry.ErrorBoundary fallback={<main className="grid min-h-screen place-items-center p-6"><div role="alert">The application encountered an unexpected error. Reload to continue.</div></main>}>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider><App /></AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </Sentry.ErrorBoundary>
  </StrictMode>,
)
