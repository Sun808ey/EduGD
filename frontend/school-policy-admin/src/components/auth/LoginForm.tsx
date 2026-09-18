import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { normalizeApiError } from '@/services/errors'

export function LoginForm() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, status } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [retrySeconds, setRetrySeconds] = useState(0)

  useEffect(() => {
    if (retrySeconds <= 0) return
    const timer = window.setInterval(() => setRetrySeconds((seconds) => Math.max(0, seconds - 1)), 1000)
    return () => window.clearInterval(timer)
  }, [retrySeconds])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!username.trim() || !password) return setError('Username and password are required.')
    setError('')
    try {
      await login(username.trim(), password)
      const requested = (location.state as { from?: string } | null)?.from
      navigate(requested?.startsWith('/') ? requested : '/dashboard', { replace: true })
    } catch (caught) {
      const failure = normalizeApiError(caught)
      if (failure.status === 429) {
        setRetrySeconds(failure.retryAfterSeconds ?? 60)
        setError('Too many sign-in attempts. Please wait before trying again.')
      } else if (failure.status === 401) setError('The username or password is incorrect.')
      else setError(failure.message)
    }
  }

  const disabled = status === 'authenticating' || retrySeconds > 0

  return <form onSubmit={submit} className="mt-8 space-y-5" noValidate>
    <label className="block text-sm font-medium" htmlFor="username">Username
      <input id="username" required autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2.5 focus-visible:outline-2 focus-visible:outline-emerald-600" />
    </label>
    <label className="block text-sm font-medium" htmlFor="password">Password
      <input id="password" required type="password" autoComplete="current-password" placeholder="••••••••" value={password} onChange={(event) => setPassword(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2.5 focus-visible:outline-2 focus-visible:outline-emerald-600" />
    </label>
    {error && <div role="alert" aria-live="polite" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</div>}
    <button type="submit" disabled={disabled} className="w-full rounded-lg bg-slate-950 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50">{status === 'authenticating' ? 'Signing in…' : retrySeconds > 0 ? `Try again in ${retrySeconds}s` : 'Sign in'}</button>
  </form>
}
