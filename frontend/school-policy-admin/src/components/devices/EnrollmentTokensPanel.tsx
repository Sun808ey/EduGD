import { KeyRound, RotateCcw } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { adminService } from '@/services/admin.service'
import type { EnrollmentTokenSummary } from '@/types/api'

export function EnrollmentTokensPanel() {
  const [tokens, setTokens] = useState<EnrollmentTokenSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [revokeTarget, setRevokeTarget] = useState<EnrollmentTokenSummary | null>(null)
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)

  function loadTokens() {
    setLoading(true)
    adminService.listEnrollmentTokens().then((data) => setTokens(data.enrollment_tokens)).catch(() => setError('Enrollment tokens are temporarily unavailable.')).finally(() => setLoading(false))
  }

  useEffect(() => {
    adminService.listEnrollmentTokens().then((data) => setTokens(data.enrollment_tokens)).catch(() => setError('Enrollment tokens are temporarily unavailable.')).finally(() => setLoading(false))
  }, [])

  async function revoke(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!revokeTarget || !reason.trim()) return
    setSubmitting(true)
    setError('')
    try {
      await adminService.revokeEnrollmentToken(revokeTarget.token_uuid, reason.trim())
      setTokens((current) => current.map((token) => token.token_uuid === revokeTarget.token_uuid ? { ...token, status: 'revoked', revoked_at: new Date().toISOString() } : token))
      setRevokeTarget(null)
      setReason('')
    } catch {
      setError('The enrollment token could not be revoked.')
    } finally {
      setSubmitting(false)
    }
  }

  return <section className="rounded-2xl border border-slate-200 bg-white shadow-sm"><div className="flex items-center justify-between border-b border-slate-200 p-5"><div className="flex items-center gap-3"><KeyRound className="size-5 text-slate-500" /><div><h2 className="font-semibold">Enrollment tokens</h2><p className="mt-1 text-sm text-slate-500">Review active pairing credentials.</p></div></div><button type="button" aria-label="Refresh enrollment tokens" onClick={loadTokens} className="grid size-9 place-items-center rounded-lg text-slate-500 hover:bg-slate-100"><RotateCcw className="size-4" /></button></div>{error && <div role="alert" className="m-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}{loading ? <div className="p-8 text-center text-sm text-slate-500">Loading enrollment tokens...</div> : tokens.length === 0 ? <div className="p-8 text-center text-sm text-slate-500">No enrollment tokens recorded.</div> : <div className="overflow-x-auto"><table className="w-full min-w-170 text-left text-sm"><thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3 font-semibold">Token</th><th className="px-5 py-3 font-semibold">Status</th><th className="px-5 py-3 font-semibold">Created</th><th className="px-5 py-3 font-semibold">Expires</th><th className="px-5 py-3 font-semibold">Action</th></tr></thead><tbody className="divide-y divide-slate-100">{tokens.map((token) => <tr key={token.token_uuid}><td className="max-w-48 truncate px-5 py-4 font-mono text-xs text-slate-600">{token.token_uuid}</td><td className="px-5 py-4"><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">{token.status}</span></td><td className="px-5 py-4 text-slate-600">{token.created_at ? new Date(token.created_at).toLocaleString() : 'Unknown'}</td><td className="px-5 py-4 text-slate-600">{token.expires_at ? new Date(token.expires_at).toLocaleString() : 'Unknown'}</td><td className="px-5 py-4">{token.status === 'active' ? <button type="button" onClick={() => setRevokeTarget(token)} className="text-sm font-semibold text-red-700 hover:text-red-900">Revoke</button> : <span className="text-xs text-slate-400">Unavailable</span>}</td></tr>)}</tbody></table></div>}{revokeTarget && <div className="fixed inset-0 z-40 grid place-items-center bg-slate-950/40 p-4"><form onSubmit={revoke} role="dialog" aria-modal="true" aria-labelledby="revoke-token-title" className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"><h2 id="revoke-token-title" className="text-lg font-semibold">Revoke enrollment token</h2><p className="mt-2 break-all text-xs text-slate-500">{revokeTarget.token_uuid}</p><label htmlFor="revoke-reason" className="mt-6 block text-sm font-medium text-slate-700">Reason<input id="revoke-reason" required value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Token no longer needed" className="mt-2 h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-emerald-500" /></label><div className="mt-6 flex justify-end gap-3"><button type="button" onClick={() => setRevokeTarget(null)} className="rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">Cancel</button><button type="submit" disabled={submitting} className="rounded-xl bg-red-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{submitting ? 'Revoking...' : 'Revoke token'}</button></div></form></div>}</section>
}
