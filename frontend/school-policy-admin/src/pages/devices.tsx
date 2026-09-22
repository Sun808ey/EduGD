import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { adminService } from '@/services/admin.service'
import { useAuth } from '@/hooks/useAuth'
import { ActionDialog } from '@/components/ui/ActionDialog'
import { Pagination } from '@/components/ui/Pagination'
import { ErrorState, LoadingState } from '@/components/ui/AsyncState'
import { errorMessage } from '@/services/errors'
import { formatDate } from '@/lib/format'
import type { Device } from '@/types/api.types'

export function DevicesPage() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [selected, setSelected] = useState<Device | null>(null)
  const [revision, setRevision] = useState('')
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const { hasPermission } = useAuth()
  const cache = useQueryClient()
  const devices = useQuery({ queryKey: ['devices', page, status], queryFn: ({ signal }) => adminService.listDevices({ page, perPage: 25 }, status || undefined, signal) })
  const policies = useQuery({ queryKey: ['policies', 'all'], queryFn: ({ signal }) => adminService.listAllPolicies(signal), enabled: Boolean(selected) })
  const mutation = useMutation({ mutationFn: async () => {
    if (!selected || !reason.trim()) throw new Error('A reason is required.')
    if (!revision && !selected.active_policy_assignment) throw new Error('Select a policy revision for this unassigned device.')
    return revision ? adminService.assignPolicy(selected.device_uuid, revision, reason.trim()) : adminService.clearPolicy(selected.device_uuid, reason.trim())
  }, onSuccess: async () => { setSelected(null); setReason(''); setRevision(''); await cache.invalidateQueries({ queryKey: ['devices'] }) }, onError: (caught) => setError(errorMessage(caught)) })

  function open(device: Device) { setSelected(device); setRevision(device.active_policy_assignment?.policy_revision_uuid ?? ''); setReason(''); setError('') }
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); mutation.mutate() }

  return <section className="space-y-6"><header><h1 className="text-3xl font-semibold">Devices</h1><p className="mt-2 text-sm text-slate-600">Monitor enrollment, synchronization and assigned policy state.</p></header>
    <label className="block max-w-xs text-sm font-medium">Status<select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }} className="mt-2 h-10 w-full rounded-lg border bg-white px-3"><option value="">All statuses</option><option value="active">Active</option><option value="suspended">Suspended</option><option value="retired">Retired</option></select></label>
    {devices.isLoading && <LoadingState label="Loading devices…" />}{devices.isError && <ErrorState message="Devices are temporarily unavailable." retry={() => void devices.refetch()} />}
    {devices.data && <div className="overflow-hidden rounded-2xl border bg-white"><div className="overflow-x-auto"><table className="w-full min-w-190 text-left text-sm"><thead className="bg-slate-50"><tr><th className="p-4">Device UUID</th><th className="p-4">Status</th><th className="p-4">Android</th><th className="p-4">Last sync</th><th className="p-4">Policy</th><th className="p-4">Actions</th></tr></thead><tbody className="divide-y">{devices.data.devices.map((device) => <tr key={device.device_uuid}><td className="p-4 font-mono text-xs"><Link className="text-emerald-700 underline" to={`/devices/${device.device_uuid}`}>{device.device_uuid}</Link></td><td className="p-4">{device.status}</td><td className="p-4">{device.android_version ?? 'Unknown'} / API {device.api_level ?? 'Unknown'}</td><td className="p-4">{formatDate(device.last_sync_at)}</td><td className="p-4">{device.active_policy_assignment ? `${device.active_policy_assignment.policy_name} v${device.active_policy_assignment.policy_version}` : 'Unassigned'}</td><td className="p-4">{hasPermission('policy.assign') && device.status === 'active' ? <button type="button" onClick={() => open(device)} className="font-semibold text-emerald-700">Manage policy</button> : <span className="text-slate-500">Read only</span>}</td></tr>)}</tbody></table></div>{devices.data.devices.length === 0 && <p className="p-8 text-center text-sm text-slate-500">No devices match this filter.</p>}<Pagination value={devices.data.pagination} onPage={setPage} /></div>}
    <ActionDialog open={Boolean(selected)} onOpenChange={(value) => !value && setSelected(null)} title="Manage device policy" description="Assign an immutable revision, or choose no policy to clear the current assignment." submitLabel={revision ? 'Assign policy' : 'Clear policy'} busy={mutation.isPending} destructive={!revision} onSubmit={submit}>
      {error && <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</div>}
      <label className="block text-sm font-medium">Policy revision<select value={revision} onChange={(event) => setRevision(event.target.value)} className="mt-2 h-10 w-full rounded-lg border px-3"><option value="" disabled={!selected?.active_policy_assignment}>No policy (clear assignment)</option>{policies.data?.filter((policy) => policy.latest_revision).map((policy) => <option key={policy.latest_revision!.revision_uuid} value={policy.latest_revision!.revision_uuid}>{policy.name} v{policy.latest_revision!.version}</option>)}</select></label>
      <label className="block text-sm font-medium">Reason<input required maxLength={512} value={reason} onChange={(event) => setReason(event.target.value)} className="mt-2 w-full rounded-lg border px-3 py-2" /></label>
    </ActionDialog>
  </section>
}
