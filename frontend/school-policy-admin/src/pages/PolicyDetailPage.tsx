import { ArrowLeft } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { useState } from 'react'
import { useQueries } from '@tanstack/react-query'
import { adminService } from '@/services/admin.service'
import { Pagination } from '@/components/ui/Pagination'
import { ErrorState, LoadingState } from '@/components/ui/AsyncState'
import { formatDate } from '@/lib/format'

export function PolicyDetailPage() {
  const { policyUuid = '' } = useParams()
  const [page, setPage] = useState(1)
  const [policy, revisions] = useQueries({ queries: [
    { queryKey: ['policy', policyUuid], queryFn: ({ signal }) => adminService.getPolicy(policyUuid, signal), enabled: Boolean(policyUuid) },
    { queryKey: ['policy-revisions', policyUuid, page], queryFn: ({ signal }) => adminService.listPolicyRevisions(policyUuid, { page, perPage: 25 }, signal), enabled: Boolean(policyUuid) },
  ] })
  if (policy.isLoading || revisions.isLoading) return <LoadingState label="Loading policy…" />
  if (policy.isError || revisions.isError || !policy.data || !revisions.data) return <ErrorState message="This policy could not be loaded." retry={() => { void policy.refetch(); void revisions.refetch() }} />
  const latest = policy.data.latest_revision
  return <section className="space-y-6"><Link to="/policies" className="inline-flex items-center gap-2 font-semibold text-emerald-700"><ArrowLeft className="size-4" />Policies</Link>
    <header><h1 className="text-3xl font-semibold">{policy.data.name}</h1><p className="mt-2 break-all text-sm text-slate-500">{policy.data.policy_uuid}</p></header>
    <dl className="grid gap-4 sm:grid-cols-3"><Info label="Status" value={policy.data.status} /><Info label="Revisions" value={String(policy.data.revision_count ?? revisions.data.pagination.total)} /><Info label="Updated" value={formatDate(policy.data.updated_at)} /></dl>
    <div className="overflow-hidden rounded-2xl border bg-white"><h2 className="border-b p-5 font-semibold">Immutable revision history</h2><div className="overflow-x-auto"><table className="w-full min-w-160 text-left text-sm"><thead className="bg-slate-50"><tr><th className="p-4">Version</th><th className="p-4">Created</th><th className="p-4">Content hash</th><th className="p-4">Created by</th></tr></thead><tbody className="divide-y">{revisions.data.revisions.map((revision) => <tr key={revision.revision_uuid}><td className="p-4 font-semibold">v{revision.version}</td><td className="p-4">{formatDate(revision.created_at)}</td><td className="max-w-72 truncate p-4 font-mono text-xs">{revision.content_hash}</td><td className="p-4">{revision.created_by ?? 'System'}</td></tr>)}</tbody></table></div><Pagination value={revisions.data.pagination} onPage={setPage} /></div>
    <section className="rounded-2xl border bg-white"><h2 className="border-b p-5 font-semibold">Latest policy payload {latest ? `(v${latest.version})` : ''}</h2>{latest ? <pre className="max-h-120 overflow-auto bg-slate-950 p-5 text-xs text-emerald-100">{JSON.stringify(latest.payload, null, 2)}</pre> : <p className="p-6 text-sm text-slate-500">No revision is available.</p>}</section>
  </section>
}

function Info({ label, value }: { label: string; value: string }) { return <div className="rounded-xl border bg-white p-4"><dt className="text-sm text-slate-500">{label}</dt><dd className="mt-1 font-semibold">{value}</dd></div> }
