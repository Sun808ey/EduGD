import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from '@/services/api'
import { adminService } from '@/services/admin.service'
import { AppError } from '@/services/errors'

vi.mock('@/services/api', () => ({ default: { get: vi.fn(), post: vi.fn(), patch: vi.fn() } }))

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
  beforeEach(() => { vi.resetAllMocks(); window.localStorage.clear() })

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
    const { listAllPolicies } = adminService
    await expect(listAllPolicies()).resolves.toHaveLength(2)
    expect(api.get).toHaveBeenCalledTimes(2)
  })

  it('uses the exact audited mutation routes and payloads', async () => {
    vi.mocked(api.post)
      .mockResolvedValueOnce({ data: { token_uuid: tokenUuid, pairing_token: 'one-time', expires_at: '2026-09-11T10:00:00Z', bound_device_uuid: null, school_uuid: '77777777-7777-4777-8777-777777777777', policy_revision_uuid: revisionUuid, policy_name: 'School day', policy_version: 1 } })
      .mockResolvedValueOnce({ data: { message: 'enrollment token revoked' } })
      .mockResolvedValueOnce({ data: { assignment: { event_uuid: eventUuid, device_uuid: deviceUuid, policy_revision_uuid: revisionUuid, status: 'active', replaced: false } } })
      .mockResolvedValueOnce({ data: { clear_intent: { event_uuid: eventUuid, device_uuid: deviceUuid, operation: 'clear' } } })
      .mockResolvedValueOnce({ data: { message: 'device credential revoked' } })

    await adminService.issueEnrollmentToken({ reason: 'new device', school_uuid: '77777777-7777-4777-8777-777777777777', policy_revision_uuid: revisionUuid })
    await adminService.revokeEnrollmentToken(tokenUuid, 'unused')
    await adminService.assignPolicy(deviceUuid, revisionUuid, 'approved')
    await adminService.clearPolicy(deviceUuid, 'retired')
    await adminService.revokeDeviceCredential(deviceUuid, 'lost')

    expect(api.post).toHaveBeenNthCalledWith(1, '/admin/enrollment-tokens', { reason: 'new device', school_uuid: '77777777-7777-4777-8777-777777777777', policy_revision_uuid: revisionUuid, bound_device_uuid: null })
    expect(api.post).toHaveBeenNthCalledWith(3, `/admin/devices/${deviceUuid}/policy-assignment`, { policy_revision_uuid: revisionUuid, reason: 'approved' })
    expect(api.post).toHaveBeenNthCalledWith(5, `/admin/devices/${deviceUuid}/credentials/revoke`, { reason: 'lost' })
  })

  it('creates an administrator through the protected management endpoint', async () => {
    const administrator = {
      administrator_uuid: '66666666-6666-4666-8666-666666666666',
      username: 'policy.admin',
      permissions: ['administrator.manage', 'policy.manage'],
      revoked_sessions: 0,
    }
    vi.mocked(api.post).mockResolvedValueOnce({ data: administrator })

    await expect(adminService.createAdministrator(
      'policy.admin',
      'Policy Administrator',
      'SecondAdministrator!2026',
      'CurrentAdministrator!2026',
      'approved provisioning',
    )).resolves.toEqual(administrator)

    expect(api.post).toHaveBeenCalledWith('/admin/administrators', {
      username: 'policy.admin',
      display_name: 'Policy Administrator',
      password: 'SecondAdministrator!2026',
      operator_password: 'CurrentAdministrator!2026',
      reason: 'approved provisioning',
    })
  })

  it('supports administrator management and managed application contracts', async () => {
    const administrator = {
      administrator_uuid: '66666666-6666-4666-8666-666666666666',
      username: 'policy.admin',
      display_name: 'Policy Administrator',
      permissions: ['administrator.manage'],
      status: 'active',
      created_at: '2026-09-11T10:00:00Z',
      password_changed_at: '2026-09-11T10:00:00Z',
      disabled_at: null,
    }
    const application = {
      application_uuid: '77777777-7777-4777-8777-777777777777',
      display_name: 'Learning app',
      package_name: 'org.example.learning',
      signing_certificate_sha256: null,
      category: 'education',
      education_approved: true,
      mandatory_block: false,
      status: 'enabled' as const,
      created_at: '2026-09-11T10:00:00Z',
      updated_at: '2026-09-11T10:00:00Z',
    }
    vi.mocked(api.get)
      .mockResolvedValueOnce({ data: { administrators: [administrator], pagination } })
      .mockResolvedValueOnce({ data: { administrator } })
      .mockResolvedValueOnce({ data: { applications: [application] } })
    vi.mocked(api.patch).mockResolvedValueOnce({ data: { administrator_uuid: administrator.administrator_uuid, message: 'permissions updated' } })
      .mockResolvedValueOnce({ data: { application } })
    vi.mocked(api.post)
      .mockResolvedValueOnce({ data: { administrator_uuid: administrator.administrator_uuid, revoked_sessions: 1, message: 'sessions revoked' } })
      .mockResolvedValueOnce({ data: { administrator_uuid: administrator.administrator_uuid, message: 'administrator disabled' } })
      .mockResolvedValueOnce({ data: { administrator_uuid: administrator.administrator_uuid, message: 'password reset' } })
      .mockResolvedValueOnce({ data: { application } })

    await expect(adminService.listAdministrators({ page: 1, perPage: 25 })).resolves.toMatchObject({ administrators: [administrator] })
    await expect(adminService.getAdministrator(administrator.administrator_uuid)).resolves.toEqual(administrator)
    await expect(adminService.replaceAdministratorPermissions(administrator.administrator_uuid, ['administrator.manage'], 'operator', 'reviewed')).resolves.toMatchObject({ message: 'permissions updated' })
    await expect(adminService.revokeAdministratorSessions(administrator.administrator_uuid, 'operator', 'reviewed')).resolves.toMatchObject({ revoked_sessions: 1 })
    await expect(adminService.disableAdministrator(administrator.administrator_uuid, 'operator', 'reviewed')).resolves.toMatchObject({ message: 'administrator disabled' })
    await expect(adminService.resetAdministratorPassword(administrator.administrator_uuid, 'NewPassword!2026', 'operator', 'reviewed')).resolves.toMatchObject({ message: 'password reset' })
    await expect(adminService.listManagedApplications()).resolves.toEqual([application])
    await expect(adminService.createManagedApplication(application)).resolves.toEqual(application)
    await expect(adminService.updateManagedApplication(application.application_uuid, application)).resolves.toEqual(application)

    expect(api.patch).toHaveBeenNthCalledWith(1, `/admin/administrators/${administrator.administrator_uuid}/permissions`, { permissions: ['administrator.manage'], operator_password: 'operator', reason: 'reviewed' })
    expect(api.patch).toHaveBeenNthCalledWith(2, `/admin/applications/${application.application_uuid}`, application)
  })

  it('encodes untrusted route parameters', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: { device } })
    await adminService.getDevice('../value')
    expect(api.get).toHaveBeenCalledWith('/admin/devices/..%2Fvalue', expect.anything())
  })

  it('supports omitted filters and cancellation signals', async () => {
    const signal = new AbortController().signal
    vi.mocked(api.get).mockResolvedValueOnce({ data: { devices: [device], pagination } })
    await expect(adminService.listDevices({ page: 1, perPage: 25 }, undefined, signal)).resolves.toMatchObject({ devices: [device] })
    expect(api.get).toHaveBeenCalledWith('/admin/devices', { params: { page: 1, per_page: 25 }, signal })
  })

  it('supports DPC dashboard, override and evidence reads', async () => {
    const override = { version: 1, status: 'active', reason: 'focus time', issued_at: '2026-09-11T10:00:00Z', cleared_at: null }
    const summary = { managed_devices: 2, active_block_overrides: 1, active_v3_assignments: 2, enforcement_failures: 0 }
    const evidence = { kind: 'policy_application', occurred_at: null, operation: 'apply', outcome: 'success' }
    vi.mocked(api.get)
      .mockResolvedValueOnce({ data: { summary } })
      .mockResolvedValueOnce({ data: { override } })
      .mockResolvedValueOnce({ data: { evidence: [evidence], pagination } })

    await expect(adminService.getDpcSummary()).resolves.toEqual(summary)
    await expect(adminService.getBlockOverride(deviceUuid)).resolves.toEqual(override)
    await expect(adminService.listDpcEvidence(deviceUuid, { page: 1, perPage: 25 })).resolves.toMatchObject({ evidence: [evidence] })
  })

  it('supports DPC override mutations and policy lifecycle mutations', async () => {
    const override = { version: 1, status: 'active', reason: 'focus time', issued_at: '2026-09-11T10:00:00Z', cleared_at: null }
    vi.mocked(api.post)
      .mockResolvedValueOnce({ data: { override } })
      .mockResolvedValueOnce({ data: { override: null } })
      .mockResolvedValueOnce({ data: { policy_uuid: policyUuid, status: 'draft' } })
      .mockResolvedValueOnce({ data: { revision_uuid: revisionUuid, version: 2 } })
      .mockResolvedValueOnce({ data: { policy_uuid: policyUuid, status: 'active' } })

    await expect(adminService.setBlockOverride(deviceUuid, 'temporary exception')).resolves.toEqual(override)
    await expect(adminService.clearBlockOverride(deviceUuid, 'exception ended')).resolves.toBeNull()
    await expect(adminService.createPolicy('School day', { blocked_packages: [] })).resolves.toEqual({ policy_uuid: policyUuid, status: 'draft' })
    await expect(adminService.createPolicyRevision(policyUuid, { blocked_packages: [] })).resolves.toEqual({ revision_uuid: revisionUuid, version: 2 })
    await expect(adminService.setPolicyLifecycle(policyUuid, 'active', 'approved')).resolves.toEqual({ policy_uuid: policyUuid, status: 'active' })

    expect(api.post).toHaveBeenNthCalledWith(1, `/admin/devices/${deviceUuid}/block-overrides`, { reason: 'temporary exception' })
    expect(api.post).toHaveBeenNthCalledWith(2, `/admin/devices/${deviceUuid}/block-overrides/clear`, { reason: 'exception ended' })
    expect(api.post).toHaveBeenNthCalledWith(4, `/admin/policies/${policyUuid}/revisions`, { payload: { blocked_packages: [] } })
    expect(api.post).toHaveBeenNthCalledWith(5, `/admin/policies/${policyUuid}/lifecycle`, { status: 'active', reason: 'approved' })
  })

  it('uses the authenticated approved-dynamic translation route', async () => {
    const translation = { translated_text: 'Oli otya?', source_language: 'eng', target_language: 'lug', cached: false, content_class: 'approved_dynamic', quality_status: 'machine' as const }
    vi.mocked(api.post).mockResolvedValueOnce({ data: translation })

    await expect(adminService.translateApprovedDynamicContent('Hello', 'lug')).resolves.toEqual(translation)
    expect(api.post).toHaveBeenCalledWith('/admin/translation/translate', {
      text: 'Hello',
      target_language: 'lug',
      source_language: 'eng',
      content_class: 'approved_dynamic',
    })
  })

  it('covers asset, location, incident, report, school, and domain contracts', async () => {
    const assignment = { assignment_uuid: '88888888-8888-4888-8888-888888888888', target_type: 'class', target_name: 'P6', responsible_officer: 'Teacher', assigned_at: '2026-09-11T10:00:00Z', expected_return_date: null, returned_at: null, issue_condition: 'Good', return_condition: null }
    const incident = { incident_uuid: '99999999-9999-4999-8999-999999999999', incident_number: 'INC-1', device_uuid: null, asset_number: null, incident_type: 'damage', description: 'Screen damage', reported_by: 'Teacher', reported_at: null, status: 'OPEN' as const, action_taken: null, responsible_person: null, closed_at: null, created_by: null, updated_at: null }
    const school = { school_uuid: '77777777-7777-4777-8777-777777777777', name: 'Demo school', district: 'Central', school_type: 'primary', contact_person: 'Head teacher', official_telephone: '+256700000000', official_email: null, physical_location: 'Kampala', authorised_administrator_name: 'Administrator', timezone: 'Africa/Kampala', created_at: null }
    const domain = { domain_uuid: '88888888-8888-4888-8888-888888888888', domain: 'learning.example', category: 'education', status: 'enabled' as const, created_at: '2026-09-11T10:00:00Z', updated_at: '2026-09-11T10:00:00Z' }
    const policyChange = { event_uuid: eventUuid, policy_name: 'School day', previous_policy_name: null, previous_version: null, new_version: 1, administrator: 'admin', occurred_at: null, device_uuid: null, asset_number: null, devices_affected: 1, reason: 'approved', operation: 'assign', result: 'success' }
    const violation = { event_uuid: eventUuid, device_uuid: deviceUuid, asset_number: null, class_name: 'P6', event_code: 'APP_BLOCKED', violation_type: 'application', outcome: 'blocked', rule_id: null, details: { package: 'org.example.game' }, policy_uuid: policyUuid, policy_name: 'School day', policy_version: 1, occurred_at: null, received_at: null, sequence: 1, event_hash: 'hash', previous_event_hash: null }
    vi.mocked(api.post)
      .mockResolvedValueOnce({ data: { device_uuid: deviceUuid } })
      .mockResolvedValueOnce({ data: { device_uuid: deviceUuid, message: 'purged' } })
      .mockResolvedValueOnce({ data: { assignment } })
      .mockResolvedValueOnce({ data: { incident } })
      .mockResolvedValueOnce({ data: { school } })
      .mockResolvedValueOnce({ data: { domain } })
    vi.mocked(api.patch)
      .mockResolvedValueOnce({ data: { device_uuid: deviceUuid, message: 'corrected' } })
      .mockResolvedValueOnce({ data: { assignment } })
      .mockResolvedValueOnce({ data: { incident } })
      .mockResolvedValueOnce({ data: { school } })
      .mockResolvedValueOnce({ data: { domain } })
    vi.mocked(api.get)
      .mockResolvedValueOnce({ data: { assignments: [assignment] } })
      .mockResolvedValueOnce({ data: { incidents: [incident], pagination } })
      .mockResolvedValueOnce({ data: { incidents: [incident], pagination } })
      .mockResolvedValueOnce({ data: { policy_changes: [policyChange], pagination } })
      .mockResolvedValueOnce({ data: { violations: [violation], pagination } })
      .mockResolvedValueOnce({ data: new Blob(['csv']) })
      .mockResolvedValueOnce({ data: { school } })
      .mockResolvedValueOnce({ data: { domains: [domain] } })

    await expect(adminService.registerSchoolDevice({ asset_number: 'EDU-1' })).resolves.toEqual({ device_uuid: deviceUuid })
    await expect(adminService.correctSchoolDeviceAsset(deviceUuid, { asset_notes: 'updated' })).resolves.toMatchObject({ message: 'corrected' })
    await expect(adminService.purgeRetiredDeviceData(deviceUuid, 'retired')).resolves.toMatchObject({ message: 'purged' })
    await expect(adminService.listDeviceLocationAssignments(deviceUuid)).resolves.toEqual({ assignments: [assignment] })
    await expect(adminService.createDeviceLocationAssignment(deviceUuid, { target_type: 'class', target_name: 'P6' })).resolves.toEqual({ assignment })
    await expect(adminService.correctDeviceLocationAssignment(deviceUuid, assignment.assignment_uuid, { return_condition: 'Good' })).resolves.toEqual({ assignment })
    await expect(adminService.listIncidents({ page: 1, perPage: 25 }, 'OPEN')).resolves.toMatchObject({ incidents: [incident] })
    await expect(adminService.listDeviceIncidents(deviceUuid, { page: 1, perPage: 25 })).resolves.toMatchObject({ incidents: [incident] })
    await expect(adminService.createIncident({ device_uuid: null, incident_type: 'damage', description: 'Screen damage', reported_by: 'Teacher', responsible_person: null })).resolves.toEqual(incident)
    await expect(adminService.updateIncident(incident.incident_uuid, { status: 'CLOSED', action_taken: 'Repaired', responsible_person: null })).resolves.toEqual(incident)
    await expect(adminService.listPolicyChanges({ page: 1, perPage: 25 })).resolves.toMatchObject({ policy_changes: [policyChange] })
    await expect(adminService.listViolationReports({ page: 1, perPage: 25 }, { deviceUuid, className: 'P6', from: '2026-09-01', to: '2026-09-30' })).resolves.toMatchObject({ violations: [violation] })
    await expect(adminService.exportViolationReport({ deviceUuid })).resolves.toBeInstanceOf(Blob)
    await expect(adminService.getSchool()).resolves.toEqual(school)
    await expect(adminService.registerSchool(school)).resolves.toEqual(school)
    await expect(adminService.updateSchool(school)).resolves.toEqual(school)
    await expect(adminService.listManagedDomains()).resolves.toEqual([domain])
    await expect(adminService.createManagedDomain({ domain: domain.domain, category: domain.category, status: domain.status })).resolves.toEqual(domain)
    await expect(adminService.updateManagedDomain(domain.domain_uuid, { domain: domain.domain, category: domain.category, status: domain.status })).resolves.toEqual(domain)
  })

  it('queues offline mutations and preserves non-network errors', async () => {
    const offline = new AppError('network_unavailable', 'offline')
    vi.mocked(api.post).mockRejectedValue(offline)
    await expect(adminService.createDeviceLocationAssignment(deviceUuid, { target_type: 'class', target_name: 'P6' })).resolves.toMatchObject({ sync_state: 'PENDING_SYNC' })
    await expect(adminService.assignPolicy(deviceUuid, revisionUuid, 'offline')).resolves.toMatchObject({ assignment: { status: 'PENDING_SYNC' } })
    await expect(adminService.clearPolicy(deviceUuid, 'offline')).resolves.toMatchObject({ clear_intent: { operation: 'clear' } })
    await expect(adminService.createPolicy('Offline policy', { blocked_packages: [] })).resolves.toMatchObject({ status: 'draft', sync_state: 'LOCAL_ONLY' })
    await expect(adminService.createPolicyRevision(policyUuid, { blocked_packages: [] })).resolves.toMatchObject({ version: 1, sync_state: 'LOCAL_ONLY' })
    await expect(adminService.setPolicyLifecycle(policyUuid, 'active', 'offline')).resolves.toMatchObject({ status: 'active', sync_state: 'PENDING_SYNC' })

    vi.mocked(api.post).mockRejectedValue(new AppError('validation_failed', 'invalid'))
    await expect(adminService.assignPolicy(deviceUuid, revisionUuid, 'invalid')).rejects.toMatchObject({ code: 'validation_failed' })
  })
})
