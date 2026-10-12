import api from '@/services/api'
import {
  assignmentMutationSchema, auditEventsSchema, clearMutationSchema,
  administratorCreateSchema,
  administratorDetailSchema, administratorsSchema, administratorMutationSchema,
  currentAssignmentSchema, deviceDetailSchema, devicesSchema,
  enrollmentTokensSchema, issuedEnrollmentTokenSchema, messageSchema,
  policiesSchema, policyDetailSchema, revisionsSchema, blockOverrideResponseSchema,
  dpcEvidenceResponseSchema, dpcSummarySchema, policyCreateSchema,
  managedApplicationsSchema, managedApplicationSchema, managedDomainsSchema, managedDomainSchema, schoolResponseSchema,
  policyLifecycleSchema, policyRevisionMutationSchema, translationResultSchema,
  incidentsSchema, incidentResponseSchema, policyChangesSchema,
  violationReportsSchema,
} from '@/schemas/api'
import type { PageRequest, Policy } from '@/types/api.types'
import { normalizeApiError } from '@/services/errors'
import { createOfflineUuid, enqueueOfflineMutation, listOfflineQueue, readOfflineCache, writeOfflineCache } from '@/services/offlineStore'

const path = (value: string) => encodeURIComponent(value)
const pageParams = ({ page, perPage }: PageRequest) => ({ page, per_page: perPage })
const isOfflineFailure = (error: unknown) => {
  const code = normalizeApiError(error).code
  return (typeof navigator !== 'undefined' && navigator.onLine === false) || code === 'network_unavailable' || code === 'request_timeout'
}
async function cached<T>(key: string, request: () => Promise<T>): Promise<T> {
  try { const value = await request(); await writeOfflineCache(key, value); return value } catch (error) {
    const value = await readOfflineCache<T>(key)
    if (value !== null) return value
    throw error
  }
}
const pendingDeviceState = async (device: import('@/types/api.types').Device) => {
  const queue = await listOfflineQueue()
  const latest = queue.filter((item) => item.payload.device_uuid === device.device_uuid).sort((a, b) => a.updatedAt.localeCompare(b.updatedAt)).at(-1)
  return latest ? { ...device, sync_state: latest.state } : device
}

export const adminService = {
  async createAdministrator(username: string, displayName: string, password: string, operatorPassword: string, reason: string) {
    const response = await api.post('/admin/administrators', { username, display_name: displayName, password, operator_password: operatorPassword, reason })
    return administratorCreateSchema.parse(response.data)
  },
  async listAdministrators(request: PageRequest, signal?: AbortSignal) {
    const response = await api.get('/admin/administrators', { params: pageParams(request), signal })
    return administratorsSchema.parse(response.data)
  },
  async getAdministrator(uuid: string, signal?: AbortSignal) {
    const response = await api.get(`/admin/administrators/${path(uuid)}`, { signal })
    return administratorDetailSchema.parse(response.data).administrator
  },
  async replaceAdministratorPermissions(uuid: string, permissions: import('@/types/api.types').AdministratorPermission[], operatorPassword: string, reason: string) {
    const response = await api.patch(`/admin/administrators/${path(uuid)}/permissions`, { permissions, operator_password: operatorPassword, reason })
    return administratorMutationSchema.parse(response.data)
  },
  async revokeAdministratorSessions(uuid: string, operatorPassword: string, reason: string) {
    const response = await api.post(`/admin/administrators/${path(uuid)}/sessions/revoke`, { operator_password: operatorPassword, reason })
    return administratorMutationSchema.parse(response.data)
  },
  async disableAdministrator(uuid: string, operatorPassword: string, reason: string) {
    const response = await api.post(`/admin/administrators/${path(uuid)}/disable`, { operator_password: operatorPassword, reason })
    return administratorMutationSchema.parse(response.data)
  },
  async resetAdministratorPassword(uuid: string, password: string, operatorPassword: string, reason: string) {
    const response = await api.post(`/admin/administrators/${path(uuid)}/password/reset`, { password, operator_password: operatorPassword, reason })
    return administratorMutationSchema.parse(response.data)
  },
  async listDevices(request: PageRequest, status?: string, signal?: AbortSignal) {
    const key = `devices.${status ?? 'all'}.${request.page}.${request.perPage}`
    const result = await cached(key, async () => {
      const response = await api.get('/admin/devices', { params: { ...pageParams(request), ...(status ? { status } : {}) }, signal })
      return devicesSchema.parse(response.data)
    })
    return { ...result, devices: await Promise.all(result.devices.map(pendingDeviceState)) }
  },
  async registerSchoolDevice(payload: Record<string, unknown>) {
    const response = await api.post('/admin/devices/assets', payload)
    return response.data as { device_uuid: string }
  },
  async correctSchoolDeviceAsset(deviceUuid: string, payload: Record<string, unknown>) {
    const response = await api.patch(`/admin/devices/${path(deviceUuid)}/asset`, payload)
    return response.data as { device_uuid: string; message: string }
  },
  async purgeRetiredDeviceData(deviceUuid: string, reason: string) {
    const response = await api.post(`/admin/devices/${path(deviceUuid)}/data-retention/purge`, { reason })
    return response.data as { device_uuid: string; message: string }
  },
  async listDeviceLocationAssignments(deviceUuid: string) {
    return cached(`location-assignments.${deviceUuid}`, async () => {
      const response = await api.get(`/admin/devices/${path(deviceUuid)}/location-assignments`)
      return response.data as { assignments: import('@/types/api.types').DeviceLocationAssignment[] }
    })
  },
  async createDeviceLocationAssignment(deviceUuid: string, payload: Record<string, unknown>) {
    try {
      const response = await api.post(`/admin/devices/${path(deviceUuid)}/location-assignments`, payload)
      return response.data as { assignment: import('@/types/api.types').DeviceLocationAssignment }
    } catch (error) {
      if (!isOfflineFailure(error)) throw error
      await enqueueOfflineMutation({ kind: 'location_assignment', method: 'POST', url: `/admin/devices/${path(deviceUuid)}/location-assignments`, payload: { ...payload, device_uuid: deviceUuid }, state: 'PENDING_SYNC' })
      const assignment = { assignment_uuid: createOfflineUuid(), target_type: payload.target_type as 'class' | 'department', target_name: String(payload.target_name ?? ''), responsible_officer: String(payload.responsible_officer ?? ''), assigned_at: new Date().toISOString(), expected_return_date: (payload.expected_return_date as string | null) ?? null, returned_at: null, issue_condition: String(payload.issue_condition ?? ''), return_condition: null }
      const cachedHistory = await readOfflineCache<{ assignments: import('@/types/api.types').DeviceLocationAssignment[] }>(`location-assignments.${deviceUuid}`)
      await writeOfflineCache(`location-assignments.${deviceUuid}`, { assignments: [...(cachedHistory?.assignments ?? []), assignment] })
      return { assignment, sync_state: 'PENDING_SYNC' }
    }
  },
  async correctDeviceLocationAssignment(deviceUuid: string, assignmentUuid: string, payload: Record<string, unknown>) {
    const response = await api.patch(`/admin/devices/${path(deviceUuid)}/location-assignments/${path(assignmentUuid)}`, payload)
    return response.data as { assignment: import('@/types/api.types').DeviceLocationAssignment }
  },
  async getDevice(uuid: string, signal?: AbortSignal) {
    return cached(`device.${uuid}`, async () => {
      const response = await api.get(`/admin/devices/${path(uuid)}`, { signal })
      return deviceDetailSchema.parse(response.data).device
    }).then(pendingDeviceState)
  },
  async getCurrentAssignment(uuid: string, signal?: AbortSignal) {
    return cached(`assignment.${uuid}`, async () => {
      const response = await api.get(`/admin/devices/${path(uuid)}/policy-assignment`, { signal })
      return currentAssignmentSchema.parse(response.data).policy_assignment
    })
  },
  async listPolicies(request: PageRequest, status?: string, signal?: AbortSignal) {
    const key = `policies.${status ?? 'all'}.${request.page}.${request.perPage}`
    return cached(key, async () => {
      const response = await api.get('/admin/policies', { params: { ...pageParams(request), ...(status ? { status } : {}) }, signal })
      return policiesSchema.parse(response.data)
    })
  },
  async listAllPolicies(signal?: AbortSignal) {
    const policies: Policy[] = []
    let page = 1
    while (true) {
      const result = await adminService.listPolicies({ page, perPage: 100 }, 'active', signal)
      policies.push(...result.policies)
      if (!result.pagination.has_next) return policies
      page += 1
    }
  },
  async getPolicy(uuid: string, signal?: AbortSignal) {
    return cached(`policy.${uuid}`, async () => {
      const response = await api.get(`/admin/policies/${path(uuid)}`, { signal })
      return policyDetailSchema.parse(response.data).policy
    })
  },
  async listPolicyRevisions(uuid: string, request: PageRequest, signal?: AbortSignal) {
    return cached(`revisions.${uuid}.${request.page}.${request.perPage}`, async () => {
      const response = await api.get(`/admin/policies/${path(uuid)}/revisions`, { params: pageParams(request), signal })
      return revisionsSchema.parse(response.data)
    })
  },
  async listEnrollmentTokens(request: PageRequest, status?: string, signal?: AbortSignal) {
    const response = await api.get('/admin/enrollment-tokens', { params: { ...pageParams(request), ...(status ? { status } : {}) }, signal })
    return enrollmentTokensSchema.parse(response.data)
  },
  async issueEnrollmentToken(payload: { reason: string; school_uuid: string; policy_revision_uuid: string; bound_device_uuid?: string }) {
    const response = await api.post('/admin/enrollment-tokens', { ...payload, bound_device_uuid: payload.bound_device_uuid || null })
    return issuedEnrollmentTokenSchema.parse(response.data)
  },
  async revokeEnrollmentToken(uuid: string, reason: string) {
    const response = await api.post(`/admin/enrollment-tokens/${path(uuid)}/revoke`, { reason })
    return messageSchema.parse(response.data)
  },
  async assignPolicy(deviceUuid: string, revisionUuid: string, reason: string) {
    const payload = { policy_revision_uuid: revisionUuid, reason }
    try {
      const response = await api.post(`/admin/devices/${path(deviceUuid)}/policy-assignment`, payload)
      return assignmentMutationSchema.parse(response.data)
    } catch (error) {
      if (!isOfflineFailure(error)) throw error
      await enqueueOfflineMutation({ kind: 'policy_assign', method: 'POST', url: `/admin/devices/${path(deviceUuid)}/policy-assignment`, payload: { ...payload, device_uuid: deviceUuid }, state: 'PENDING_SYNC' })
      return assignmentMutationSchema.parse({ assignment: { event_uuid: createOfflineUuid(), device_uuid: deviceUuid, policy_revision_uuid: revisionUuid, status: 'PENDING_SYNC', replaced: false } })
    }
  },
  async clearPolicy(deviceUuid: string, reason: string) {
    const payload = { reason }
    try {
      const response = await api.post(`/admin/devices/${path(deviceUuid)}/policy-assignment/clear`, payload)
      return clearMutationSchema.parse(response.data)
    } catch (error) {
      if (!isOfflineFailure(error)) throw error
      await enqueueOfflineMutation({ kind: 'policy_clear', method: 'POST', url: `/admin/devices/${path(deviceUuid)}/policy-assignment/clear`, payload: { ...payload, device_uuid: deviceUuid }, state: 'PENDING_SYNC' })
      return clearMutationSchema.parse({ clear_intent: { event_uuid: createOfflineUuid(), device_uuid: deviceUuid, operation: 'clear' } })
    }
  },
  async revokeDeviceCredential(deviceUuid: string, reason: string) {
    const response = await api.post(`/admin/devices/${path(deviceUuid)}/credentials/revoke`, { reason })
    return messageSchema.parse(response.data)
  },
  async listAuditEvents(request: PageRequest, eventType?: string, signal?: AbortSignal) {
    return cached(`audit.${eventType ?? 'all'}.${request.page}.${request.perPage}`, async () => {
      const response = await api.get('/admin/audit-events', { params: { ...pageParams(request), ...(eventType ? { event_type: eventType } : {}) }, signal })
      return auditEventsSchema.parse(response.data)
    })
  },
  async listIncidents(request: PageRequest, status?: string, signal?: AbortSignal) {
    const response = await api.get('/admin/incidents', { params: { ...pageParams(request), ...(status ? { status } : {}) }, signal })
    return incidentsSchema.parse(response.data)
  },
  async listDeviceIncidents(deviceUuid: string, request: PageRequest, signal?: AbortSignal) {
    const response = await api.get(`/admin/devices/${path(deviceUuid)}/incidents`, { params: pageParams(request), signal })
    return incidentsSchema.parse(response.data)
  },
  async createIncident(payload: { device_uuid: string | null; incident_type: string; description: string; reported_by: string; responsible_person: string | null }) {
    const response = await api.post('/admin/incidents', payload)
    return incidentResponseSchema.parse(response.data).incident
  },
  async updateIncident(uuid: string, payload: { status: import('@/types/api.types').IncidentStatus; action_taken: string | null; responsible_person: string | null }) {
    const response = await api.patch(`/admin/incidents/${path(uuid)}`, payload)
    return incidentResponseSchema.parse(response.data).incident
  },
  async listPolicyChanges(request: PageRequest, signal?: AbortSignal) {
    const response = await api.get('/admin/policy-changes', { params: pageParams(request), signal })
    return policyChangesSchema.parse(response.data)
  },
  async listViolationReports(request: PageRequest, filters: { deviceUuid?: string; className?: string; from?: string; to?: string } = {}, signal?: AbortSignal) {
    const response = await api.get('/admin/reports/violations', { params: { ...pageParams(request), ...(filters.deviceUuid ? { device_uuid: filters.deviceUuid } : {}), ...(filters.className ? { class_name: filters.className } : {}), ...(filters.from ? { from: filters.from } : {}), ...(filters.to ? { to: filters.to } : {}) }, signal })
    return violationReportsSchema.parse(response.data)
  },
  async exportViolationReport(filters: { deviceUuid?: string; className?: string; from?: string; to?: string } = {}) {
    const response = await api.get('/admin/reports/violations.csv', { params: { ...(filters.deviceUuid ? { device_uuid: filters.deviceUuid } : {}), ...(filters.className ? { class_name: filters.className } : {}), ...(filters.from ? { from: filters.from } : {}), ...(filters.to ? { to: filters.to } : {}) }, responseType: 'blob' })
    return response.data as Blob
  },
  async getDpcSummary(signal?: AbortSignal) {
    return cached('dpc-summary', async () => {
      const response = await api.get('/admin/dashboard/dpc-summary', { signal })
      return dpcSummarySchema.parse(response.data).summary
    })
  },
  async getSchool(signal?: AbortSignal) {
    const response = await api.get('/admin/school', { signal })
    return schoolResponseSchema.parse(response.data).school
  },
  async registerSchool(school: import('@/types/api.types').SchoolRegistration) {
    const response = await api.post('/admin/school', school)
    return schoolResponseSchema.parse(response.data).school
  },
  async updateSchool(school: import('@/types/api.types').SchoolRegistration) {
    const response = await api.patch('/admin/school', school)
    return schoolResponseSchema.parse(response.data).school
  },
  async getBlockOverride(deviceUuid: string, signal?: AbortSignal) {
    const response = await api.get(`/admin/devices/${path(deviceUuid)}/block-overrides`, { signal })
    return blockOverrideResponseSchema.parse(response.data).override
  },
  async setBlockOverride(deviceUuid: string, reason: string) {
    const response = await api.post(`/admin/devices/${path(deviceUuid)}/block-overrides`, { reason })
    return blockOverrideResponseSchema.parse(response.data).override
  },
  async clearBlockOverride(deviceUuid: string, reason: string) {
    const response = await api.post(`/admin/devices/${path(deviceUuid)}/block-overrides/clear`, { reason })
    return blockOverrideResponseSchema.parse(response.data).override
  },
  async listDpcEvidence(deviceUuid: string, request: PageRequest, signal?: AbortSignal) {
    const response = await api.get(`/admin/devices/${path(deviceUuid)}/control-evidence`, { params: pageParams(request), signal })
    return dpcEvidenceResponseSchema.parse(response.data)
  },
  async createPolicy(name: string, payload: Record<string, unknown>) {
    try {
      const response = await api.post('/admin/policies', { name, payload })
      return policyCreateSchema.parse(response.data)
    } catch (error) {
      if (!isOfflineFailure(error)) throw error
      const policyUuid = createOfflineUuid()
      await enqueueOfflineMutation({ kind: 'policy_create', method: 'POST', url: '/admin/policies', payload: { name, payload }, state: 'LOCAL_ONLY' })
      const revisionUuid = createOfflineUuid()
      const localPolicy = { policy_uuid: policyUuid, name, status: 'draft' as const, created_at: new Date().toISOString(), updated_at: new Date().toISOString(), latest_revision: { revision_uuid: revisionUuid, version: 1, payload, content_hash: 'LOCAL_ONLY', created_at: new Date().toISOString(), created_by: null, sync_state: 'LOCAL_ONLY' as const }, revision_count: 1, sync_state: 'LOCAL_ONLY' as const }
      await writeOfflineCache(`policy.${policyUuid}`, localPolicy)
      const cachedPolicies = await readOfflineCache<{ policies: typeof localPolicy[]; pagination: { page: number; per_page: number; total: number; has_next: boolean } }>('policies.all.1.25')
      await writeOfflineCache('policies.all.1.25', { policies: [localPolicy, ...(cachedPolicies?.policies ?? [])], pagination: cachedPolicies?.pagination ?? { page: 1, per_page: 25, total: 1, has_next: false } })
      return policyCreateSchema.parse({ policy_uuid: policyUuid, status: 'draft', sync_state: 'LOCAL_ONLY' })
    }
  },
  async listManagedApplications(signal?: AbortSignal) {
    const response = await api.get('/admin/applications', { signal })
    return managedApplicationsSchema.parse(response.data).applications
  },
  async createManagedApplication(application: Omit<import('@/types/api.types').ManagedApplication, 'application_uuid' | 'created_at' | 'updated_at'>) {
    const response = await api.post('/admin/applications', application)
    return managedApplicationSchema.parse(response.data.application)
  },
  async updateManagedApplication(uuid: string, application: Omit<import('@/types/api.types').ManagedApplication, 'application_uuid' | 'created_at' | 'updated_at'>) {
    const response = await api.patch(`/admin/applications/${path(uuid)}`, application)
    return managedApplicationSchema.parse(response.data.application)
  },
  async listManagedDomains(signal?: AbortSignal) {
    const response = await api.get('/admin/domains', { signal })
    return managedDomainsSchema.parse(response.data).domains
  },
  async createManagedDomain(domain: { domain: string; category: string; status: 'enabled' | 'disabled' }) {
    const response = await api.post('/admin/domains', domain)
    return managedDomainSchema.parse(response.data.domain)
  },
  async updateManagedDomain(uuid: string, domain: { domain: string; category: string; status: 'enabled' | 'disabled' }) {
    const response = await api.patch(`/admin/domains/${path(uuid)}`, domain)
    return managedDomainSchema.parse(response.data.domain)
  },
  async translateApprovedDynamicContent(text: string, targetLanguage: import('@/types/api.types').SupportedLanguage, sourceLanguage: import('@/types/api.types').SupportedLanguage | null = 'eng') {
    const response = await api.post('/admin/translation/translate', { text, target_language: targetLanguage, source_language: sourceLanguage, content_class: 'approved_dynamic' })
    return translationResultSchema.parse(response.data)
  },
  async createPolicyRevision(policyUuid: string, payload: Record<string, unknown>) {
    try {
      const response = await api.post(`/admin/policies/${path(policyUuid)}/revisions`, { payload })
      return policyRevisionMutationSchema.parse(response.data)
    } catch (error) {
      if (!isOfflineFailure(error)) throw error
      await enqueueOfflineMutation({ kind: 'policy_revision', method: 'POST', url: `/admin/policies/${path(policyUuid)}/revisions`, payload: { payload, policy_uuid: policyUuid }, state: 'LOCAL_ONLY' })
      return policyRevisionMutationSchema.parse({ revision_uuid: createOfflineUuid(), version: 1, sync_state: 'LOCAL_ONLY' })
    }
  },
  async setPolicyLifecycle(policyUuid: string, status: 'active' | 'inactive' | 'revoked', reason: string) {
    try {
      const response = await api.post(`/admin/policies/${path(policyUuid)}/lifecycle`, { status, reason })
      return policyLifecycleSchema.parse(response.data)
    } catch (error) {
      if (!isOfflineFailure(error)) throw error
      await enqueueOfflineMutation({ kind: 'policy_lifecycle', method: 'POST', url: `/admin/policies/${path(policyUuid)}/lifecycle`, payload: { status, reason, policy_uuid: policyUuid }, state: 'PENDING_SYNC' })
      return policyLifecycleSchema.parse({ policy_uuid: policyUuid, status, sync_state: 'PENDING_SYNC' })
    }
  },
}
