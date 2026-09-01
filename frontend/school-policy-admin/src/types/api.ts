export interface ApiErrorShape {
  code: string
  message: string
}

export interface ApiErrorResponse {
  error: ApiErrorShape
}

export interface AdministratorSummary {
  administrator_uuid: string
  username: string
  display_name: string
  permissions?: string[]
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  administrator: AdministratorSummary
}

export interface CurrentAdministratorResponse {
  administrator: AdministratorSummary
}

export interface PaginationMeta {
  page: number
  per_page: number
  total: number
  has_next: boolean
}

export interface PaginatedResponse<T> {
  items: T[]
  pagination: PaginationMeta
}

export interface DeviceSummary {
  device_uuid: string
  android_version?: string | null
  api_level?: number | null
  status: string
  enrollment_state?: string | null
  registered_at?: string | null
  last_sync_at?: string | null
  active_policy_assignment?: PolicyAssignmentSummary | null
}

export type DeviceDetail = DeviceSummary & {
  created_at?: string | null
  updated_at?: string | null
}

export interface PolicySummary {
  policy_uuid: string
  name: string
  status: string
  created_at?: string | null
  updated_at?: string | null
  latest_revision?: PolicyRevisionSummary | null
}

export interface AuditEventSummary {
  event_uuid: string
  event_type: string
  category: string
  occurred_at: string | null
  failure_class?: string | null
}

export interface PolicyAssignmentSummary {
  event_uuid: string
  policy_revision_uuid: string
  policy_uuid: string
  policy_name: string
  policy_version: number
  status: string
  assigned_at?: string | null
  superseded_at?: string | null
}

export interface PolicyRevisionSummary {
  revision_uuid: string
  version: number
  created_at?: string | null
  content_hash?: string
  created_by?: string | null
  payload?: Record<string, unknown>
}

export interface PolicyDetail extends PolicySummary {
  revision_count: number
}

export interface EnrollmentTokenResponse {
  token_uuid: string
  pairing_token: string
  expires_at: string
  bound_device_uuid: string | null
}

export interface EnrollmentTokenSummary {
  token_uuid: string
  status: string
  bound_device_uuid: string | null
  consumed_by_device_uuid?: string | null
  expires_at: string | null
  created_at: string | null
  revoked_at?: string | null
  reason?: string | null
}

export interface PolicyAssignmentResponse {
  assignment: PolicyAssignmentSummary
}

export interface PolicyClearResponse {
  clear_intent: {
    event_uuid: string
    device_uuid: string
    operation: 'clear'
  }
}
