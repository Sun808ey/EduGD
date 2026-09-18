import { useState } from 'react'
import type { FormEvent } from 'react'
import { ArrowLeft } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { adminService } from '@/services/admin.service'
import { ActionDialog } from '@/components/ui/ActionDialog'
import { ErrorState, LoadingState } from '@/components/ui/AsyncState'
import { useAuth } from '@/hooks/useAuth'
import { errorMessage } from '@/services/errors'
import { formatDate } from '@/lib/format'

export function DeviceDetailPage() {
  const { deviceUuid = '' } = useParams()
  const { hasPermission } = useAuth()
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const cache = useQueryClient()
  const device = useQuery({ queryKey: ['device', deviceUuid], queryFn: ({ signal }) => adminService.getDevice(deviceUuid, signal), enabled: Boolean(deviceUuid) })
  const assignment = useQuery({ queryKey: ['assignment', deviceUuid], queryFn: ({ signal }) => adminService.getCurrentAssignment(deviceUuid, signal), enabled: Boolean(deviceUuid) })
  const revoke = useMutation({ mutationFn: () => adminService.revokeDeviceCredential(deviceUuid, reason.trim()), onSuccess: async () => { setOpen(false); setReason(''); await cache.invalidateQueries({ queryKey: ['device', deviceUuid] }) }, onError: (caught) => setError(errorMessage(caught)) })
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (reason.trim()) revoke.mutate() }
  if (device.isLoading || assignment.isLoading) return <LoadingState label="Loading device…" />
  if (device.isError || assignment.isError || !device.data) return <ErrorState message="This device could not be loaded." retry={() => { void device.refetch(); void assignment.refetch() }} />
  return <section className="space-y-6"><Link to="/devices" className="inline-flex items-center gap-2 font-semibold text-emerald-700"><ArrowLeft className="size-4" />Devices</Link><header><h1 className="break-all text-3xl font-semibold">{device.data.device_uuid}</h1><p className="mt-2 text-sm text-slate-600">Registered {formatDate(device.data.registered_at)}</p></header>
    <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><Info label="Status" value={device.data.status} /><Info label="Enrollment" value={device.data.enrollment_state ?? 'Unknown'} /><Info label="Last sync" value={formatDate(device.data.last_sync_at)} /><Info label="Android" value={`${device.data.android_version ?? 'Unknown'} / API ${device.data.api_level ?? 'Unknown'}`} /></dl>
    <section className="rounded-2xl border bg-white p-5"><h2 className="font-semibold">Current policy assignment</h2>{assignment.data?.assignment ? <dl className="mt-4 space-y-2 text-sm"><InfoRow label="Policy" value={`${assignment.data.assignment.policy_name} v${assignment.data.assignment.policy_version}`} /><InfoRow label="Revision" value={assignment.data.assignment.policy_revision_uuid} /><InfoRow label="Assigned" value={formatDate(assignment.data.assignment.assigned_at)} /></dl> : <p className="mt-3 text-sm text-slate-500">No policy is assigned.</p>}</section>
    {hasPermission('device_credential.revoke') && <button type="button" onClick={() => setOpen(true)} className="rounded-lg bg-red-700 px-4 py-2 font-semibold text-white">Revoke active credential</button>}
    <ActionDialog open={open} onOpenChange={setOpen} title="Revoke device credential" description="The device must enroll again before authenticated synchronization can continue." submitLabel="Revoke credential" busy={revoke.isPending} destructive onSubmit={submit}>{error && <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-800">{error}</div>}<label className="block text-sm font-medium">Reason<input required maxLength={512} value={reason} onChange={(event) => setReason(event.target.value)} className="mt-2 w-full rounded-lg border px-3 py-2" /></label></ActionDialog>
  </section>
}

function Info({ label, value }: { label: string; value: string }) { return <div className="rounded-xl border bg-white p-4"><dt className="text-sm text-slate-500">{label}</dt><dd className="mt-1 break-all font-semibold">{value}</dd></div> }
function InfoRow({ label, value }: { label: string; value: string }) { return <div><dt className="text-slate-500">{label}</dt><dd className="break-all font-medium">{value}</dd></div> }
