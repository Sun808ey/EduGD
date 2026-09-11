import { createContext } from 'react'
import type { Administrator, AdministratorPermission } from '@/types/api.types'

export type AuthStatus = 'anonymous' | 'authenticating' | 'authenticated' | 'logging_out'

export interface AuthContextValue {
  user: Administrator | null
  status: AuthStatus
  notice: string | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  hasPermission: (permission: AdministratorPermission) => boolean
  clearNotice: () => void
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined)
