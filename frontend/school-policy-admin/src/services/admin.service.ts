import api from '@/services/api'
import {
  assignmentMutationSchema, auditEventsSchema, clearMutationSchema,
  currentAssignmentSchema, deviceDetailSchema, devicesSchema,
  enrollmentTokensSchema, issuedEnrollmentTokenSchema, messageSchema,
  policiesSchema, policyDetailSchema, revisionsSchema,
} from '@/schemas/api'
import type { PageRequest, Policy } from '@/types/api.types'

const path = (value: string) => encodeURIComponent(value)
const pageParams = ({ page, perPage }: PageRequest) => ({ page, per_page: perPage })

export const adminService = {
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
      const result = await this.listPolicies({ page, perPage: 100 }, 'active', signal)
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
}
