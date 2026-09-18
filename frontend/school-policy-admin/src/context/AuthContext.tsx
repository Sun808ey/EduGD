import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { authService } from '@/services/auth.service'
import { clearSessionToken, getSessionExpiry, setSessionToken } from '@/auth/session'
import { setUnauthorizedHandler } from '@/services/api'
import { AuthContext } from '@/context/auth-context'
import type { Administrator, AdministratorPermission } from '@/types/api.types'
import type { AuthStatus } from '@/context/auth-context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Administrator | null>(null)
  const [status, setStatus] = useState<AuthStatus>('anonymous')
  const [notice, setNotice] = useState<string | null>(null)
  const expiryTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const queryClient = useQueryClient()

  const endSession = useCallback((message?: string) => {
    clearSessionToken()
    if (expiryTimer.current) clearTimeout(expiryTimer.current)
    queryClient.cancelQueries()
    queryClient.clear()
    setUser(null)
    setStatus('anonymous')
    setNotice(message ?? null)
  }, [queryClient])

  useEffect(() => {
    setUnauthorizedHandler(() => endSession('Your session expired or was revoked. Please sign in again.'))
    return () => setUnauthorizedHandler(undefined)
  }, [endSession])

  const scheduleExpiry = useCallback(() => {
    if (expiryTimer.current) clearTimeout(expiryTimer.current)
    const remaining = Math.max(0, getSessionExpiry() - Date.now())
    expiryTimer.current = setTimeout(() => endSession('Your session expired. Please sign in again.'), remaining)
  }, [endSession])

  const login = useCallback(async (username: string, password: string) => {
    setStatus('authenticating')
    setNotice(null)
    try {
      const loginResult = await authService.login(username, password)
      setSessionToken(loginResult.access_token, loginResult.expires_in)
      const currentUser = await authService.getCurrentAdministrator()
      setUser(currentUser)
      setStatus('authenticated')
      scheduleExpiry()
    } catch (error) {
      endSession()
      throw error
    }
  }, [endSession, scheduleExpiry])

  const logout = useCallback(async () => {
    setStatus('logging_out')
    let warning: string | undefined
    try { await authService.logout() } catch { warning = 'You are signed out locally, but server revocation could not be confirmed.' }
    endSession(warning)
  }, [endSession])

  const value = useMemo(() => ({
    user,
    status,
    notice,
    isAuthenticated: status === 'authenticated' && user !== null,
    login,
    logout,
    hasPermission: (permission: AdministratorPermission) => user?.permissions.includes(permission) ?? false,
    clearNotice: () => setNotice(null),
  }), [login, logout, notice, status, user])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
