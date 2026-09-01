import api from '@/services/api'
import type {
  AuditEventSummary,
  DeviceSummary,
  PaginatedResponse,
  PolicySummary,
  EnrollmentTokenResponse,
  PolicyAssignmentResponse,
  PolicyClearResponse,
  EnrollmentTokenSummary,
  PolicyDetail,
  PolicyRevisionSummary,
  DeviceDetail,
} from '@/types/api'

interface DeviceListResponse {
  devices: DeviceSummary[]
  pagination: PaginatedResponse<DeviceSummary>['pagination']
}

interface PolicyListResponse {
  policies: PolicySummary[]
  pagination: PaginatedResponse<PolicySummary>['pagination']
}

interface AuditEventListResponse {
  audit_events: AuditEventSummary[]
  pagination: PaginatedResponse<AuditEventSummary>['pagination']
}

interface EnrollmentTokenListResponse {
  enrollment_tokens: EnrollmentTokenSummary[]
  pagination: PaginatedResponse<EnrollmentTokenSummary>['pagination']
}

interface PolicyDetailResponse {
  policy: PolicyDetail
}

interface PolicyRevisionListResponse {
  revisions: PolicyRevisionSummary[]
  pagination: PaginatedResponse<PolicyRevisionSummary>['pagination']
}

interface DeviceDetailResponse {
  device: DeviceDetail
}

export const adminService = {
  async listDevices() {
    const { data } = await api.get<DeviceListResponse>('/admin/devices', {
      params: { page: 1, per_page: 100 },
    })
    return data
  },

  async getDevice(deviceUuid: string) {
    const { data } = await api.get<DeviceDetailResponse>(`/admin/devices/${deviceUuid}`)
    return data.device
  },

  async listPolicies() {
    const { data } = await api.get<PolicyListResponse>('/admin/policies', {
      params: { page: 1, per_page: 100 },
    })
    return data
  },

  async getPolicy(policyUuid: string) {
    const { data } = await api.get<PolicyDetailResponse>(`/admin/policies/${policyUuid}`)
    return data.policy
  },

  async listPolicyRevisions(policyUuid: string) {
    const { data } = await api.get<PolicyRevisionListResponse>(`/admin/policies/${policyUuid}/revisions`, { params: { page: 1, per_page: 100 } })
    return data
  },

  async listAuditEvents(eventType?: string) {
    const { data } = await api.get<AuditEventListResponse>('/admin/audit-events', {
      params: { page: 1, per_page: 25, ...(eventType && eventType !== 'all' ? { event_type: eventType } : {}) },
    })
    return data
  },

  async issueEnrollmentToken(reason: string, boundDeviceUuid?: string) {
    const { data } = await api.post<EnrollmentTokenResponse>('/admin/enrollment-tokens', {
      reason,
      bound_device_uuid: boundDeviceUuid || null,
    })
    return data
  },

  async listEnrollmentTokens() {
    const { data } = await api.get<EnrollmentTokenListResponse>('/admin/enrollment-tokens', {
      params: { page: 1, per_page: 25 },
    })
    return data
  },

  async revokeEnrollmentToken(tokenUuid: string, reason: string) {
    await api.post(`/admin/enrollment-tokens/${tokenUuid}/revoke`, { reason })
  },

  async assignPolicy(deviceUuid: string, policyRevisionUuid: string, reason: string) {
    const { data } = await api.post<PolicyAssignmentResponse>(`/admin/devices/${deviceUuid}/policy-assignment`, {
      policy_revision_uuid: policyRevisionUuid,
      reason,
    })
    return data
  },

  async clearPolicy(deviceUuid: string, reason: string) {
    const { data } = await api.post<PolicyClearResponse>(`/admin/devices/${deviceUuid}/policy-assignment/clear`, { reason })
    return data
  },
}