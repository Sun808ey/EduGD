import { createContext } from 'react'
import type { AdministratorSummary } from '@/types/api'

export interface AuthContextValue {
  user: AdministratorSummary | null
  token: string | null
  isAuthenticated: boolean
  loading: boolean
  error: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined)
