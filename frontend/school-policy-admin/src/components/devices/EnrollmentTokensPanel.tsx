import { useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { adminService } from '@/services/admin.service'
import { ActionDialog } from '@/components/ui/ActionDialog'
import { Pagination } from '@/components/ui/Pagination'
import { ErrorState, LoadingState } from '@/components/ui/AsyncState'
import { useAuth } from '@/hooks/useAuth'
import { errorMessage } from '@/services/errors'
import { formatDate } from '@/lib/format'
import type { EnrollmentToken, IssuedEnrollmentToken } from '@/types/api.types'

export function EnrollmentTokensPanel() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [issueOpen, setIssueOpen] = useState(false)
  const [revokeTarget, setRevokeTarget] = useState<EnrollmentToken | null>(null)
  const [reason, setReason] = useState('')
  const [boundDevice, setBoundDevice] = useState('')
  const [issued, setIssued] = useState<IssuedEnrollmentToken | null>(null)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState('')
  const { hasPermission } = useAuth()
  const cache = useQueryClient()
  const tokens = useQuery({ queryKey: ['enrollment-tokens', page, status], queryFn: ({ signal }) => adminService.listEnrollmentTokens({ page, perPage: 25 }, status || undefined, signal) })
  const issue = useMutation({ mutationFn: () => adminService.issueEnrollmentToken(reason.trim(), boundDevice.trim() || undefined), onSuccess: async (result) => { setIssued(result); setReason(''); setBoundDevice(''); await cache.invalidateQueries({ queryKey: ['enrollment-tokens'] }) }, onError: (caught) => setError(errorMessage(caught)) })
  const revoke = useMutation({ mutationFn: () => adminService.revokeEnrollmentToken(revokeTarget!.token_uuid, reason.trim()), onSuccess: async () => { setRevokeTarget(null); setReason(''); await cache.invalidateQueries({ queryKey: ['enrollment-tokens'] }) }, onError: (caught) => setError(errorMessage(caught)) })
  function submitIssue(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (reason.trim()) issue.mutate() }
  function submitRevoke(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (reason.trim() && revokeTarget) revoke.mutate() }

  return <section className="space-y-4"><header className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-xl font-semibold">Enrollment tokens</h2><p className="mt-1 text-sm text-slate-600">Issue and review short-lived device pairing credentials.</p></div>{hasPermission('enrollment_token.issue') && <button type="button" onClick={() => { setIssued(null); setCopied(false); setReason(''); setBoundDevice(''); setError(''); setIssueOpen(true) }} className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white">Issue token</button>}</header>
    <label className="block max-w-xs text-sm font-medium">Status<select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }} className="mt-2 h-10 w-full rounded-lg border bg-white px-3"><option value="">All statuses</option><option value="active">Active</option><option value="consumed">Consumed</option><option value="revoked">Revoked</option><option value="expired">Expired</option><option value="locked">Locked</option></select></label>
    {tokens.isLoading && <LoadingState label="Loading enrollment tokens…" />}{tokens.isError && <ErrorState message="Enrollment tokens are temporarily unavailable." retry={() => void tokens.refetch()} />}
    {tokens.data && <div className="overflow-hidden rounded-2xl border bg-white"><div className="overflow-x-auto"><table className="w-full min-w-190 text-left text-sm"><thead className="bg-slate-50"><tr><th className="p-4">Token UUID</th><th className="p-4">Status</th><th className="p-4">Bound device</th><th className="p-4">Created</th><th className="p-4">Expires</th><th className="p-4">Action</th></tr></thead><tbody className="divide-y">{tokens.data.enrollment_tokens.map((token) => <tr key={token.token_uuid}><td className="p-4 font-mono text-xs">{token.token_uuid}</td><td className="p-4">{token.status}</td><td className="p-4 font-mono text-xs">{token.bound_device_uuid ?? 'Any device'}</td><td className="p-4">{formatDate(token.created_at)}</td><td className="p-4">{formatDate(token.expires_at)}</td><td className="p-4">{token.status === 'active' && hasPermission('enrollment_token.revoke') ? <button type="button" onClick={() => { setReason(''); setError(''); setRevokeTarget(token) }} className="font-semibold text-red-700">Revoke</button> : <span className="text-slate-400">Unavailable</span>}</td></tr>)}</tbody></table></div><Pagination value={tokens.data.pagination} onPage={setPage} /></div>}
    <ActionDialog open={issueOpen} onOpenChange={(value) => { setIssueOpen(value); if (!value) { setIssued(null); setCopied(false) } }} title="Issue enrollment token" description="The pairing token is shown only in this dialog and is never stored by the frontend." submitLabel={issued ? undefined : 'Issue token'} closeLabel={issued ? 'Close' : 'Cancel'} busy={issue.isPending} onSubmit={submitIssue}>
      {error && <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-800">{error}</div>}{issued ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4"><p className="text-sm font-semibold">Pairing token</p><p className="mt-2 break-all font-mono text-lg">{issued.pairing_token}</p><p className="mt-2 text-xs">Expires {formatDate(issued.expires_at)}. Copy it now, then close this dialog.</p><button type="button" onClick={() => void navigator.clipboard.writeText(issued.pairing_token).then(() => setCopied(true)).catch(() => setError('Copy failed. Select and copy the token manually.'))} className="mt-3 text-sm font-semibold underline">{copied ? 'Copied' : 'Copy token'}</button></div> : <><label className="block text-sm font-medium">Reason<input required maxLength={512} value={reason} onChange={(event) => setReason(event.target.value)} className="mt-2 w-full rounded-lg border px-3 py-2" /></label><label className="block text-sm font-medium">Bind to device UUID (optional)<input value={boundDevice} onChange={(event) => setBoundDevice(event.target.value)} className="mt-2 w-full rounded-lg border px-3 py-2" /></label></>}
    </ActionDialog>
    <ActionDialog open={Boolean(revokeTarget)} onOpenChange={(value) => !value && setRevokeTarget(null)} title="Revoke enrollment token" description="The pairing credential will no longer be accepted." submitLabel="Revoke token" busy={revoke.isPending} destructive onSubmit={submitRevoke}>{error && <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-800">{error}</div>}<label className="block text-sm font-medium">Reason<input required maxLength={512} value={reason} onChange={(event) => setReason(event.target.value)} className="mt-2 w-full rounded-lg border px-3 py-2" /></label></ActionDialog>
  </section>
}
