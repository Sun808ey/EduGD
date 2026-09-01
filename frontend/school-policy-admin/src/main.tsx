import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import * as Sentry from '@sentry/react'

import './index.css'
import App from './App.tsx'
import { AuthProvider } from '@/context/AuthContext'

const sentryDsn = import.meta.env.VITE_SENTRY_DSN

if (sentryDsn && sentryDsn !== 'YOUR_DSN') {
  Sentry.init({ dsn: sentryDsn })
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>,
)
