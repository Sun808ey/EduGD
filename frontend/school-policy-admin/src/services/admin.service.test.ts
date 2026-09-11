import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from '@/services/api'
import { adminService } from '@/services/admin.service'

vi.mock('@/services/api', () => ({ default: { get: vi.fn(), post: vi.fn() } }))

const deviceUuid = '11111111-1111-4111-8111-111111111111'
const policyUuid = '22222222-2222-4222-8222-222222222222'
const revisionUuid = '33333333-3333-4333-8333-333333333333'
const eventUuid = '44444444-4444-4444-8444-444444444444'
const tokenUuid = '55555555-5555-4555-8555-555555555555'
const pagination = { page: 1, per_page: 25, total: 0, has_next: false }
const revision = { revision_uuid: revisionUuid, version: 1, payload: {}, content_hash: 'abc', created_at: null, created_by: null }
const policy = { policy_uuid: policyUuid, name: 'School day', status: 'active', created_at: null, updated_at: null, latest_revision: revision }
const device = { device_uuid: deviceUuid, android_version: '14', api_level: 34, status: 'active', enrollment_state: 'enrolled', legacy_enrollment_eligible: false, registered_at: null, last_sync_at: null, active_policy_assignment: null }

describe('administrator API service', () => {
  beforeEach(() => vi.clearAllMocks())

  it('uses the read routes, filters and runtime response validation', async () => {
    vi.mocked(api.get)
      .mockResolvedValueOnce({ data: { devices: [device], pagination: { ...pagination, total: 1 } } })
      .mockResolvedValueOnce({ data: { device } })
      .mockResolvedValueOnce({ data: { policy_assignment: { device_uuid: deviceUuid, assignment: null } } })
      .mockResolvedValueOnce({ data: { policies: [policy], pagination: { ...pagination, total: 1 } } })
      .mockResolvedValueOnce({ data: { policy } })
      .mockResolvedValueOnce({ data: { revisions: [revision], pagination: { ...pagination, total: 1 } } })
      .mockResolvedValueOnce({ data: { enrollment_tokens: [], pagination } })
      .mockResolvedValueOnce({ data: { audit_events: [], pagination } })

    await expect(adminService.listDevices({ page: 1, perPage: 25 }, 'active')).resolves.toMatchObject({ devices: [device] })
    await expect(adminService.getDevice(deviceUuid)).resolves.toMatchObject(device)
    await expect(adminService.getCurrentAssignment(deviceUuid)).resolves.toMatchObject({ device_uuid: deviceUuid })
    await expect(adminService.listPolicies({ page: 1, perPage: 25 }, 'active')).resolves.toMatchObject({ policies: [policy] })
    await expect(adminService.getPolicy(policyUuid)).resolves.toMatchObject(policy)
    await expect(adminService.listPolicyRevisions(policyUuid, { page: 1, perPage: 25 })).resolves.toMatchObject({ revisions: [revision] })
    await expect(adminService.listEnrollmentTokens({ page: 1, perPage: 25 }, 'locked')).resolves.toMatchObject({ enrollment_tokens: [] })
    await expect(adminService.listAuditEvents({ page: 1, perPage: 25 }, 'device_enrollment')).resolves.toMatchObject({ audit_events: [] })
    expect(api.get).toHaveBeenNthCalledWith(1, '/admin/devices', expect.objectContaining({ params: { page: 1, per_page: 25, status: 'active' } }))
  })

  it('loads every policy page before offering assignment choices', async () => {
    vi.mocked(api.get)
      .mockResolvedValueOnce({ data: { policies: [policy], pagination: { page: 1, per_page: 100, total: 2, has_next: true } } })
      .mockResolvedValueOnce({ data: { policies: [{ ...policy, policy_uuid: deviceUuid }], pagination: { page: 2, per_page: 100, total: 2, has_next: false } } })
    await expect(adminService.listAllPolicies()).resolves.toHaveLength(2)
    expect(api.get).toHaveBeenCalledTimes(2)
  })

  it('uses the exact audited mutation routes and payloads', async () => {
    vi.mocked(api.post)
      .mockResolvedValueOnce({ data: { token_uuid: tokenUuid, pairing_token: 'one-time', expires_at: '2026-09-11T10:00:00Z', bound_device_uuid: null } })
      .mockResolvedValueOnce({ data: { message: 'enrollment token revoked' } })
      .mockResolvedValueOnce({ data: { assignment: { event_uuid: eventUuid, device_uuid: deviceUuid, policy_revision_uuid: revisionUuid, status: 'active', replaced: false } } })
      .mockResolvedValueOnce({ data: { clear_intent: { event_uuid: eventUuid, device_uuid: deviceUuid, operation: 'clear' } } })
      .mockResolvedValueOnce({ data: { message: 'device credential revoked' } })

    await adminService.issueEnrollmentToken('new device')
    await adminService.revokeEnrollmentToken(tokenUuid, 'unused')
    await adminService.assignPolicy(deviceUuid, revisionUuid, 'approved')
    await adminService.clearPolicy(deviceUuid, 'retired')
    await adminService.revokeDeviceCredential(deviceUuid, 'lost')

    expect(api.post).toHaveBeenNthCalledWith(1, '/admin/enrollment-tokens', { reason: 'new device', bound_device_uuid: null })
    expect(api.post).toHaveBeenNthCalledWith(3, `/admin/devices/${deviceUuid}/policy-assignment`, { policy_revision_uuid: revisionUuid, reason: 'approved' })
    expect(api.post).toHaveBeenNthCalledWith(5, `/admin/devices/${deviceUuid}/credentials/revoke`, { reason: 'lost' })
  })

  it('encodes untrusted route parameters', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: { device } })
    await adminService.getDevice('../value')
    expect(api.get).toHaveBeenCalledWith('/admin/devices/..%2Fvalue', expect.anything())
  })
})
