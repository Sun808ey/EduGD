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
import { AndroidProvisioningQrDialog } from '@/components/devices/AndroidProvisioningQrDialog'

export function EnrollmentTokensPanel() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [issueOpen, setIssueOpen] = useState(false)
  const [revokeTarget, setRevokeTarget] = useState<EnrollmentToken | null>(null)
  const [reason, setReason] = useState('')
  const [boundDevice, setBoundDevice] = useState('')
  const [policyRevision, setPolicyRevision] = useState('')
  const [issued, setIssued] = useState<IssuedEnrollmentToken | null>(null)
  const [qrOpen, setQrOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState('')
  const { hasPermission } = useAuth()
  const cache = useQueryClient()
  const tokens = useQuery({ queryKey: ['enrollment-tokens', page, status], queryFn: ({ signal }) => adminService.listEnrollmentTokens({ page, perPage: 25 }, status || undefined, signal) })
  const school = useQuery({ queryKey: ['school'], queryFn: ({ signal }) => adminService.getSchool(signal), enabled: issueOpen })
  const policies = useQuery({ queryKey: ['active-policies'], queryFn: ({ signal }) => adminService.listAllPolicies(signal), enabled: issueOpen })
  const devices = useQuery({ queryKey: ['devices-for-enrollment'], queryFn: ({ signal }) => adminService.listDevices({ page: 1, perPage: 100 }, 'active', signal), enabled: issueOpen })
  const issue = useMutation({
    mutationFn: () => adminService.issueEnrollmentToken({ reason: reason.trim(), school_uuid: school.data!.school_uuid, policy_revision_uuid: policyRevision, bound_device_uuid: boundDevice || undefined }),
    onSuccess: async (result) => { setIssued(result); setReason(''); setBoundDevice(''); setPolicyRevision(''); await cache.invalidateQueries({ queryKey: ['enrollment-tokens'] }) },
    onError: (caught) => setError(errorMessage(caught)),
  })
  const revoke = useMutation({ mutationFn: () => adminService.revokeEnrollmentToken(revokeTarget!.token_uuid, reason.trim()), onSuccess: async () => { setRevokeTarget(null); setReason(''); await cache.invalidateQueries({ queryKey: ['enrollment-tokens'] }) }, onError: (caught) => setError(errorMessage(caught)) })
  const eligiblePolicies = policies.data?.filter((policy) => policy.latest_revision) ?? []
  const readyToIssue = Boolean(school.data && policyRevision && reason.trim())
  function resetIssue() { setIssued(null); setQrOpen(false); setCopied(false); setReason(''); setBoundDevice(''); setPolicyRevision(''); setError('') }
  function submitIssue(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (readyToIssue) issue.mutate() }
  function submitRevoke(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (reason.trim() && revokeTarget) revoke.mutate() }

  return <section className="space-y-4"><header className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-xl font-semibold">Enrollment tokens</h2><p className="mt-1 text-sm text-slate-600">Prepare an approved school-owned device for EDUGD management.</p></div>{hasPermission('enrollment_token.issue') && <button type="button" onClick={() => { resetIssue(); setIssueOpen(true) }} className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white">Create enrollment token</button>}</header>
    <label className="block max-w-xs text-sm font-medium">Status<select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }} className="mt-2 h-10 w-full rounded-lg border bg-white px-3"><option value="">All statuses</option><option value="active">Active</option><option value="consumed">Consumed</option><option value="revoked">Revoked</option><option value="expired">Expired</option><option value="locked">Locked</option></select></label>
    {tokens.isLoading && <LoadingState label="Loading enrollment tokens…" />}{tokens.isError && <ErrorState message="Enrollment tokens are temporarily unavailable." retry={() => void tokens.refetch()} />}
    {tokens.data && <div className="overflow-hidden rounded-2xl border bg-white"><div className="overflow-x-auto"><table className="w-full min-w-240 text-left text-sm"><thead className="bg-slate-50"><tr><th className="p-4">Status</th><th className="p-4">Policy attached</th><th className="p-4">Device</th><th className="p-4">Created by</th><th className="p-4">Created</th><th className="p-4">Expires</th><th className="p-4">Action</th></tr></thead><tbody className="divide-y">{tokens.data.enrollment_tokens.map((token) => <tr key={token.token_uuid}><td className="p-4">{token.status}</td><td className="p-4">{token.policy_name ? `${token.policy_name} v${token.policy_version}` : 'Legacy token'}</td><td className="p-4 font-mono text-xs">{token.consumed_by_device_uuid ?? token.bound_device_uuid ?? 'Any device'}</td><td className="p-4">{token.issued_by_name ?? token.issued_by ?? 'Unavailable'}</td><td className="p-4">{formatDate(token.created_at)}</td><td className="p-4">{formatDate(token.expires_at)}</td><td className="p-4">{token.status === 'active' && hasPermission('enrollment_token.revoke') ? <button type="button" onClick={() => { setReason(''); setError(''); setRevokeTarget(token) }} className="font-semibold text-red-700">Revoke</button> : <span className="text-slate-400">Unavailable</span>}</td></tr>)}</tbody></table></div><Pagination value={tokens.data.pagination} onPage={setPage} /></div>}
    <ActionDialog open={issueOpen} onOpenChange={(value) => { setIssueOpen(value); if (!value) resetIssue() }} title="Create enrollment token" description="The pairing token is shown only once and is never stored by the frontend." submitLabel="Create token" closeLabel="Cancel" busy={issue.isPending} onSubmit={submitIssue}>
      {error && <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-800">{error}</div>}
      {school.isLoading || policies.isLoading || devices.isLoading ? <LoadingState label="Loading school, policies, and devices…" /> : <div className="space-y-4"><p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">Use this code only on a school-owned device approved for EDUGD. Do not use it on a personal learner device.</p>{!school.data ? <p role="alert" className="text-sm text-red-700">Register the school before creating an enrollment token.</p> : <><label className="block text-sm font-medium">School<select disabled value={school.data.school_uuid} className="mt-2 h-10 w-full rounded-lg border bg-slate-50 px-3"><option value={school.data.school_uuid}>{school.data.name}</option></select></label><label className="block text-sm font-medium">Policy template<select required value={policyRevision} onChange={(event) => setPolicyRevision(event.target.value)} className="mt-2 h-10 w-full rounded-lg border bg-white px-3"><option value="">Select a policy template</option>{eligiblePolicies.map((policy) => <option key={policy.latest_revision!.revision_uuid} value={policy.latest_revision!.revision_uuid}>{policy.name} v{policy.latest_revision!.version}</option>)}</select></label>{eligiblePolicies.length === 0 && <p role="alert" className="text-sm text-red-700">Create and activate a policy template before creating a token.</p>}<label className="block text-sm font-medium">Approved school-owned device (optional)<select value={boundDevice} onChange={(event) => setBoundDevice(event.target.value)} className="mt-2 h-10 w-full rounded-lg border bg-white px-3"><option value="">Use on a new factory-reset device</option>{devices.data?.devices.map((device) => <option key={device.device_uuid} value={device.device_uuid}>{device.asset_number ?? device.device_uuid} — {device.manufacturer ?? 'Unknown'} {device.model ?? ''}</option>)}</select></label><label className="block text-sm font-medium">Reason<input required maxLength={512} value={reason} onChange={(event) => setReason(event.target.value)} className="mt-2 w-full rounded-lg border px-3 py-2" /></label></>}</div>}
    </ActionDialog>{issued && <ActionDialog open onOpenChange={(value) => !value && resetIssue()} title="Enrollment token ready" description={`${issued.policy_name} v${issued.policy_version} is attached to this short-lived token.`} closeLabel="Close" busy={false} onSubmit={(event) => event.preventDefault()}><div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4"><p className="text-sm font-semibold">Pairing token</p><p className="mt-2 break-all font-mono text-lg">{issued.pairing_token}</p><p className="mt-2 text-xs">Expires {formatDate(issued.expires_at)}. Use it once, then close this dialog.</p><div className="mt-3 flex flex-wrap gap-4"><button type="button" onClick={() => void navigator.clipboard.writeText(issued.pairing_token).then(() => setCopied(true)).catch(() => setError('Copy failed. Select and copy the token manually.'))} className="text-sm font-semibold underline">{copied ? 'Copied' : 'Copy token'}</button><button type="button" onClick={() => setQrOpen(true)} className="text-sm font-semibold text-emerald-800 underline">Generate QR</button></div></div></ActionDialog>}{issued && <AndroidProvisioningQrDialog issued={issued} open={qrOpen} onOpenChange={setQrOpen} />}
    <ActionDialog open={Boolean(revokeTarget)} onOpenChange={(value) => !value && setRevokeTarget(null)} title="Revoke enrollment token" description="The pairing credential will no longer be accepted." submitLabel="Revoke token" busy={revoke.isPending} destructive onSubmit={submitRevoke}>{error && <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-800">{error}</div>}<label className="block text-sm font-medium">Reason<input required maxLength={512} value={reason} onChange={(event) => setReason(event.target.value)} className="mt-2 w-full rounded-lg border px-3 py-2" /></label></ActionDialog>
  </section>
}
