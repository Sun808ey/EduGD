import { FileText } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { adminService } from '@/services/admin.service'
import type { PolicySummary } from '@/types/api'

export function PoliciesPage() {
  const [count, setCount] = useState(0)
  const [policies, setPolicies] = useState<PolicySummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    adminService.listPolicies()
      .then((data) => { setCount(data.pagination.total); setPolicies(data.policies) })
      .catch(() => setError('Policies are temporarily unavailable.'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <section className="space-y-8">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Workspace</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Policies</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-600">Build and publish policy revisions, then assign them to the right devices.</p>
      </header>
      {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-200 p-5">
          <div><h2 className="font-semibold">Policy library</h2><p className="mt-1 text-sm text-slate-500">{loading ? 'Loading policies...' : `${count} policies available`}</p></div>
          <Button><FileText className="size-4" />Create policy</Button>
        </div>
        {loading && <div className="p-10 text-center text-sm text-slate-500">Loading policy library...</div>}
        {!loading && policies.length > 0 && <div className="overflow-x-auto"><table className="w-full min-w-155 text-left text-sm"><thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3 font-semibold">Name</th><th className="px-5 py-3 font-semibold">Status</th><th className="px-5 py-3 font-semibold">Latest revision</th><th className="px-5 py-3 font-semibold">Updated</th><th className="px-5 py-3 font-semibold">Action</th></tr></thead><tbody className="divide-y divide-slate-100">{policies.map((policy) => <tr key={policy.policy_uuid} className="hover:bg-slate-50"><td className="px-5 py-4 font-medium text-slate-900">{policy.name}</td><td className="px-5 py-4 text-slate-600">{policy.status}</td><td className="px-5 py-4 text-slate-600">{policy.latest_revision ? `v${policy.latest_revision.version}` : 'No revisions'}</td><td className="px-5 py-4 text-slate-600">{policy.updated_at ? new Date(policy.updated_at).toLocaleDateString() : 'Unknown'}</td><td className="px-5 py-4"><Link to={`/policies/${policy.policy_uuid}`} className="text-sm font-semibold text-emerald-700 hover:text-emerald-900">View details</Link></td></tr>)}</tbody></table></div>}
        {!loading && policies.length === 0 && <div className="p-10 text-center"><div className="mx-auto grid size-12 place-items-center rounded-2xl bg-emerald-50 text-emerald-700"><FileText className="size-6" /></div><h2 className="mt-4 font-semibold">Your policy library is ready</h2><p className="mx-auto mt-1 max-w-md text-sm text-slate-500">Create a policy to define the first managed experience for your schools.</p></div>}
      </div>
    </section>
  )
}
