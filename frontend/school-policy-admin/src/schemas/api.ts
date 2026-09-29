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
  reason: z.string().nullable(),
})

export const enrollmentTokensSchema = z.object({ enrollment_tokens: z.array(enrollmentTokenSchema), pagination })
export const issuedEnrollmentTokenSchema = z.object({
  token_uuid: uuid,
  pairing_token: z.string().min(1),
  expires_at: z.string(),
  bound_device_uuid: uuid.nullable(),
})

export const auditEventSchema = z.object({
  event_type: z.enum(['administrator_authentication', 'device_enrollment', 'policy_assignment', 'policy_synchronization']),
  event_uuid: uuid,
  category: z.string(),
  occurred_at: nullableDate,
  failure_class: z.string().nullable().optional(),
  operation: z.string().optional(),
  device_uuid: uuid.optional(),
  policy_revision_uuid: uuid.optional(),
})
export const auditEventsSchema = z.object({ audit_events: z.array(auditEventSchema), pagination })
export const messageSchema = z.object({ message: z.string() })

export const blockOverrideSchema = z.object({ version: z.number().int().positive(), status: z.enum(['active', 'cleared']), reason: z.string(), issued_at: z.string(), cleared_at: nullableDate })
export const blockOverrideResponseSchema = z.object({ override: blockOverrideSchema.nullable() })
export const dpcEvidenceSchema = z.object({ kind: z.enum(['usage', 'override', 'web_filter', 'policy_application']), occurred_at: nullableDate, usage_date: z.string().optional(), active_minutes: z.number().int().optional(), operation: z.string().optional(), reason: z.string().optional(), domain_hash: z.string().optional(), rule_id: z.string().optional(), outcome: z.string().optional(), error_code: z.string().nullable().optional(), policy_uuid: uuid.nullable().optional(), revision_uuid: uuid.nullable().optional() })
export const dpcEvidenceResponseSchema = z.object({ evidence: z.array(dpcEvidenceSchema), pagination })
export const dpcSummarySchema = z.object({ summary: z.object({ managed_devices: z.number().int().nonnegative(), active_block_overrides: z.number().int().nonnegative(), active_v3_assignments: z.number().int().nonnegative(), enforcement_failures: z.number().int().nonnegative() }) })
export const policyCreateSchema = z.object({ policy_uuid: uuid, status: z.enum(['draft', 'active', 'inactive', 'revoked']) })
export const managedApplicationSchema = z.object({ application_uuid: uuid, display_name: z.string(), package_name: z.string(), signing_certificate_sha256: z.string().nullable(), category: z.string(), education_approved: z.boolean(), mandatory_block: z.boolean(), status: z.enum(['enabled', 'disabled']), created_at: z.string(), updated_at: z.string() })
export const managedApplicationsSchema = z.object({ applications: z.array(managedApplicationSchema) })
export const translationResultSchema = z.object({ translated_text: z.string().min(1), source_language: z.string().nullable(), target_language: z.enum(['eng', 'ach', 'lgg', 'teo', 'nyn', 'lug']), cached: z.boolean(), content_class: z.literal('approved_dynamic'), quality_status: z.enum(['machine', 'reviewed', 'approved']).default('machine') })
