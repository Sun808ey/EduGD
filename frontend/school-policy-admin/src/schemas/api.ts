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
  ])),
})

export const loginSchema = z.object({
  access_token: z.string().min(1),
  token_type: z.literal('Bearer'),
  expires_in: z.number().int().positive().max(3600),
  administrator: administratorSchema.omit({ permissions: true }),
})

export const meSchema = z.object({ administrator: administratorSchema })

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
