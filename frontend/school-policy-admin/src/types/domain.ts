export type AppRoute = '/dashboard' | '/devices' | '/policies' | '/logs'

export interface LoginFormValues {
  username: string
  password: string
}

export interface AuthSessionState {
  token: string | null
  user: {
    administrator_uuid: string
    username: string
    display_name: string
    permissions?: string[]
  } | null
}

export interface DeviceStatusSummary {
  device_uuid: string
  display_name: string
  status: 'active' | 'pending' | 'disabled' | 'unknown'
  platform?: string
}

export interface PolicyStatusSummary {
  policy_uuid: string
  name: string
  revision: number
  status: 'draft' | 'active' | 'archived'
}
