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

export interface AdministratorInventoryItem extends Administrator {
  status: 'active' | 'disabled' | 'locked'
  created_at: string
  password_changed_at: string
  disabled_at: string | null
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
  asset_number?: string | null
  manufacturer?: string | null
  model?: string | null
  serial_number?: string | null
  date_received?: string | null
  condition?: string | null
  department?: string | null
  asset_lifecycle_status?: string | null
  asset_notes?: string | null
  enforcement_status?: 'COMPLIANT' | 'PARTIALLY_COMPLIANT' | 'NOT_REPORTED'
  connection_status?: 'ONLINE' | 'OFFLINE'
  connection_review?: boolean
  connection_review_after_days?: number
  last_compliance_check?: string | null
  failed_controls?: string[]
  sync_state?: 'LOCAL_ONLY' | 'PENDING_SYNC' | 'SENT_TO_DEVICE' | 'APPLIED' | 'FAILED'
}

export interface PolicyRevision {
  revision_uuid: string
  version: number
  payload: Record<string, unknown>
  content_hash: string
  created_at: string | null
  created_by: string | null
  sync_state?: 'LOCAL_ONLY' | 'PENDING_SYNC' | 'SENT_TO_DEVICE' | 'APPLIED' | 'FAILED'
}

export interface Policy {
  policy_uuid: string
  name: string
  status: 'draft' | 'active' | 'inactive' | 'revoked'
  created_at: string | null
  updated_at: string | null
  latest_revision: PolicyRevision | null
  revision_count?: number
  sync_state?: 'LOCAL_ONLY' | 'PENDING_SYNC' | 'SENT_TO_DEVICE' | 'APPLIED' | 'FAILED'
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
  issued_by_name: string | null
  reason: string | null
  policy_revision_uuid: string | null
  policy_name: string | null
  policy_version: number | null
}
export interface DeviceLocationAssignment { assignment_uuid: string; target_type: 'class' | 'department'; target_name: string; responsible_officer: string; assigned_at: string; expected_return_date: string | null; returned_at: string | null; issue_condition: string; return_condition: string | null }

export interface IssuedEnrollmentToken {
  token_uuid: string
  pairing_token: string
  expires_at: string
  bound_device_uuid: string | null
  school_uuid: string | null
  policy_revision_uuid: string | null
  policy_name: string | null
  policy_version: number | null
}

export interface AuditEvent {
  event_type: 'administrator_authentication' | 'device_enrollment' | 'device_asset' | 'policy_assignment' | 'policy_synchronization' | 'incident'
  event_uuid: string
  category: string
  occurred_at: string | null
  failure_class?: string | null
  operation?: string
  device_uuid?: string
  policy_revision_uuid?: string
}

export type IncidentStatus = 'OPEN' | 'UNDER_REVIEW' | 'ACTION_TAKEN' | 'CLOSED'
export interface Incident { incident_uuid: string; incident_number: string; device_uuid: string | null; asset_number: string | null; incident_type: string; description: string; reported_by: string; reported_at: string | null; status: IncidentStatus; action_taken: string | null; responsible_person: string | null; closed_at: string | null; created_by: string | null; updated_at: string | null }
export interface PolicyChange { event_uuid: string; policy_name: string | null; previous_policy_name: string | null; previous_version: number | null; new_version: number | null; administrator: string | null; occurred_at: string | null; device_uuid: string | null; asset_number: string | null; devices_affected: number; reason: string; operation: string; result: string }
export interface ViolationReportItem { event_uuid: string; device_uuid: string; asset_number: string | null; class_name: string | null; event_code: string; violation_type: string; outcome: string; rule_id: string | null; details: Record<string, string | number | boolean | null>; policy_uuid: string | null; policy_name: string | null; policy_version: number | null; occurred_at: string | null; received_at: string | null; sequence: number; event_hash: string; previous_event_hash: string | null }

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
export interface School { school_uuid: string; name: string; district: string; school_type: string; contact_person: string; official_telephone: string; official_email: string | null; physical_location: string; authorised_administrator_name: string; timezone: string; created_at: string | null }
export interface SchoolRegistration { name: string; district: string; school_type: string; contact_person: string; official_telephone: string; official_email: string | null; physical_location: string; authorised_administrator_name: string; timezone: string }
export interface ManagedApplication { application_uuid: string; display_name: string; package_name: string; signing_certificate_sha256: string | null; category: string; education_approved: boolean; mandatory_block: boolean; status: 'enabled' | 'disabled'; created_at: string; updated_at: string }
export interface ManagedDomain { domain_uuid: string; domain: string; category: string; status: 'enabled' | 'disabled'; created_at: string; updated_at: string }
export type SupportedLanguage = 'eng' | 'ach' | 'lgg' | 'teo' | 'nyn' | 'lug'
export interface TranslationResult { translated_text: string; source_language: SupportedLanguage | null; target_language: SupportedLanguage; cached: boolean; content_class: 'approved_dynamic'; quality_status: 'machine' | 'reviewed' | 'approved' }
