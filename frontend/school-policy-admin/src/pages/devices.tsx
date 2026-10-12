import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { adminService } from '@/services/admin.service'
import { useAuth } from '@/hooks/useAuth'
import { ActionDialog } from '@/components/ui/ActionDialog'
import { ErrorState, LoadingState } from '@/components/ui/AsyncState'
import { errorMessage } from '@/services/errors'
import { formatDate } from '@/lib/format'
import type { Device } from '@/types/api.types'

type ComplianceFilter = 'all' | 'compliant' | 'partially_compliant' | 'pending' | 'not_reported'
type ConnectionFilter = 'all' | 'review' | 'reported'
type ProvisioningFilter = 'all' | 'provisioning' | 'missing'
type EnrollmentFilter = 'all' | 'enrolled' | 'not_enrolled'

function compliance(device: Device): Exclude<ComplianceFilter, 'all'> {
  if (device.enrollment_state !== 'enrolled') return 'pending'
  if (device.enforcement_status === 'COMPLIANT') return 'compliant'
  if (device.enforcement_status === 'PARTIALLY_COMPLIANT') return 'partially_compliant'
  return 'not_reported'
}

function isOffline(device: Device) {
  if (device.connection_status) return device.connection_status === 'OFFLINE'
  if (!device.last_sync_at) return false
  return Date.now() - new Date(device.last_sync_at).getTime() > 24 * 60 * 60 * 1000
}

function lifecycleLabel(device: Device) {
  return device.asset_lifecycle_status ?? device.status
}

export function DevicesPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [department, setDepartment] = useState('')
  const [policyUuid, setPolicyUuid] = useState('')
  const [complianceFilter, setComplianceFilter] = useState<ComplianceFilter>('all')
  const [connectionFilter, setConnectionFilter] = useState<ConnectionFilter>('all')
  const [provisioningFilter, setProvisioningFilter] = useState<ProvisioningFilter>('all')
  const [enrollmentFilter, setEnrollmentFilter] = useState<EnrollmentFilter>('all')
  const [selected, setSelected] = useState<Device | null>(null)
  const [revision, setRevision] = useState('')
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const { hasPermission } = useAuth()
  const cache = useQueryClient()
  const devices = useQuery({ queryKey: ['devices', 'register'], queryFn: ({ signal }) => adminService.listDevices({ page: 1, perPage: 100 }, undefined, signal) })
  const policies = useQuery({ queryKey: ['policies', 'all'], queryFn: ({ signal }) => adminService.listAllPolicies(signal), enabled: Boolean(selected) })
  const mutation = useMutation({ mutationFn: async () => {
    if (!selected || !reason.trim()) throw new Error('A reason is required.')
    if (!revision && !selected.active_policy_assignment) throw new Error('Select a policy revision for this unassigned device.')
    return revision ? adminService.assignPolicy(selected.device_uuid, revision, reason.trim()) : adminService.clearPolicy(selected.device_uuid, reason.trim())
  }, onSuccess: async () => { setSelected(null); setReason(''); setRevision(''); await cache.invalidateQueries({ queryKey: ['devices'] }) }, onError: (caught) => setError(errorMessage(caught)) })
  const filtered = useMemo(() => {
    const term = search.trim().toLocaleLowerCase()
    return (devices.data?.devices ?? []).filter((device) => {
      const searchable = [device.asset_number, device.model, device.manufacturer, device.serial_number, device.department, device.device_uuid].filter(Boolean).join(' ').toLocaleLowerCase()
      const assignment = device.active_policy_assignment
      const matchesProvisioning = provisioningFilter === 'all' || (provisioningFilter === 'missing' ? device.asset_lifecycle_status === 'MISSING' : ['REGISTERED', 'READY_FOR_PROVISIONING', 'PROVISIONING', 'PROVISIONING_FAILED'].includes(device.asset_lifecycle_status ?? ''))
      return (!term || searchable.includes(term)) && (!department || device.department === department) && (!policyUuid || assignment?.policy_uuid === policyUuid) && (enrollmentFilter === 'all' || (enrollmentFilter === 'enrolled' ? device.enrollment_state === 'enrolled' : device.enrollment_state !== 'enrolled')) && (complianceFilter === 'all' || compliance(device) === complianceFilter) && (connectionFilter === 'all' || (connectionFilter === 'review' ? (device.connection_review ?? isOffline(device)) : Boolean(device.last_sync_at))) && matchesProvisioning
    })
  }, [devices.data, search, department, policyUuid, enrollmentFilter, complianceFilter, connectionFilter, provisioningFilter])
  const departments = [...new Set((devices.data?.devices ?? []).map((device) => device.department).filter((value): value is string => Boolean(value)))].sort()
  const listedPolicies = [...new Map((devices.data?.devices ?? []).flatMap((device) => device.active_policy_assignment ? [[device.active_policy_assignment.policy_uuid, device.active_policy_assignment.policy_name] as const] : [])).entries()]
  function open(device: Device) { setSelected(device); setRevision(device.active_policy_assignment?.policy_revision_uuid ?? ''); setReason(''); setError('') }
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); mutation.mutate() }

  return <section className="space-y-6"><header><h1 className="text-3xl font-semibold">School devices</h1><p className="mt-2 text-sm text-slate-600">Search devices reported by the Android DPC, filter by enrollment, and open an individual device for controls and evidence.</p><p className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-950">Device details are filled automatically during secure provisioning and subsequent DPC synchronisation. No manual device registration is required.</p></header>
    <section className="grid gap-3 rounded-2xl border bg-white p-4 md:grid-cols-2 xl:grid-cols-3"><label className="text-sm font-medium xl:col-span-2">Search asset, model, serial, department, or device ID<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="EDUGD-TAB-001 or Galaxy Tab A" className="mt-2 h-10 w-full rounded-lg border px-3" /></label><label className="text-sm font-medium">Enrollment<select value={enrollmentFilter} onChange={(event) => setEnrollmentFilter(event.target.value as EnrollmentFilter)} className="mt-2 h-10 w-full rounded-lg border bg-white px-3"><option value="all">All registered devices</option><option value="enrolled">Enrolled devices</option><option value="not_enrolled">Awaiting enrollment</option></select></label><label className="text-sm font-medium">Department<select value={department} onChange={(event) => setDepartment(event.target.value)} className="mt-2 h-10 w-full rounded-lg border bg-white px-3"><option value="">All departments</option>{departments.map((value) => <option key={value} value={value}>{value}</option>)}</select></label><label className="text-sm font-medium">Policy<select value={policyUuid} onChange={(event) => setPolicyUuid(event.target.value)} className="mt-2 h-10 w-full rounded-lg border bg-white px-3"><option value="">All policies</option>{listedPolicies.map(([uuid, name]) => <option key={uuid} value={uuid}>{name}</option>)}</select></label><label className="text-sm font-medium">Compliance<select value={complianceFilter} onChange={(event) => setComplianceFilter(event.target.value as ComplianceFilter)} className="mt-2 h-10 w-full rounded-lg border bg-white px-3"><option value="all">All results</option><option value="compliant">Compliant</option><option value="partially_compliant">Partially compliant</option><option value="pending">Pending enrollment</option><option value="not_reported">Not reported</option></select></label><label className="text-sm font-medium">Connection review<select value={connectionFilter} onChange={(event) => setConnectionFilter(event.target.value as ConnectionFilter)} className="input mt-2"><option value="all">All connection states</option><option value="review">Connection review due</option><option value="reported">Has sync time</option></select></label><label className="text-sm font-medium">Provisioning<select value={provisioningFilter} onChange={(event) => setProvisioningFilter(event.target.value as ProvisioningFilter)} className="mt-2 h-10 w-full rounded-lg border bg-white px-3"><option value="all">All lifecycle states</option><option value="provisioning">Provisioning</option><option value="missing">Missing</option></select></label></section>
    <p className="text-sm text-slate-500">Compliance is calculated from the latest device controls. Connection review is a separate operational follow-up; an offline device is not automatically non-compliant.</p>
    {devices.isLoading && <LoadingState label="Loading devices…" />}{devices.isError && <ErrorState message="Devices are temporarily unavailable." retry={() => void devices.refetch()} />}
     {devices.data && <div className="overflow-hidden rounded-2xl border bg-white"><div className="overflow-x-auto"><table className="w-full min-w-300 text-left text-sm"><thead className="bg-slate-50"><tr><th className="p-4">Asset number</th><th className="p-4">Model</th><th className="p-4">Department</th><th className="p-4">Policy</th><th className="p-4">Compliance</th><th className="p-4">Last synchronised</th><th className="p-4">Battery</th><th className="p-4">Status</th><th className="p-4">Actions</th></tr></thead><tbody className="divide-y">{filtered.map((device) => <tr key={device.device_uuid}><td className="p-4 font-medium"><Link className="text-emerald-700 underline" to={`/devices/${device.device_uuid}`}>{device.asset_number ?? device.device_uuid}</Link></td><td className="p-4">{[device.manufacturer, device.model].filter(Boolean).join(' ') || 'Not recorded'}</td><td className="p-4">{device.department ?? 'Not assigned'}</td><td className="p-4">{device.active_policy_assignment ? `${device.active_policy_assignment.policy_name} v${device.active_policy_assignment.policy_version}` : 'Unassigned'}</td><td className="p-4">{compliance(device).replaceAll('_', ' ')}</td><td className="p-4">{formatDate(device.last_sync_at)}</td><td className="p-4">Not reported</td><td className="p-4">{lifecycleLabel(device).replaceAll('_', ' ')}</td><td className="p-4 whitespace-nowrap"><button type="button" onClick={() => navigate(`/devices/${device.device_uuid}`)} className="font-semibold text-emerald-700">Open details</button>{hasPermission('policy.assign') && device.status === 'active' && <button type="button" onClick={() => open(device)} className="ml-3 font-semibold text-emerald-700">Policy</button>}</td></tr>)}</tbody></table></div>{filtered.length === 0 && <p className="p-8 text-center text-sm text-slate-500">No devices match these filters.</p>}</div>}
    <ActionDialog open={Boolean(selected)} onOpenChange={(value) => !value && setSelected(null)} title="Manage device policy" description="Assign an immutable revision, or choose no policy to clear the current assignment." submitLabel={revision ? 'Assign policy' : 'Clear policy'} busy={mutation.isPending} destructive={!revision} onSubmit={submit}>{error && <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</div>}<label className="block text-sm font-medium">Policy revision<select value={revision} onChange={(event) => setRevision(event.target.value)} className="mt-2 h-10 w-full rounded-lg border px-3"><option value="" disabled={!selected?.active_policy_assignment}>No policy (clear assignment)</option>{policies.data?.filter((policy) => policy.latest_revision).map((policy) => <option key={policy.latest_revision!.revision_uuid} value={policy.latest_revision!.revision_uuid}>{policy.name} v{policy.latest_revision!.version}</option>)}</select></label><label className="block text-sm font-medium">Reason<input required maxLength={512} value={reason} onChange={(event) => setReason(event.target.value)} className="mt-2 w-full rounded-lg border px-3 py-2" /></label></ActionDialog>
  </section>
}
