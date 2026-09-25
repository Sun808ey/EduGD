import api from '@/services/api'
import {
  assignmentMutationSchema, auditEventsSchema, clearMutationSchema,
  administratorCreateSchema,
  currentAssignmentSchema, deviceDetailSchema, devicesSchema,
  enrollmentTokensSchema, issuedEnrollmentTokenSchema, messageSchema,
  policiesSchema, policyDetailSchema, revisionsSchema, blockOverrideResponseSchema,
  dpcEvidenceResponseSchema, dpcSummarySchema, policyCreateSchema,
  managedApplicationsSchema, managedApplicationSchema,
  translationResultSchema,
} from '@/schemas/api'
import type { PageRequest, Policy } from '@/types/api.types'

const path = (value: string) => encodeURIComponent(value)
const pageParams = ({ page, perPage }: PageRequest) => ({ page, per_page: perPage })

export const adminService = {
  async createAdministrator(username: string, displayName: string, password: string, operatorPassword: string, reason: string) {
    const response = await api.post('/admin/administrators', { username, display_name: displayName, password, operator_password: operatorPassword, reason })
    return administratorCreateSchema.parse(response.data)
  },
  async listDevices(request: PageRequest, status?: string, signal?: AbortSignal) {
    const response = await api.get('/admin/devices', { params: { ...pageParams(request), ...(status ? { status } : {}) }, signal })
    return devicesSchema.parse(response.data)
  },
  async getDevice(uuid: string, signal?: AbortSignal) {
    const response = await api.get(`/admin/devices/${path(uuid)}`, { signal })
    return deviceDetailSchema.parse(response.data).device
  },
  async getCurrentAssignment(uuid: string, signal?: AbortSignal) {
    const response = await api.get(`/admin/devices/${path(uuid)}/policy-assignment`, { signal })
    return currentAssignmentSchema.parse(response.data).policy_assignment
  },
  async listPolicies(request: PageRequest, status?: string, signal?: AbortSignal) {
    const response = await api.get('/admin/policies', { params: { ...pageParams(request), ...(status ? { status } : {}) }, signal })
    return policiesSchema.parse(response.data)
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
    const response = await api.get(`/admin/policies/${path(uuid)}`, { signal })
    return policyDetailSchema.parse(response.data).policy
  },
  async listPolicyRevisions(uuid: string, request: PageRequest, signal?: AbortSignal) {
    const response = await api.get(`/admin/policies/${path(uuid)}/revisions`, { params: pageParams(request), signal })
    return revisionsSchema.parse(response.data)
  },
  async listEnrollmentTokens(request: PageRequest, status?: string, signal?: AbortSignal) {
    const response = await api.get('/admin/enrollment-tokens', { params: { ...pageParams(request), ...(status ? { status } : {}) }, signal })
    return enrollmentTokensSchema.parse(response.data)
  },
  async issueEnrollmentToken(reason: string, boundDeviceUuid?: string) {
    const response = await api.post('/admin/enrollment-tokens', { reason, bound_device_uuid: boundDeviceUuid || null })
    return issuedEnrollmentTokenSchema.parse(response.data)
  },
  async revokeEnrollmentToken(uuid: string, reason: string) {
    const response = await api.post(`/admin/enrollment-tokens/${path(uuid)}/revoke`, { reason })
    return messageSchema.parse(response.data)
  },
  async assignPolicy(deviceUuid: string, revisionUuid: string, reason: string) {
    const response = await api.post(`/admin/devices/${path(deviceUuid)}/policy-assignment`, { policy_revision_uuid: revisionUuid, reason })
    return assignmentMutationSchema.parse(response.data)
  },
  async clearPolicy(deviceUuid: string, reason: string) {
    const response = await api.post(`/admin/devices/${path(deviceUuid)}/policy-assignment/clear`, { reason })
    return clearMutationSchema.parse(response.data)
  },
  async revokeDeviceCredential(deviceUuid: string, reason: string) {
    const response = await api.post(`/admin/devices/${path(deviceUuid)}/credentials/revoke`, { reason })
    return messageSchema.parse(response.data)
  },
  async listAuditEvents(request: PageRequest, eventType?: string, signal?: AbortSignal) {
    const response = await api.get('/admin/audit-events', { params: { ...pageParams(request), ...(eventType ? { event_type: eventType } : {}) }, signal })
    return auditEventsSchema.parse(response.data)
  },
  async getDpcSummary(signal?: AbortSignal) {
    const response = await api.get('/admin/dashboard/dpc-summary', { signal })
    return dpcSummarySchema.parse(response.data).summary
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
    const response = await api.post('/admin/policies', { name, payload })
    return policyCreateSchema.parse(response.data)
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
  async translateApprovedDynamicContent(text: string, targetLanguage: import('@/types/api.types').SupportedLanguage, sourceLanguage: import('@/types/api.types').SupportedLanguage | null = 'eng') {
    const response = await api.post('/admin/translation/translate', { text, target_language: targetLanguage, source_language: sourceLanguage, content_class: 'approved_dynamic' })
    return translationResultSchema.parse(response.data)
  },
  async createPolicyRevision(policyUuid: string, payload: Record<string, unknown>) {
    return api.post(`/admin/policies/${path(policyUuid)}/revisions`, { payload })
  },
  async setPolicyLifecycle(policyUuid: string, status: 'active' | 'inactive' | 'revoked', reason: string) {
    return api.post(`/admin/policies/${path(policyUuid)}/lifecycle`, { status, reason })
  },
}
