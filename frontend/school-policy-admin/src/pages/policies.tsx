import { FileText } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { adminService } from '@/services/admin.service'
import { Pagination } from '@/components/ui/Pagination'
import { ErrorState, LoadingState } from '@/components/ui/AsyncState'
import { formatDate } from '@/lib/format'

export function PoliciesPage() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const query = useQuery({ queryKey: ['policies', page, status], queryFn: ({ signal }) => adminService.listPolicies({ page, perPage: 25 }, status || undefined, signal) })
  return <section className="space-y-6">
    <header><h1 className="text-3xl font-semibold">Policies</h1><p className="mt-2 text-sm text-slate-600">Review policy definitions and their immutable revision history.</p></header>
    <label className="block max-w-xs text-sm font-medium">Status
      <select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }} className="mt-2 h-10 w-full rounded-lg border bg-white px-3"><option value="">All statuses</option><option value="draft">Draft</option><option value="active">Active</option><option value="inactive">Inactive</option><option value="revoked">Revoked</option></select>
    </label>
    {query.isLoading && <LoadingState label="Loading policies…" />}
    {query.isError && <ErrorState message="Policies are temporarily unavailable." retry={() => void query.refetch()} />}
    {query.data && <div className="overflow-hidden rounded-2xl border bg-white"><div className="overflow-x-auto"><table className="w-full min-w-160 text-left text-sm"><thead className="bg-slate-50"><tr><th className="p-4">Policy</th><th className="p-4">Status</th><th className="p-4">Latest revision</th><th className="p-4">Updated</th><th className="p-4">Action</th></tr></thead><tbody className="divide-y">{query.data.policies.map((policy) => <tr key={policy.policy_uuid}><td className="p-4 font-medium"><FileText className="mr-2 inline size-4" aria-hidden="true" />{policy.name}</td><td className="p-4">{policy.status}</td><td className="p-4">{policy.latest_revision ? `v${policy.latest_revision.version}` : 'None'}</td><td className="p-4">{formatDate(policy.updated_at)}</td><td className="p-4"><Link className="font-semibold text-emerald-700" to={`/policies/${policy.policy_uuid}`}>View</Link></td></tr>)}</tbody></table></div>{query.data.policies.length === 0 && <p className="p-8 text-center text-sm text-slate-500">No policies match this filter.</p>}<Pagination value={query.data.pagination} onPage={setPage} /></div>}
  </section>
}
