import { ArrowLeft, Braces, FileText } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { adminService } from '@/services/admin.service'
import type { PolicyDetail, PolicyRevisionSummary } from '@/types/api'

export function PolicyDetailPage() {
  const { policyUuid = '' } = useParams()
  const [policy, setPolicy] = useState<PolicyDetail | null>(null)
  const [revisions, setRevisions] = useState<PolicyRevisionSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!policyUuid) return
    Promise.all([adminService.getPolicy(policyUuid), adminService.listPolicyRevisions(policyUuid)])
      .then(([policyData, revisionData]) => {
        setPolicy(policyData)
        setRevisions(revisionData.revisions)
      })
      .catch(() => setError('This policy could not be loaded.'))
      .finally(() => setLoading(false))
  }, [policyUuid])

  if (loading) return <div className="grid min-h-64 place-items-center text-sm text-slate-500">Loading policy...</div>
  if (error || !policy) return <section className="space-y-6"><BackLink /><div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error || 'Policy not found.'}</div></section>

  const latestRevision = revisions[0] ?? policy.latest_revision
  const payload = latestRevision?.payload

  return (
    <section className="space-y-8">
      <BackLink />
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Policy detail</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">{policy.name}</h1>
          <p className="mt-2 break-all text-sm text-slate-600">{policy.policy_uuid}</p>
        </div>
        <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700">{policy.status}</span>
      </header>

      <div className="grid gap-4 sm:grid-cols-3">
        <SummaryCard label="Revisions" value={String(policy.revision_count)} />
        <SummaryCard label="Latest version" value={latestRevision ? `v${latestRevision.version}` : 'None'} />
        <SummaryCard label="Last updated" value={policy.updated_at ? new Date(policy.updated_at).toLocaleString() : 'Unknown'} />
      </div>

      <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center gap-3 border-b border-slate-200 p-5">
          <FileText className="size-5 text-slate-500" />
          <div><h2 className="font-semibold">Revision history</h2><p className="mt-1 text-sm text-slate-500">Immutable revisions available for assignment.</p></div>
        </div>
        {revisions.length === 0 ? <div className="p-8 text-center text-sm text-slate-500">No revisions recorded.</div> : <div className="overflow-x-auto"><table className="w-full min-w-155 text-left text-sm"><thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3 font-semibold">Version</th><th className="px-5 py-3 font-semibold">Created</th><th className="px-5 py-3 font-semibold">Content hash</th><th className="px-5 py-3 font-semibold">Created by</th></tr></thead><tbody className="divide-y divide-slate-100">{revisions.map((revision) => <tr key={revision.revision_uuid}><td className="px-5 py-4 font-semibold text-slate-900">v{revision.version}</td><td className="px-5 py-4 text-slate-600">{revision.created_at ? new Date(revision.created_at).toLocaleString() : 'Unknown'}</td><td className="max-w-64 truncate px-5 py-4 font-mono text-xs text-slate-500">{revision.content_hash ?? 'Unavailable'}</td><td className="px-5 py-4 text-slate-600">{revision.created_by ?? 'System'}</td></tr>)}</tbody></table></div>}
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center gap-3 border-b border-slate-200 p-5"><Braces className="size-5 text-slate-500" /><div><h2 className="font-semibold">Latest payload</h2><p className="mt-1 text-sm text-slate-500">Read-only policy JSON for the latest revision.</p></div></div>
        {payload ? <pre className="max-h-120 overflow-auto bg-slate-950 p-5 text-xs leading-6 text-emerald-100">{JSON.stringify(payload, null, 2)}</pre> : <div className="p-8 text-center text-sm text-slate-500">No payload is available for the latest revision.</div>}
      </section>
    </section>
  )
}

function BackLink() {
  return <Link to="/policies" className="inline-flex items-center gap-2 text-sm font-semibold text-emerald-700 hover:text-emerald-900"><ArrowLeft className="size-4" />Back to policies</Link>
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm text-slate-500">{label}</p><p className="mt-2 text-2xl font-semibold">{value}</p></div>
}
