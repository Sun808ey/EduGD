import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '@/context/AuthContext'
import { useAuth } from '@/hooks/useAuth'
import { authService } from '@/services/auth.service'
import { clearSessionToken, getSessionToken } from '@/auth/session'

vi.mock('@/services/auth.service', () => ({ authService: { login: vi.fn(), getCurrentAdministrator: vi.fn(), logout: vi.fn() } }))

const administrator = {
  administrator_uuid: '11111111-1111-4111-8111-111111111111',
  username: 'admin',
  display_name: 'Administrator',
  permissions: ['policy.assign'] as const,
}

function Probe() {
  const auth = useAuth()
  return <div>
    <output>{auth.status}:{auth.user?.username ?? 'none'}:{String(auth.hasPermission('policy.assign'))}</output>
    {auth.notice && <p>{auth.notice}</p>}
    <button onClick={() => void auth.login('admin', 'password').catch(() => undefined)}>login</button>
    <button onClick={() => void auth.logout()}>logout</button>
    <button onClick={auth.clearNotice}>clear</button>
  </div>
}

function renderProvider() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><AuthProvider><Probe /></AuthProvider></QueryClientProvider>)
}

describe('administrator session lifecycle', () => {
  beforeEach(() => {
    clearSessionToken()
    vi.clearAllMocks()
    vi.mocked(authService.login).mockResolvedValue({ access_token: 'memory-token', token_type: 'Bearer', expires_in: 900, administrator })
    vi.mocked(authService.getCurrentAdministrator).mockResolvedValue({ ...administrator, permissions: [...administrator.permissions] })
    vi.mocked(authService.logout).mockResolvedValue({ message: 'administrator logged out' })
  })
  afterEach(() => vi.useRealTimers())

  it('authenticates against login and me before exposing permissions', async () => {
    renderProvider()
    fireEvent.click(screen.getByRole('button', { name: 'login' }))
    await screen.findByText('authenticated:admin:true')
    expect(getSessionToken()).toBe('memory-token')
    expect(authService.getCurrentAdministrator).toHaveBeenCalledOnce()
  })

  it('clears browser state even when server logout cannot be confirmed', async () => {
    vi.mocked(authService.logout).mockRejectedValue(new Error('offline'))
    renderProvider()
    fireEvent.click(screen.getByRole('button', { name: 'login' }))
    await screen.findByText('authenticated:admin:true')
    fireEvent.click(screen.getByRole('button', { name: 'logout' }))
    await screen.findByText('anonymous:none:false')
    expect(getSessionToken()).toBeNull()
    expect(screen.getByText(/server revocation could not be confirmed/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'clear' }))
    await waitFor(() => expect(screen.queryByText(/server revocation/i)).not.toBeInTheDocument())
  })

  it('expires the session at the backend supplied lifetime', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-09-11T00:00:00Z'))
    vi.mocked(authService.login).mockResolvedValue({ access_token: 'short-token', token_type: 'Bearer', expires_in: 1, administrator })
    renderProvider()
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'login' })); await Promise.resolve() })
    expect(screen.getByText('authenticated:admin:true')).toBeInTheDocument()
    act(() => vi.advanceTimersByTime(1001))
    expect(screen.getByText('anonymous:none:false')).toBeInTheDocument()
    expect(screen.getByText(/session expired/i)).toBeInTheDocument()
  })

  it('returns to anonymous state when identity verification fails', async () => {
    vi.mocked(authService.getCurrentAdministrator).mockRejectedValue(new Error('rejected'))
    renderProvider()
    fireEvent.click(screen.getByRole('button', { name: 'login' }))
    await waitFor(() => expect(screen.getByText('anonymous:none:false')).toBeInTheDocument())
    expect(getSessionToken()).toBeNull()
  })
})
