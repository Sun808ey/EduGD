import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import * as Sentry from '@sentry/react'
import { resolveApiBaseUrl, resolveSentryDsn } from './lib/environment'
import { scrubSentryEvent } from './lib/observability'

resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL, import.meta.env.PROD)
const dsn = resolveSentryDsn(import.meta.env.VITE_SENTRY_DSN)
if (dsn) {
  Sentry.init({
    dsn,
    environment: import.meta.env.MODE,
    sendDefaultPii: false,
    defaultIntegrations: false,
    integrations: [Sentry.globalHandlersIntegration()],
    sampleRate: 0.25,
    tracesSampleRate: 0,
    beforeSend: scrubSentryEvent,
  })
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
