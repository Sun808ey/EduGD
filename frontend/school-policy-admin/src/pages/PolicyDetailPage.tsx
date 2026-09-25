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
type RevisionForm = {
  allowedPackages: string
  blockedPackages: string
  defaultAction: 'allow' | 'block'
  domains: string
  wifiOnly: boolean
  disallowMobileNetworkConfiguration: boolean
  disallowTethering: boolean
  disallowUserVpn: boolean
  alwaysOnFilteringVpn: boolean
  vpnLockdownRequired: boolean
  disallowOutgoingCalls: boolean
  disallowSms: boolean
}

const split = (value: string) => value.split('\n').map((item) => item.trim()).filter(Boolean)
const asRecord = (value: unknown): Record<string, unknown> => value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
const asList = (value: unknown) => Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string').join('\n') : ''

export function PolicyDetailPage() {
  const { policyUuid = '' } = useParams()
  const [page, setPage] = useState(1)
  const [action, setAction] = useState<PolicyAction | null>(null)
  const [revisionForm, setRevisionForm] = useState<RevisionForm>({ allowedPackages: '', blockedPackages: '', defaultAction: 'allow', domains: '', wifiOnly: true, disallowMobileNetworkConfiguration: true, disallowTethering: true, disallowUserVpn: true, alwaysOnFilteringVpn: true, vpnLockdownRequired: true, disallowOutgoingCalls: true, disallowSms: true })
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
      if (!latest?.payload) throw new Error('A current policy revision is required.')
      return adminService.createPolicyRevision(policyUuid, buildRevisionPayload(latest.payload, revisionForm))
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
  const openRevision = () => {
    const payload = asRecord(latest?.payload)
    const mode = asRecord(Array.isArray(payload.modes) ? payload.modes[0] : undefined)
    const web = asRecord(payload.web_filter)
    const network = asRecord(payload.network_controls)
    const telephony = asRecord(payload.telephony_controls)
    setRevisionForm({
      allowedPackages: asList(mode.allowed_packages), blockedPackages: asList(mode.blocked_packages),
      defaultAction: web.default_action === 'block' ? 'block' : 'allow',
      domains: Array.isArray(web.rules) ? web.rules.map((rule) => asRecord(rule).domain).filter((domain): domain is string => typeof domain === 'string').join('\n') : '',
      wifiOnly: network.wifi_only !== false, disallowMobileNetworkConfiguration: network.disallow_mobile_network_configuration !== false,
      disallowTethering: network.disallow_tethering !== false, disallowUserVpn: network.disallow_user_vpn !== false,
      alwaysOnFilteringVpn: network.always_on_filtering_vpn !== false, vpnLockdownRequired: network.vpn_lockdown_required !== false,
      disallowOutgoingCalls: telephony.disallow_outgoing_calls !== false, disallowSms: telephony.disallow_sms !== false,
    })
    setError(''); setAction('revision')
  }
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
      {action === 'revision' ? <RevisionFields value={revisionForm} onChange={setRevisionForm} /> : <label className="block text-sm font-medium text-slate-700">Reason<input required maxLength={512} value={reason} onChange={(event) => setReason(event.target.value)} className="mt-2 w-full rounded-lg border px-3 py-2" /></label>}
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    </ActionDialog>
  </section>
}

function Info({ label, value }: { label: string; value: string }) { return <div className="rounded-xl border bg-white p-4"><dt className="text-sm text-slate-500">{label}</dt><dd className="mt-1 font-semibold">{value}</dd></div> }

function buildRevisionPayload(source: Record<string, unknown>, form: RevisionForm): Record<string, unknown> {
  const modes = Array.isArray(source.modes) ? source.modes.map((item) => asRecord(item)) : []
  const first = modes[0] ?? {}
  const rules = split(form.domains).map((domain, index) => ({ rule_id: `rule_${index + 1}`, domain, include_subdomains: true, action: form.defaultAction === 'block' ? 'allow' : 'block', reason: 'School policy' }))
  return {
    ...source,
    modes: [{ ...first, allowed_packages: [...new Set(split(form.allowedPackages))], blocked_packages: [...new Set(split(form.blockedPackages))] }, ...modes.slice(1)],
    web_filter: { default_action: form.defaultAction, rules },
    network_controls: { wifi_only: form.wifiOnly, disallow_mobile_network_configuration: form.disallowMobileNetworkConfiguration, disallow_tethering: form.disallowTethering, disallow_user_vpn: form.disallowUserVpn, always_on_filtering_vpn: form.alwaysOnFilteringVpn, vpn_lockdown_required: form.vpnLockdownRequired },
    telephony_controls: { disallow_outgoing_calls: form.disallowOutgoingCalls, disallow_sms: form.disallowSms, preserve_emergency_calls: true },
  }
}

function RevisionFields({ value, onChange }: { value: RevisionForm; onChange: (value: RevisionForm) => void }) {
  const update = <K extends keyof RevisionForm>(key: K, next: RevisionForm[K]) => onChange({ ...value, [key]: next })
  return <div className="space-y-4"><p className="text-sm text-slate-600">Update structured policy controls. Application and domain values are entered one per line; the server performs final canonical validation.</p><label className="block text-sm font-medium">Allowed educational packages<textarea required value={value.allowedPackages} onChange={(event) => update('allowedPackages', event.target.value)} className="input mt-2 min-h-24" /></label><label className="block text-sm font-medium">Suspended packages<textarea value={value.blockedPackages} onChange={(event) => update('blockedPackages', event.target.value)} className="input mt-2 min-h-24" /></label><div className="grid gap-4 sm:grid-cols-2"><label className="block text-sm font-medium">Web default action<select value={value.defaultAction} onChange={(event) => update('defaultAction', event.target.value as 'allow' | 'block')} className="input mt-2"><option value="allow">Allow by default</option><option value="block">Block by default</option></select></label><label className="block text-sm font-medium">Domain rules<textarea value={value.domains} onChange={(event) => update('domains', event.target.value)} className="input mt-2 min-h-24" /></label></div><div className="grid gap-3 sm:grid-cols-2">{(['wifiOnly', 'disallowMobileNetworkConfiguration', 'disallowTethering', 'disallowUserVpn', 'alwaysOnFilteringVpn', 'vpnLockdownRequired', 'disallowOutgoingCalls', 'disallowSms'] as const).map((key) => <label key={key} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={value[key]} onChange={(event) => update(key, event.target.checked)} />{key.replaceAll(/([A-Z])/g, ' $1')}</label>)}</div></div>
}
