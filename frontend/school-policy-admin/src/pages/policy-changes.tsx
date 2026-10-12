import { useQuery } from '@tanstack/react-query'
import { adminService } from '@/services/admin.service'
import { ErrorState, LoadingState } from '@/components/ui/AsyncState'
import { Pagination } from '@/components/ui/Pagination'
import { formatDate } from '@/lib/format'
import { useState } from 'react'

export function PolicyChangesPage() {
  const [page, setPage] = useState(1)
  const changes = useQuery({ queryKey: ['policy-changes', page], queryFn: ({ signal }) => adminService.listPolicyChanges({ page, perPage: 25 }, signal) })
  return <section className="space-y-6"><header><h1 className="text-3xl font-semibold">Policy-change log</h1><p className="mt-2 text-sm text-slate-600">Every assignment or replacement records the previous revision, new revision, administrator, reason, affected device and current result.</p></header>
    {changes.isLoading && <LoadingState label="Loading policy changes…" />}{changes.isError && <ErrorState message="Policy changes are temporarily unavailable." retry={() => void changes.refetch()} />}{changes.data && <div className="overflow-hidden rounded-2xl border bg-white"><div className="overflow-x-auto"><table className="w-full min-w-280 text-left text-sm"><thead className="bg-slate-50"><tr><th className="p-4">Policy change</th><th className="p-4">Device(s)</th><th className="p-4">Administrator</th><th className="p-4">Reason</th><th className="p-4">Result</th><th className="p-4">Date</th></tr></thead><tbody className="divide-y">{changes.data.policy_changes.map((change) => <tr key={change.event_uuid}><td className="p-4 font-medium">{change.previous_policy_name ? `${change.previous_policy_name} v${change.previous_version ?? '?'} → ` : ''}{change.policy_name ? `${change.policy_name} v${change.new_version ?? '?'}` : 'Policy cleared'}<div className="mt-1 text-xs text-slate-500">{change.operation}</div></td><td className="p-4">{change.asset_number ?? change.device_uuid ?? '—'}<div className="text-xs text-slate-500">{change.devices_affected} affected</div></td><td className="p-4">{change.administrator ?? 'Unknown'}</td><td className="max-w-72 p-4">{change.reason}</td><td className="p-4">{change.result}</td><td className="p-4">{formatDate(change.occurred_at)}</td></tr>)}</tbody></table></div>{changes.data.policy_changes.length === 0 && <p className="p-8 text-center text-sm text-slate-500">No policy changes have been recorded.</p>}<Pagination value={changes.data.pagination} onPage={setPage} /></div>}
  </section>
}
