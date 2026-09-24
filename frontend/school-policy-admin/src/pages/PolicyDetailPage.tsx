import { ArrowLeft } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQueries, useQueryClient } from '@tanstack/react-query'
import { adminService } from '@/services/admin.service'
import { Pagination } from '@/components/ui/Pagination'
import { ErrorState, LoadingState } from '@/components/ui/AsyncState'
import { ActionDialog } from '@/components/ui/ActionDialog'
import { formatDate } from '@/lib/format'
import { errorMessage } from '@/services/errors'
import { useAuth } from '@/hooks/useAuth'

type PolicyAction = 'revision' | 'active' | 'inactive' | 'revoked'

export function PolicyDetailPage() {
  const { policyUuid = '' } = useParams()
  const [page, setPage] = useState(1)
  const [action, setAction] = useState<PolicyAction | null>(null)
  const [revisionPayload, setRevisionPayload] = useState('')
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const { hasPermission } = useAuth()
  const queryClient = useQueryClient()
  const [policy, revisions] = useQueries({ queries: [
    { queryKey: ['policy', policyUuid], queryFn: ({ signal }) => adminService.getPolicy(policyUuid, signal), enabled: Boolean(policyUuid) },
    { queryKey: ['policy-revisions', policyUuid, page], queryFn: ({ signal }) => adminService.listPolicyRevisions(policyUuid, { page, perPage: 25 }, signal), enabled: Boolean(policyUuid) },
  ] })
  const latest = policy.data?.latest_revision
  const revision = useMutation({
    mutationFn: () => {
      const parsed: unknown = JSON.parse(revisionPayload)
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) throw new Error('Payload must be a JSON object.')
      return adminService.createPolicyRevision(policyUuid, parsed as Record<string, unknown>)
    },
    onSuccess: async () => { closeAction(); await invalidatePolicy() },
    onError: (caught) => setError(errorMessage(caught)),
  })
  const lifecycle = useMutation({
    mutationFn: () => adminService.setPolicyLifecycle(policyUuid, action as Exclude<PolicyAction, 'revision'>, reason.trim()),
    onSuccess: async () => { closeAction(); await invalidatePolicy() },
    onError: (caught) => setError(errorMessage(caught)),
  })
  const busy = revision.isPending || lifecycle.isPending
  const closeAction = () => { if (busy) return; setAction(null); setError(''); setReason('') }
  const invalidatePolicy = () => Promise.all([
    queryClient.invalidateQueries({ queryKey: ['policy', policyUuid] }),
    queryClient.invalidateQueries({ queryKey: ['policy-revisions', policyUuid] }),
    queryClient.invalidateQueries({ queryKey: ['policies'] }),
  ])
  const openRevision = () => { setRevisionPayload(JSON.stringify(latest?.payload ?? {}, null, 2)); setError(''); setAction('revision') }
  const openLifecycle = (next: Exclude<PolicyAction, 'revision'>) => { setReason(''); setError(''); setAction(next) }
  const submitAction = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); if (action === 'revision') revision.mutate(); else if (action) lifecycle.mutate() }
  if (policy.isLoading || revisions.isLoading) return <LoadingState label="Loading policy…" />
  if (policy.isError || revisions.isError || !policy.data || !revisions.data) return <ErrorState message="This policy could not be loaded." retry={() => { void policy.refetch(); void revisions.refetch() }} />
  return <section className="space-y-6"><Link to="/policies" className="inline-flex items-center gap-2 font-semibold text-emerald-700"><ArrowLeft className="size-4" />Policies</Link>
    <header className="flex flex-wrap items-end justify-between gap-4"><div><h1 className="text-3xl font-semibold">{policy.data.name}</h1><p className="mt-2 break-all text-sm text-slate-500">{policy.data.policy_uuid}</p></div>{hasPermission('policy.manage') && <div className="flex flex-wrap gap-2"><button type="button" onClick={openRevision} className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white">Add revision</button>{policy.data.status !== 'active' && <button type="button" onClick={() => openLifecycle('active')} className="rounded-lg border border-emerald-700 px-4 py-2 text-sm font-semibold text-emerald-700">Activate</button>}{policy.data.status !== 'inactive' && <button type="button" onClick={() => openLifecycle('inactive')} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700">Set inactive</button>}{policy.data.status !== 'revoked' && <button type="button" onClick={() => openLifecycle('revoked')} className="rounded-lg border border-red-300 px-4 py-2 text-sm font-semibold text-red-700">Revoke</button>}</div>}</header>
    <dl className="grid gap-4 sm:grid-cols-3"><Info label="Status" value={policy.data.status} /><Info label="Revisions" value={String(policy.data.revision_count ?? revisions.data.pagination.total)} /><Info label="Updated" value={formatDate(policy.data.updated_at)} /></dl>
    <div className="overflow-hidden rounded-2xl border bg-white"><h2 className="border-b p-5 font-semibold">Immutable revision history</h2><div className="overflow-x-auto"><table className="w-full min-w-160 text-left text-sm"><thead className="bg-slate-50"><tr><th className="p-4">Version</th><th className="p-4">Created</th><th className="p-4">Content hash</th><th className="p-4">Created by</th></tr></thead><tbody className="divide-y">{revisions.data.revisions.map((revision) => <tr key={revision.revision_uuid}><td className="p-4 font-semibold">v{revision.version}</td><td className="p-4">{formatDate(revision.created_at)}</td><td className="max-w-72 truncate p-4 font-mono text-xs">{revision.content_hash}</td><td className="p-4">{revision.created_by ?? 'System'}</td></tr>)}</tbody></table></div><Pagination value={revisions.data.pagination} onPage={setPage} /></div>
    <section className="rounded-2xl border bg-white"><h2 className="border-b p-5 font-semibold">Latest policy payload {latest ? `(v${latest.version})` : ''}</h2>{latest ? <pre className="max-h-120 overflow-auto bg-slate-950 p-5 text-xs text-emerald-100">{JSON.stringify(latest.payload, null, 2)}</pre> : <p className="p-6 text-sm text-slate-500">No revision is available.</p>}</section>
    <ActionDialog open={Boolean(action)} onOpenChange={(open) => !open && closeAction()} title={action === 'revision' ? 'Add policy revision' : `${action === 'active' ? 'Activate' : action === 'inactive' ? 'Set inactive' : 'Revoke'} policy`} description={action === 'revision' ? 'Submit a complete JSON policy payload. The server validates and canonicalizes it before creating the next immutable revision.' : 'Provide an operator reason. This action is recorded by the server and changes the policy lifecycle state.'} submitLabel={action === 'revision' ? 'Create revision' : 'Save lifecycle change'} busy={busy} destructive={action === 'revoked'} onSubmit={submitAction}>
      {action === 'revision' ? <label className="block text-sm font-medium text-slate-700">Policy payload<textarea required value={revisionPayload} onChange={(event) => setRevisionPayload(event.target.value)} className="mt-2 min-h-80 w-full rounded-lg border p-3 font-mono text-xs" spellCheck={false} aria-describedby="revision-help" /> <span id="revision-help" className="mt-2 block text-xs font-normal text-slate-500">Use the same validated policy contract used when creating a policy.</span></label> : <label className="block text-sm font-medium text-slate-700">Reason<input required maxLength={512} value={reason} onChange={(event) => setReason(event.target.value)} className="mt-2 w-full rounded-lg border px-3 py-2" /></label>}
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    </ActionDialog>
  </section>
}

function Info({ label, value }: { label: string; value: string }) { return <div className="rounded-xl border bg-white p-4"><dt className="text-sm text-slate-500">{label}</dt><dd className="mt-1 font-semibold">{value}</dd></div> }
