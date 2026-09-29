export type AdministratorPermission =
  | 'administrator.manage'
  | 'enrollment_token.issue'
  | 'enrollment_token.revoke'
  | 'device_credential.revoke'
  | 'policy.assign'
  | 'device.control'
  | 'policy.manage'

export interface Administrator {
  administrator_uuid: string
  username: string
  display_name: string
  permissions: AdministratorPermission[]
}

export interface LoginResponse {
  access_token: string
  token_type: 'Bearer'
  expires_in: number
  administrator: Omit<Administrator, 'permissions'>
}

export interface Pagination {
  page: number
  per_page: number
  total: number
  has_next: boolean
}

export interface PolicyAssignment {
  event_uuid: string
  policy_revision_uuid: string
  policy_uuid: string
  policy_name: string
  policy_version: number
  status: string
  assigned_at: string | null
  superseded_at: string | null
}

export interface Device {
  device_uuid: string
  android_version: string | null
  api_level: number | null
  status: 'active' | 'suspended' | 'retired'
  enrollment_state: string | null
  legacy_enrollment_eligible: boolean
  registered_at: string | null
  last_sync_at: string | null
  active_policy_assignment: PolicyAssignment | null
  created_at?: string | null
  updated_at?: string | null
}

export interface PolicyRevision {
  revision_uuid: string
  version: number
  payload: Record<string, unknown>
  content_hash: string
  created_at: string | null
  created_by: string | null
}

export interface Policy {
  policy_uuid: string
  name: string
  status: 'draft' | 'active' | 'inactive' | 'revoked'
  created_at: string | null
  updated_at: string | null
  latest_revision: PolicyRevision | null
  revision_count?: number
}

export interface EnrollmentToken {
  token_uuid: string
  status: string
  bound_device_uuid: string | null
  consumed_by_device_uuid: string | null
  expires_at: string | null
  created_at: string | null
  revoked_at: string | null
  issued_by: string | null
  reason: string | null
}

export interface IssuedEnrollmentToken {
  token_uuid: string
  pairing_token: string
  expires_at: string
  bound_device_uuid: string | null
}

export interface AuditEvent {
  event_type: 'administrator_authentication' | 'device_enrollment' | 'policy_assignment' | 'policy_synchronization'
  event_uuid: string
  category: string
  occurred_at: string | null
  failure_class?: string | null
  operation?: string
  device_uuid?: string
  policy_revision_uuid?: string
}

export interface PageRequest {
  page: number
  perPage: number
}

export interface ApiFailure {
  error: { code: string; message: string }
}

export interface BlockOverride { version: number; status: 'active' | 'cleared'; reason: string; issued_at: string; cleared_at: string | null }
export interface DpcEvidence { kind: 'usage' | 'override' | 'web_filter' | 'policy_application'; occurred_at: string | null; usage_date?: string; active_minutes?: number; operation?: string; reason?: string; domain_hash?: string; rule_id?: string; outcome?: string; error_code?: string | null; policy_uuid?: string | null; revision_uuid?: string | null }
export interface DpcSummary { managed_devices: number; active_block_overrides: number; active_v3_assignments: number; enforcement_failures: number }
export interface ManagedApplication { application_uuid: string; display_name: string; package_name: string; signing_certificate_sha256: string | null; category: string; education_approved: boolean; mandatory_block: boolean; status: 'enabled' | 'disabled'; created_at: string; updated_at: string }
export type SupportedLanguage = 'eng' | 'ach' | 'lgg' | 'teo' | 'nyn' | 'lug'
export interface TranslationResult { translated_text: string; source_language: SupportedLanguage | null; target_language: SupportedLanguage; cached: boolean; content_class: 'approved_dynamic'; quality_status: 'machine' | 'reviewed' | 'approved' }
