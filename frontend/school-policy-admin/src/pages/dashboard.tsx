import { Activity, AlertTriangle, Clock3, Laptop, LockKeyhole, ShieldCheck } from 'lucide-react'
import { useQueries } from '@tanstack/react-query'
import { adminService } from '@/services/admin.service'
import { ErrorState, LoadingState } from '@/components/ui/AsyncState'
import { formatDate } from '@/lib/format'

export function DashboardPage() {
  const results = useQueries({ queries: [
    { queryKey: ['dpc-summary'], queryFn: ({ signal }) => adminService.getDpcSummary(signal) },
    { queryKey: ['audit', 1, 'all'], queryFn: ({ signal }) => adminService.listAuditEvents({ page: 1, perPage: 10 }, undefined, signal) },
  ] })
  const [summary, audit] = results
  if (results.some((result) => result.isLoading)) return <LoadingState label="Loading control room…" />
  if (results.some((result) => result.isError) || !summary.data) return <ErrorState message="Control-room data is temporarily unavailable." retry={() => results.forEach((result) => void result.refetch())} />
  const stats = [
    { label: 'Managed devices', value: summary.data.managed_devices, icon: Laptop },
    { label: 'Active v3 policies', value: summary.data.active_v3_assignments, icon: ShieldCheck },
    { label: 'Block overrides', value: summary.data.active_block_overrides, icon: LockKeyhole },
    { label: 'Enforcement failures', value: summary.data.enforcement_failures, icon: AlertTriangle },
  ]
  return <section className="space-y-8">
    <header><p className="text-xs font-bold uppercase tracking-[.16em] text-emerald-700">EduGD control room</p><h1 className="mt-2 text-3xl font-semibold">Device policy at a glance</h1><p className="mt-2 text-sm text-slate-600">Live, privacy-limited administration data from the EduGD API.</p></header>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{stats.map(({ label, value, icon: Icon }) => <article key={label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex justify-between"><div><p className="text-sm text-slate-500">{label}</p><p className="mt-3 text-3xl font-semibold">{value}</p></div><Icon aria-hidden="true" className="size-5 text-emerald-700" /></div></article>)}</div>
    <section className="rounded-2xl border bg-white"><div className="flex items-center gap-3 border-b p-5"><Activity className="size-5" aria-hidden="true" /><div><h2 className="font-semibold">Recent audit activity</h2><p className="text-sm text-slate-500">Latest events visible to this administrator.</p></div></div>
      {audit.data?.audit_events.length ? <ul className="divide-y">{audit.data.audit_events.map((event) => <li key={event.event_uuid} className="flex flex-col gap-1 p-5 sm:flex-row sm:justify-between"><span className="font-medium">{event.event_type.replaceAll('_', ' ')}</span><span className="text-sm text-slate-500">{event.category} · {formatDate(event.occurred_at)}</span></li>)}</ul> : <p className="p-6 text-sm text-slate-500">No audit events are available.</p>}
    </section>
    <p className="inline-flex items-center gap-2 text-xs text-slate-600"><Clock3 className="size-4" />Screen-time and web-filter evidence appears only after a device reports it.</p>
  </section>
}
