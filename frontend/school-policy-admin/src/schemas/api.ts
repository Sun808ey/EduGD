import { z } from 'zod'

const uuid = z.string().uuid()
const nullableDate = z.string().nullable()
const pagination = z.object({
  page: z.number().int().positive(),
  per_page: z.number().int().min(1).max(100),
  total: z.number().int().nonnegative(),
  has_next: z.boolean(),
})

export const administratorSchema = z.object({
  administrator_uuid: uuid,
  username: z.string(),
  display_name: z.string(),
  permissions: z.array(z.enum([
    'administrator.manage',
    'enrollment_token.issue',
    'enrollment_token.revoke',
    'device_credential.revoke',
    'policy.assign',
    'device.control',
    'policy.manage',
  ])),
})

export const loginSchema = z.object({
  access_token: z.string().min(1),
  token_type: z.literal('Bearer'),
  expires_in: z.number().int().positive().max(3600),
  administrator: administratorSchema.omit({ permissions: true }),
})

export const meSchema = z.object({ administrator: administratorSchema })
export const administratorCreateSchema = z.object({
  administrator_uuid: uuid,
  username: z.string(),
  permissions: administratorSchema.shape.permissions,
  revoked_sessions: z.number().int().nonnegative(),
})
export const administratorInventorySchema = administratorSchema.extend({
  status: z.enum(['active', 'disabled', 'locked']),
  created_at: z.string(),
  password_changed_at: z.string(),
  disabled_at: z.string().nullable(),
})
export const administratorsSchema = z.object({
  administrators: z.array(administratorInventorySchema),
  pagination,
})
export const administratorDetailSchema = z.object({ administrator: administratorInventorySchema })
export const administratorMutationSchema = z.object({
  administrator_uuid: uuid,
  revoked_sessions: z.number().int().nonnegative().optional(),
  message: z.string().optional(),
})

const assignmentSchema = z.object({
  event_uuid: uuid,
  policy_revision_uuid: uuid,
  policy_uuid: uuid,
  policy_name: z.string(),
  policy_version: z.number().int().positive(),
  status: z.string(),
  assigned_at: nullableDate,
  superseded_at: nullableDate,
})

export const deviceSchema = z.object({
  device_uuid: uuid,
  android_version: z.string().nullable(),
  api_level: z.number().int().nullable(),
  status: z.enum(['active', 'suspended', 'retired']),
  enrollment_state: z.string().nullable(),
  legacy_enrollment_eligible: z.boolean(),
  registered_at: nullableDate,
  last_sync_at: nullableDate,
  active_policy_assignment: assignmentSchema.nullable(),
  asset_number: z.string().nullable().optional(), manufacturer: z.string().nullable().optional(), model: z.string().nullable().optional(), serial_number: z.string().nullable().optional(), date_received: z.string().nullable().optional(), condition: z.string().nullable().optional(), department: z.string().nullable().optional(), asset_lifecycle_status: z.string().nullable().optional(), asset_notes: z.string().nullable().optional(),
  enforcement_status: z.enum(['COMPLIANT', 'PARTIALLY_COMPLIANT', 'NOT_REPORTED']).optional(), connection_status: z.enum(['ONLINE', 'OFFLINE']).optional(), connection_review: z.boolean().optional(), connection_review_after_days: z.number().int().positive().optional(), last_compliance_check: nullableDate.optional(), failed_controls: z.array(z.string()).optional(),
  sync_state: z.enum(['LOCAL_ONLY', 'PENDING_SYNC', 'SENT_TO_DEVICE', 'APPLIED', 'FAILED']).optional(),
  created_at: nullableDate.optional(),
  updated_at: nullableDate.optional(),
})

export const devicesSchema = z.object({ devices: z.array(deviceSchema), pagination })

export const revisionSchema = z.object({
  revision_uuid: uuid,
  version: z.number().int().positive(),
  payload: z.record(z.string(), z.unknown()),
  content_hash: z.string(),
  created_at: nullableDate,
  created_by: z.string().nullable(),
})

export const policySchema = z.object({
  policy_uuid: uuid,
  name: z.string(),
  status: z.enum(['draft', 'active', 'inactive', 'revoked']),
  created_at: nullableDate,
  updated_at: nullableDate,
  latest_revision: revisionSchema.nullable(),
  revision_count: z.number().int().nonnegative().optional(),
  sync_state: z.enum(['LOCAL_ONLY', 'PENDING_SYNC', 'SENT_TO_DEVICE', 'APPLIED', 'FAILED']).optional(),
})

export const policiesSchema = z.object({ policies: z.array(policySchema), pagination })
export const revisionsSchema = z.object({ revisions: z.array(revisionSchema), pagination })
export const policyDetailSchema = z.object({ policy: policySchema })
export const deviceDetailSchema = z.object({ device: deviceSchema })
export const currentAssignmentSchema = z.object({
  policy_assignment: z.object({ device_uuid: uuid, assignment: assignmentSchema.nullable() }),
})

export const assignmentMutationSchema = z.object({
  assignment: z.object({
    event_uuid: uuid,
    device_uuid: uuid,
    policy_revision_uuid: uuid,
    status: z.string(),
    replaced: z.boolean(),
  }),
})

export const clearMutationSchema = z.object({
  clear_intent: z.object({ event_uuid: uuid, device_uuid: uuid, operation: z.literal('clear') }),
})

export const enrollmentTokenSchema = z.object({
  token_uuid: uuid,
  status: z.string(),
  bound_device_uuid: uuid.nullable(),
  consumed_by_device_uuid: uuid.nullable(),
  expires_at: nullableDate,
  created_at: nullableDate,
  revoked_at: nullableDate,
  issued_by: z.string().nullable(),
  issued_by_name: z.string().nullable(),
  reason: z.string().nullable(),
  policy_revision_uuid: uuid.nullable(),
  policy_name: z.string().nullable(),
  policy_version: z.number().int().positive().nullable(),
})

export const enrollmentTokensSchema = z.object({ enrollment_tokens: z.array(enrollmentTokenSchema), pagination })
export const issuedEnrollmentTokenSchema = z.object({
  token_uuid: uuid,
  pairing_token: z.string().min(1),
  expires_at: z.string(),
  bound_device_uuid: uuid.nullable(),
  school_uuid: uuid.nullable(),
  policy_revision_uuid: uuid.nullable(),
  policy_name: z.string().nullable(),
  policy_version: z.number().int().positive().nullable(),
})

export const auditEventSchema = z.object({
  event_type: z.enum(['administrator_authentication', 'device_enrollment', 'device_asset', 'policy_assignment', 'policy_synchronization', 'incident']),
  event_uuid: uuid,
  category: z.string(),
  occurred_at: nullableDate,
  failure_class: z.string().nullable().optional(),
  operation: z.string().optional(),
  device_uuid: uuid.optional(),
  policy_revision_uuid: uuid.optional(),
})
export const auditEventsSchema = z.object({ audit_events: z.array(auditEventSchema), pagination })
export const incidentSchema = z.object({ incident_uuid: uuid, incident_number: z.string(), device_uuid: uuid.nullable(), asset_number: z.string().nullable(), incident_type: z.string(), description: z.string(), reported_by: z.string(), reported_at: nullableDate, status: z.enum(['OPEN', 'UNDER_REVIEW', 'ACTION_TAKEN', 'CLOSED']), action_taken: z.string().nullable(), responsible_person: z.string().nullable(), closed_at: nullableDate, created_by: z.string().nullable(), updated_at: nullableDate })
export const incidentsSchema = z.object({ incidents: z.array(incidentSchema), pagination })
export const incidentResponseSchema = z.object({ incident: incidentSchema })
export const policyChangeSchema = z.object({ event_uuid: uuid, policy_name: z.string().nullable(), previous_policy_name: z.string().nullable(), previous_version: z.number().int().positive().nullable(), new_version: z.number().int().positive().nullable(), administrator: z.string().nullable(), occurred_at: nullableDate, device_uuid: uuid.nullable(), asset_number: z.string().nullable(), devices_affected: z.number().int().positive(), reason: z.string(), operation: z.string(), result: z.string() })
export const policyChangesSchema = z.object({ policy_changes: z.array(policyChangeSchema), pagination })
export const violationReportItemSchema = z.object({ event_uuid: uuid, device_uuid: uuid, asset_number: z.string().nullable(), class_name: z.string().nullable(), event_code: z.string(), violation_type: z.string(), outcome: z.string(), rule_id: z.string().nullable(), details: z.record(z.string(), z.union([z.string(), z.number(), z.boolean(), z.null()])), policy_uuid: uuid.nullable(), policy_name: z.string().nullable(), policy_version: z.number().int().positive().nullable(), occurred_at: nullableDate, received_at: nullableDate, sequence: z.number().int().positive(), event_hash: z.string(), previous_event_hash: z.string().nullable() })
export const violationReportsSchema = z.object({ violations: z.array(violationReportItemSchema), pagination })
export const messageSchema = z.object({ message: z.string() })

export const blockOverrideSchema = z.object({ version: z.number().int().positive(), status: z.enum(['active', 'cleared']), reason: z.string(), issued_at: z.string(), cleared_at: nullableDate })
export const blockOverrideResponseSchema = z.object({ override: blockOverrideSchema.nullable() })
export const dpcEvidenceSchema = z.object({ kind: z.enum(['usage', 'override', 'web_filter', 'policy_application']), occurred_at: nullableDate, usage_date: z.string().optional(), active_minutes: z.number().int().optional(), operation: z.string().optional(), reason: z.string().optional(), domain_hash: z.string().optional(), rule_id: z.string().optional(), outcome: z.string().optional(), error_code: z.string().nullable().optional(), policy_uuid: uuid.nullable().optional(), revision_uuid: uuid.nullable().optional() })
export const dpcEvidenceResponseSchema = z.object({ evidence: z.array(dpcEvidenceSchema), pagination })
export const dpcSummarySchema = z.object({ summary: z.object({ managed_devices: z.number().int().nonnegative(), active_block_overrides: z.number().int().nonnegative(), active_v3_assignments: z.number().int().nonnegative(), enforcement_failures: z.number().int().nonnegative() }) })
export const schoolSchema = z.object({ school_uuid: uuid, name: z.string(), district: z.string(), school_type: z.string(), contact_person: z.string(), official_telephone: z.string(), official_email: z.string().nullable(), physical_location: z.string(), authorised_administrator_name: z.string(), timezone: z.string(), created_at: nullableDate })
export const schoolResponseSchema = z.object({ school: schoolSchema.nullable() })
export const policyCreateSchema = z.object({ policy_uuid: uuid, status: z.enum(['draft', 'active', 'inactive', 'revoked']), sync_state: z.enum(['LOCAL_ONLY', 'PENDING_SYNC', 'SENT_TO_DEVICE', 'APPLIED', 'FAILED']).optional() })
export const policyRevisionMutationSchema = z.object({ revision_uuid: uuid, version: z.number().int().positive(), sync_state: z.enum(['LOCAL_ONLY', 'PENDING_SYNC', 'SENT_TO_DEVICE', 'APPLIED', 'FAILED']).optional() })
export const policyLifecycleSchema = z.object({ policy_uuid: uuid, status: z.enum(['active', 'inactive', 'revoked']), sync_state: z.enum(['LOCAL_ONLY', 'PENDING_SYNC', 'SENT_TO_DEVICE', 'APPLIED', 'FAILED']).optional() })
export const managedApplicationSchema = z.object({ application_uuid: uuid, display_name: z.string(), package_name: z.string(), signing_certificate_sha256: z.string().nullable(), category: z.string(), education_approved: z.boolean(), mandatory_block: z.boolean(), status: z.enum(['enabled', 'disabled']), created_at: z.string(), updated_at: z.string() })
export const managedApplicationsSchema = z.object({ applications: z.array(managedApplicationSchema) })
export const managedDomainSchema = z.object({ domain_uuid: uuid, domain: z.string(), category: z.string(), status: z.enum(['enabled', 'disabled']), created_at: z.string(), updated_at: z.string() })
export const managedDomainsSchema = z.object({ domains: z.array(managedDomainSchema) })
export const translationResultSchema = z.object({ translated_text: z.string().min(1), source_language: z.string().nullable(), target_language: z.enum(['eng', 'ach', 'lgg', 'teo', 'nyn', 'lug']), cached: z.boolean(), content_class: z.literal('approved_dynamic'), quality_status: z.enum(['machine', 'reviewed', 'approved']).default('machine') })
