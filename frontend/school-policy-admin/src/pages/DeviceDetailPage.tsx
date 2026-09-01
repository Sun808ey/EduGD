import { ArrowLeft, Laptop, ShieldCheck } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { adminService } from '@/services/admin.service'
import type { DeviceDetail } from '@/types/api'

export function DeviceDetailPage() {
  const { deviceUuid = '' } = useParams()
  const [device, setDevice] = useState<DeviceDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!deviceUuid) return
    adminService.getDevice(deviceUuid).then(setDevice).catch(() => setError('This device could not be loaded.')).finally(() => setLoading(false))
  }, [deviceUuid])

  if (loading) return <div className="grid min-h-64 place-items-center text-sm text-slate-500">Loading device...</div>
  if (error || !device) return <section className="space-y-6"><BackLink /><div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error || 'Device not found.'}</div></section>

  return <section className="space-y-8"><BackLink /><header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Device detail</p><h1 className="mt-2 break-all text-3xl font-semibold tracking-tight">{device.device_uuid}</h1><p className="mt-2 text-sm text-slate-600">Registered {formatDate(device.registered_at)}</p></div><span className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700">{device.status}</span></header><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><InfoCard label="Enrollment" value={device.enrollment_state ?? 'Unknown'} /><InfoCard label="Android" value={device.android_version ?? 'Unknown'} /><InfoCard label="API level" value={String(device.api_level ?? 'Unknown')} /><InfoCard label="Last sync" value={formatDate(device.last_sync_at)} /></div><div className="grid gap-6 xl:grid-cols-2"><section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><div className="flex items-center gap-3"><Laptop className="size-5 text-slate-500" /><h2 className="font-semibold">Device identity</h2></div><dl className="mt-6 space-y-4 text-sm"><Row label="Device UUID" value={device.device_uuid} /><Row label="Created" value={formatDate(device.created_at)} /><Row label="Updated" value={formatDate(device.updated_at)} /></dl></section><section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><div className="flex items-center gap-3"><ShieldCheck className="size-5 text-slate-500" /><h2 className="font-semibold">Active policy</h2></div>{device.active_policy_assignment ? <dl className="mt-6 space-y-4 text-sm"><Row label="Policy" value={`${device.active_policy_assignment.policy_name} v${device.active_policy_assignment.policy_version}`} /><Row label="Assigned" value={formatDate(device.active_policy_assignment.assigned_at)} /><Row label="Revision" value={device.active_policy_assignment.policy_revision_uuid} /></dl> : <p className="mt-6 text-sm text-slate-500">No policy is currently assigned.</p>}</section></div></section>
}

function BackLink() { return <Link to="/devices" className="inline-flex items-center gap-2 text-sm font-semibold text-emerald-700 hover:text-emerald-900"><ArrowLeft className="size-4" />Back to devices</Link> }
function InfoCard({ label, value }: { label: string; value: string }) { return <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm text-slate-500">{label}</p><p className="mt-2 truncate text-lg font-semibold">{value}</p></div> }
function Row({ label, value }: { label: string; value: string }) { return <div className="flex flex-col gap-1"><dt className="text-slate-500">{label}</dt><dd className="break-all font-medium text-slate-900">{value}</dd></div> }
function formatDate(value?: string | null) { return value ? new Date(value).toLocaleString() : 'Unknown' }