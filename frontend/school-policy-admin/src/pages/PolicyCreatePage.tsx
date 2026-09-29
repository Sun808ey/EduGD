import { useState, type ReactNode } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { adminService } from '@/services/admin.service'
import { errorMessage } from '@/services/errors'

const split = (value: string) => value.split('\n').map((item) => item.trim()).filter(Boolean)

export function PolicyCreatePage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [emergency, setEmergency] = useState('')
  const [allowed, setAllowed] = useState('')
  const [blocked, setBlocked] = useState('')
  const [limit, setLimit] = useState('')
  const [reset, setReset] = useState('0')
  const [domains, setDomains] = useState('')
  const [webDefaultAction, setWebDefaultAction] = useState<'allow' | 'block'>('allow')
  const [includeSubdomains, setIncludeSubdomains] = useState(true)
  const [wifiOnly, setWifiOnly] = useState(true)
  const [disallowMobileNetworkConfiguration, setDisallowMobileNetworkConfiguration] = useState(true)
  const [disallowTethering, setDisallowTethering] = useState(true)
  const [disallowUserVpn, setDisallowUserVpn] = useState(true)
  const [alwaysOnFilteringVpn, setAlwaysOnFilteringVpn] = useState(true)
  const [vpnLockdownRequired, setVpnLockdownRequired] = useState(true)
  const [disallowOutgoingCalls, setDisallowOutgoingCalls] = useState(true)
  const [disallowSms, setDisallowSms] = useState(true)
  const [error, setError] = useState('')
  const allowedCount = split(allowed).length
  const blockedCount = split(blocked).length
  const domainCount = split(domains).length
  const mutation = useMutation({
    mutationFn: () => {
      const emergencyPackages = split(emergency)
      const payload = {
        schema_version: 3, timezone: 'Africa/Kampala', refresh_after_seconds: 3600,
        default_mode: 'learning', emergency_packages: emergencyPackages,
        required_capabilities: ['screen_time', 'web_filter', 'app_visibility'], minimum_dpc_version: 1,
        modes: [{ mode_id: 'learning', application_mode: 'allowlist', allowed_packages: [...new Set([...emergencyPackages, ...split(allowed)])], blocked_packages: split(blocked), lock_task_packages: [], user_restrictions: [], device_controls: { camera_disabled: false, screen_capture_disabled: false, unknown_sources_disabled: true, factory_reset_disabled: true, safe_boot_disabled: true, add_users_disabled: false, account_changes_disabled: false, usb_file_transfer_disabled: false } }, { mode_id: 'restricted', application_mode: 'allowlist', allowed_packages: emergencyPackages, blocked_packages: [], lock_task_packages: [], user_restrictions: [], device_controls: { camera_disabled: false, screen_capture_disabled: false, unknown_sources_disabled: true, factory_reset_disabled: true, safe_boot_disabled: true, add_users_disabled: false, account_changes_disabled: false, usb_file_transfer_disabled: false } }],
        schedules: [], screen_time: { daily_limit_minutes: Number(limit), reset_minute: Number(reset), exhausted_mode_id: 'restricted' },
        web_filter: { default_action: webDefaultAction, rules: split(domains).map((domain, index) => ({ rule_id: `rule_${index + 1}`, domain, include_subdomains: includeSubdomains, action: webDefaultAction === 'block' ? 'allow' : 'block', reason: 'School policy' })) },
        network_controls: { wifi_only: wifiOnly, disallow_mobile_network_configuration: disallowMobileNetworkConfiguration, disallow_tethering: disallowTethering, disallow_user_vpn: disallowUserVpn, always_on_filtering_vpn: alwaysOnFilteringVpn, vpn_lockdown_required: vpnLockdownRequired },
        telephony_controls: { disallow_outgoing_calls: disallowOutgoingCalls, disallow_sms: disallowSms, preserve_emergency_calls: true },
      }
      return adminService.createPolicy(name.trim(), payload)
    },
    onSuccess: (result) => navigate(`/policies/${result.policy_uuid}`),
    onError: (caught) => setError(errorMessage(caught)),
  })
  return <section className="mx-auto max-w-4xl space-y-8"><header><Link to="/policies" className="text-sm font-semibold text-emerald-700">← Policies</Link><p className="mt-5 text-xs font-bold uppercase tracking-[.16em] text-emerald-700">DPC v3 authoring</p><h1 className="mt-2 text-3xl font-semibold">Create an immutable policy</h1><p className="mt-2 text-sm text-slate-600">Review carefully. Saving creates revision 1 and the server validates the canonical DPC v3 contract.</p></header>
    <form className="grid gap-6" onSubmit={(event) => { event.preventDefault(); setError(''); mutation.mutate() }}>
      <Panel title="Policy identity"><Field label="Policy name"><input required value={name} onChange={(event) => setName(event.target.value)} className="input" maxLength={255} /></Field></Panel>
      <Panel title="Application modes"><p className="text-sm text-slate-600">One Android package name per line. The restricted mode retains only emergency packages after the daily allowance.</p><div className="grid gap-4 md:grid-cols-3"><Field label="Emergency packages"><textarea required value={emergency} onChange={(event) => setEmergency(event.target.value)} className="input min-h-36" /></Field><Field label="Learning allowlist"><textarea value={allowed} onChange={(event) => setAllowed(event.target.value)} className="input min-h-36" /></Field><Field label="Learning blocklist"><textarea value={blocked} onChange={(event) => setBlocked(event.target.value)} className="input min-h-36" /></Field></div></Panel>
      <Panel title="Daily screen time"><div className="grid gap-4 sm:grid-cols-2"><Field label="Daily active minutes"><input required type="number" min="1" max="1440" value={limit} onChange={(event) => setLimit(event.target.value)} className="input" /></Field><Field label="Kampala reset minute after midnight"><input required type="number" min="0" max="1439" value={reset} onChange={(event) => setReset(event.target.value)} className="input" /></Field></div></Panel>
      <Panel title="Web filtering"><p className="text-sm text-slate-600">Enter domains only, without paths, protocols, or query strings. Rules override the selected default action.</p><div className="grid gap-4 sm:grid-cols-2"><Field label="Default action"><select value={webDefaultAction} onChange={(event) => setWebDefaultAction(event.target.value as 'allow' | 'block')} className="input"><option value="allow">Allow by default</option><option value="block">Block by default</option></select></Field><label className="flex items-center gap-3 pt-7 text-sm font-medium text-slate-700"><input type="checkbox" checked={includeSubdomains} onChange={(event) => setIncludeSubdomains(event.target.checked)} /> Include subdomains in every rule</label></div><Field label={webDefaultAction === 'allow' ? 'Blocked domains' : 'Allowed domains'}><textarea value={domains} onChange={(event) => setDomains(event.target.value)} className="input mt-3 min-h-36" /></Field></Panel>
      <Panel title="Network and telephony restrictions"><p className="text-sm text-slate-600">These controls describe the certified device contract. Emergency calling remains preserved.</p><div className="grid gap-3 sm:grid-cols-2"><Toggle label="Wi-Fi only" checked={wifiOnly} onChange={setWifiOnly} /><Toggle label="Disallow mobile network configuration" checked={disallowMobileNetworkConfiguration} onChange={setDisallowMobileNetworkConfiguration} /><Toggle label="Disallow tethering" checked={disallowTethering} onChange={setDisallowTethering} /><Toggle label="Disallow user VPN" checked={disallowUserVpn} onChange={setDisallowUserVpn} /><Toggle label="Always-on filtering VPN" checked={alwaysOnFilteringVpn} onChange={setAlwaysOnFilteringVpn} /><Toggle label="VPN lockdown required" checked={vpnLockdownRequired} onChange={setVpnLockdownRequired} /><Toggle label="Disallow outgoing calls" checked={disallowOutgoingCalls} onChange={setDisallowOutgoingCalls} /><Toggle label="Disallow SMS" checked={disallowSms} onChange={setDisallowSms} /></div></Panel>
      {error && <p role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}
      <button disabled={mutation.isPending} className="w-fit rounded-full bg-emerald-700 px-6 py-3 font-semibold text-white disabled:opacity-60">{mutation.isPending ? 'Validating…' : 'Create immutable policy'}</button>
    </form><aside className="rounded-2xl border border-emerald-200 bg-[#eaf4e3] p-5 shadow-sm"><p className="text-xs font-bold uppercase tracking-[.16em] text-emerald-800">Policy preview</p><h2 className="mt-2 text-xl font-semibold">{name || 'Untitled policy'}</h2><dl className="mt-5 space-y-3 text-sm"><Summary label="Web default" value={webDefaultAction === 'allow' ? 'Allow' : 'Block'} /><Summary label="Allowed packages" value={String(allowedCount)} /><Summary label="Suspended packages" value={String(blockedCount)} /><Summary label="Domain rules" value={String(domainCount)} /><Summary label="Daily limit" value={limit ? `${limit} minutes` : 'Not set'} /><Summary label="Emergency calls" value="Preserved" /></dl><p className="mt-5 border-t border-emerald-200 pt-4 text-xs leading-5 text-slate-600">No DPC connection is required to author or save this policy. Device evidence appears after enrollment and check-in.</p></aside>
  </section>
}

function Panel({ title, children }: { title: string; children: ReactNode }) { return <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="text-lg font-semibold">{title}</h2><div className="mt-4">{children}</div></section> }
function Field({ label, children }: { label: string; children: ReactNode }) { return <label className="block text-sm font-medium text-slate-700"><span>{label}</span>{children}</label> }
function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) { return <label className="flex items-center gap-3 text-sm font-medium text-slate-700"><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />{label}</label> }
function Summary({ label, value }: { label: string; value: string }) { return <div className="flex items-center justify-between gap-3"><dt className="text-slate-600">{label}</dt><dd className="font-semibold text-slate-950">{value}</dd></div> }
