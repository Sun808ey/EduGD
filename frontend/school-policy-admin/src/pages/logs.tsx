import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { adminService } from '@/services/admin.service'
import { Pagination } from '@/components/ui/Pagination'
import { ErrorState, LoadingState } from '@/components/ui/AsyncState'
import { formatDate } from '@/lib/format'

export function LogsPage() {
  const [page, setPage] = useState(1)
  const [eventType, setEventType] = useState('')
  const events = useQuery({ queryKey: ['audit', page, eventType], queryFn: ({ signal }) => adminService.listAuditEvents({ page, perPage: 25 }, eventType || undefined, signal) })
  return <section className="space-y-6"><header><h1 className="text-3xl font-semibold">Audit events</h1><p className="mt-2 text-sm text-slate-600">Review administrative, enrollment, assignment and synchronization activity.</p></header>
    <label className="block max-w-sm text-sm font-medium">Event type<select value={eventType} onChange={(event) => { setEventType(event.target.value); setPage(1) }} className="mt-2 h-10 w-full rounded-lg border bg-white px-3"><option value="">All event types</option><option value="administrator_authentication">Administrator authentication</option><option value="device_enrollment">Device enrollment</option><option value="policy_assignment">Policy assignment</option><option value="policy_synchronization">Policy synchronization</option></select></label>
    {events.isLoading && <LoadingState label="Loading audit events…" />}{events.isError && <ErrorState message="Audit events are temporarily unavailable." retry={() => void events.refetch()} />}
    {events.data && <div className="overflow-hidden rounded-2xl border bg-white"><div className="overflow-x-auto"><table className="w-full min-w-220 text-left text-sm"><thead className="bg-slate-50"><tr><th className="p-4">Type</th><th className="p-4">Category</th><th className="p-4">Operation</th><th className="p-4">Occurred</th><th className="p-4">Device / revision</th><th className="p-4">Event UUID</th></tr></thead><tbody className="divide-y">{events.data.audit_events.map((event) => <tr key={event.event_uuid}><td className="p-4">{event.event_type.replaceAll('_', ' ')}</td><td className="p-4">{event.failure_class ? `${event.category} (${event.failure_class})` : event.category}</td><td className="p-4">{event.operation ?? '—'}</td><td className="p-4">{formatDate(event.occurred_at)}</td><td className="p-4 font-mono text-xs">{event.device_uuid ?? event.policy_revision_uuid ?? '—'}</td><td className="p-4 font-mono text-xs">{event.event_uuid}</td></tr>)}</tbody></table></div>{events.data.audit_events.length === 0 && <p className="p-8 text-center text-sm text-slate-500">No audit events match this filter.</p>}<Pagination value={events.data.pagination} onPage={setPage} /></div>}
  </section>
}
