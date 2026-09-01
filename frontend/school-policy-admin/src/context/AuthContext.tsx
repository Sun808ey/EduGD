import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { authService } from '@/services/auth.service'
import { AuthContext } from '@/context/auth-context'
import type { AuthContextValue } from '@/context/auth-context'
import type { AdministratorSummary } from '@/types/api'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AdministratorSummary | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refreshUser = useCallback(async () => {
    const savedToken = authService.getStoredToken()
    const savedUser = authService.getStoredUser()

    if (!savedToken) {
      setUser(null)
      setToken(null)
      setLoading(false)
      return
    }

    setToken(savedToken)

    if (savedUser) {
      setUser(savedUser)
    }

    try {
      const currentUser = await authService.getCurrentAdministrator()
      setUser(currentUser)
      setError(null)
    } catch {
      await authService.logout().catch(() => undefined)
      setUser(null)
      setToken(null)
      setError('Your session expired. Please sign in again.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let active = true
    void (async () => {
      await refreshUser()
      if (!active) return
    })()
    return () => { active = false }
  }, [refreshUser])

  const login = useCallback(async (username: string, password: string) => {
    setLoading(true)
    setError(null)

    try {
      const result = await authService.login(username, password)
      setToken(result.access_token)
      setUser(result.administrator)
    } catch (err) {
      setUser(null)
      setToken(null)
      setError(err instanceof Error ? err.message : 'Unable to sign in. Please try again.')
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const logout = useCallback(async () => {
    await authService.logout().catch(() => undefined)
    setUser(null)
    setToken(null)
    setError(null)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      isAuthenticated: Boolean(token && user),
      loading,
      error,
      login,
      logout,
      refreshUser,
    }),
    [error, loading, login, logout, refreshUser, token, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
