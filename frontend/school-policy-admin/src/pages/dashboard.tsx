import { Activity, AlertTriangle, Laptop, ShieldCheck } from 'lucide-react'
import { useQueries } from '@tanstack/react-query'
import { adminService } from '@/services/admin.service'
import { ErrorState, LoadingState } from '@/components/ui/AsyncState'
import { formatDate } from '@/lib/format'

export function DashboardPage() {
  const results = useQueries({ queries: [
    { queryKey: ['devices', 1, 'all'], queryFn: ({ signal }) => adminService.listDevices({ page: 1, perPage: 1 }, undefined, signal) },
    { queryKey: ['policies', 1, 'all'], queryFn: ({ signal }) => adminService.listPolicies({ page: 1, perPage: 1 }, undefined, signal) },
    { queryKey: ['audit', 1, 'all'], queryFn: ({ signal }) => adminService.listAuditEvents({ page: 1, perPage: 10 }, undefined, signal) },
  ] })
  const [devices, policies, audit] = results
  if (results.some((result) => result.isLoading)) return <LoadingState label="Loading dashboard…" />
  if (results.some((result) => result.isError)) return <ErrorState message="Dashboard data is temporarily unavailable." retry={() => results.forEach((result) => void result.refetch())} />
  const failures = audit.data?.audit_events.filter((event) => event.failure_class).length ?? 0
  const stats = [
    { label: 'Managed devices', value: devices.data?.pagination.total ?? 0, icon: Laptop },
    { label: 'Policies', value: policies.data?.pagination.total ?? 0, icon: ShieldCheck },
    { label: 'Recent failures', value: failures, icon: AlertTriangle },
  ]
  return <section className="space-y-8">
    <header><h1 className="text-3xl font-semibold">System overview</h1><p className="mt-2 text-sm text-slate-600">Current data reported by the EduG administration API.</p></header>
    <div className="grid gap-4 sm:grid-cols-3">{stats.map(({ label, value, icon: Icon }) => <article key={label} className="rounded-2xl border bg-white p-5"><div className="flex justify-between"><div><p className="text-sm text-slate-500">{label}</p><p className="mt-3 text-3xl font-semibold">{value}</p></div><Icon aria-hidden="true" className="size-5 text-emerald-700" /></div></article>)}</div>
    <section className="rounded-2xl border bg-white"><div className="flex items-center gap-3 border-b p-5"><Activity className="size-5" aria-hidden="true" /><div><h2 className="font-semibold">Recent audit activity</h2><p className="text-sm text-slate-500">Latest events visible to this administrator.</p></div></div>
      {audit.data?.audit_events.length ? <ul className="divide-y">{audit.data.audit_events.map((event) => <li key={event.event_uuid} className="flex flex-col gap-1 p-5 sm:flex-row sm:justify-between"><span className="font-medium">{event.event_type.replaceAll('_', ' ')}</span><span className="text-sm text-slate-500">{event.category} · {formatDate(event.occurred_at)}</span></li>)}</ul> : <p className="p-6 text-sm text-slate-500">No audit events are available.</p>}
    </section>
  </section>
}
