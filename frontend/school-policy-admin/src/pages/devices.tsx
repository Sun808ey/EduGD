import { Laptop, Plus, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { adminService } from '@/services/admin.service'
import type { DeviceSummary, PolicySummary } from '@/types/api'

export function DevicesPage() {
	const [devices, setDevices] = useState<DeviceSummary[]>([])
	const [policies, setPolicies] = useState<PolicySummary[]>([])
	const [query, setQuery] = useState('')
	const [status, setStatus] = useState('all')
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState('')
	const [enrollOpen, setEnrollOpen] = useState(false)
	const [reason, setReason] = useState('')
	const [pairingToken, setPairingToken] = useState('')
	const [submitting, setSubmitting] = useState(false)
	const [selectedDevice, setSelectedDevice] = useState<DeviceSummary | null>(null)
	const [selectedRevision, setSelectedRevision] = useState('')

	useEffect(() => { Promise.all([adminService.listDevices(), adminService.listPolicies()]).then(([deviceData, policyData]) => { setDevices(deviceData.devices); setPolicies(policyData.policies) }).catch(() => setError('Devices are temporarily unavailable.')).finally(() => setLoading(false)) }, [])

	const filteredDevices = devices.filter((device) => {
		const matchesQuery = device.device_uuid.toLowerCase().includes(query.toLowerCase())
		return matchesQuery && (status === 'all' || device.status === status)
	})

	async function issueToken(event: React.FormEvent<HTMLFormElement>) {
		event.preventDefault()
		setSubmitting(true)
		setError('')
		try {
			const token = await adminService.issueEnrollmentToken(reason.trim())
			setPairingToken(token.pairing_token)
			setReason('')
		} catch {
			setError('Enrollment token could not be issued. Check your permission and try again.')
		} finally {
			setSubmitting(false)
		}
	}

	async function updateAssignment(event: React.FormEvent<HTMLFormElement>) {
		event.preventDefault()
		if (!selectedDevice || !selectedRevision) return
		setSubmitting(true)
		setError('')
		try {
			const result = await adminService.assignPolicy(selectedDevice.device_uuid, selectedRevision, reason.trim())
			setDevices((current) => current.map((device) => device.device_uuid === selectedDevice.device_uuid ? { ...device, active_policy_assignment: result.assignment } : device))
			setSelectedDevice(null)
			setReason('')
		} catch {
			setError('Policy assignment failed. Check your permission and try again.')
		} finally {
			setSubmitting(false)
		}
	}

	async function clearAssignment() {
		if (!selectedDevice || !selectedDevice.active_policy_assignment) return
		setSubmitting(true)
		setError('')
		try {
			await adminService.clearPolicy(selectedDevice.device_uuid, reason.trim())
			setDevices((current) => current.map((device) => device.device_uuid === selectedDevice.device_uuid ? { ...device, active_policy_assignment: null } : device))
			setSelectedDevice(null)
			setReason('')
		} catch {
			setError('Policy clear failed. Check your permission and try again.')
		} finally {
			setSubmitting(false)
		}
	}

	return <><ResourcePage title="Devices" description="Monitor enrollment, health, and policy assignment for every managed device." action="Enroll device" onAction={() => { setPairingToken(''); setEnrollOpen(true) }} onManage={(device) => { setSelectedDevice(device); setSelectedRevision(device.active_policy_assignment?.policy_revision_uuid ?? '') }} icon={Laptop} count={devices.length} loading={loading} error={error} empty={devices.length === 0} query={query} onQueryChange={setQuery} status={status} onStatusChange={setStatus} rows={filteredDevices} />{enrollOpen && <div className="fixed inset-0 z-30 grid place-items-center bg-slate-950/40 p-4"><div role="dialog" aria-modal="true" aria-labelledby="enroll-title" className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"><div className="flex items-start justify-between gap-4"><div><h2 id="enroll-title" className="text-lg font-semibold">Issue enrollment token</h2><p className="mt-1 text-sm text-slate-500">Generate a pairing token for a new device.</p></div><button type="button" aria-label="Close dialog" onClick={() => setEnrollOpen(false)} className="text-sm text-slate-500 hover:text-slate-900">Close</button></div>{pairingToken ? <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-emerald-800">Pairing token</p><p className="mt-2 break-all font-mono text-lg text-emerald-950">{pairingToken}</p><p className="mt-2 text-xs text-emerald-800">Copy this token into the device enrollment flow. It is shown only after issuance.</p></div> : <form onSubmit={issueToken} className="mt-6 space-y-4"><label className="block text-sm font-medium text-slate-700" htmlFor="enrollment-reason">Reason<input id="enrollment-reason" required value={reason} onChange={(event) => setReason(event.target.value)} placeholder="New classroom device" className="mt-2 h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-emerald-500" /></label><div className="flex justify-end gap-3"><button type="button" onClick={() => setEnrollOpen(false)} className="rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">Cancel</button><button type="submit" disabled={submitting} className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{submitting ? 'Issuing...' : 'Issue token'}</button></div></form>}</div></div>}{selectedDevice && <div className="fixed inset-0 z-30 grid place-items-center bg-slate-950/40 p-4"><form onSubmit={updateAssignment} role="dialog" aria-modal="true" aria-labelledby="assignment-title" className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"><div className="flex items-start justify-between gap-4"><div><h2 id="assignment-title" className="text-lg font-semibold">Manage device policy</h2><p className="mt-1 break-all text-sm text-slate-500">{selectedDevice.device_uuid}</p></div><button type="button" aria-label="Close dialog" onClick={() => setSelectedDevice(null)} className="text-sm text-slate-500 hover:text-slate-900">Close</button></div><label className="mt-6 block text-sm font-medium text-slate-700" htmlFor="policy-revision">Policy revision<select id="policy-revision" required value={selectedRevision} onChange={(event) => setSelectedRevision(event.target.value)} className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-emerald-500"><option value="">Select a revision</option>{policies.filter((policy) => policy.latest_revision).map((policy) => <option key={policy.latest_revision!.revision_uuid} value={policy.latest_revision!.revision_uuid}>{policy.name} v{policy.latest_revision!.version}</option>)}</select></label><label className="mt-4 block text-sm font-medium text-slate-700" htmlFor="assignment-reason">Reason<input id="assignment-reason" required value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Apply classroom policy" className="mt-2 h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-emerald-500" /></label><div className="mt-6 flex justify-between gap-3"><button type="button" disabled={!selectedDevice.active_policy_assignment || submitting || !reason.trim()} onClick={() => void clearAssignment()} className="rounded-xl px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-40">Clear policy</button><div className="flex gap-3"><button type="button" onClick={() => setSelectedDevice(null)} className="rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">Cancel</button><button type="submit" disabled={submitting} className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{submitting ? 'Assigning...' : 'Assign policy'}</button></div></div></form></div>}</>
}

function ResourcePage({ title, description, action, onAction, onManage, icon: Icon, count, loading, error, empty, query, onQueryChange, status, onStatusChange, rows }: { title: string; description: string; action: string; onAction: () => void; onManage: (device: DeviceSummary) => void; icon: typeof Laptop; count: number; loading: boolean; error: string; empty: boolean; query: string; onQueryChange: (value: string) => void; status: string; onStatusChange: (value: string) => void; rows: DeviceSummary[] }) {
	return <section className="space-y-8"><header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Workspace</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">{title}</h1><p className="mt-2 max-w-2xl text-sm text-slate-600">{description}</p></div><button type="button" onClick={onAction} className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 text-sm font-semibold text-white hover:bg-slate-800"><Plus className="size-4" />{action}</button></header>{error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}<div className="rounded-2xl border border-slate-200 bg-white shadow-sm"><div className="flex flex-col gap-3 border-b border-slate-200 p-4 lg:flex-row lg:items-center lg:justify-between"><div className="relative max-w-sm flex-1"><Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" /><input aria-label={`Search ${title.toLowerCase()}`} value={query} onChange={(event) => onQueryChange(event.target.value)} placeholder={`Search ${title.toLowerCase()}`} className="h-10 w-full rounded-xl border border-slate-200 pl-9 pr-3 text-sm outline-none focus:border-emerald-500" /></div><div className="flex items-center gap-3"><select aria-label="Filter by status" value={status} onChange={(event) => onStatusChange(event.target.value)} className="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-emerald-500"><option value="all">All statuses</option><option value="active">Active</option><option value="suspended">Suspended</option><option value="retired">Retired</option></select><span className="text-xs font-medium text-slate-500">{loading ? 'Loading...' : `${rows.length} of ${count}`}</span></div></div>{!loading && !empty && <div className="overflow-x-auto"><table className="w-full min-w-170 text-left text-sm"><thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3 font-semibold">Device</th><th className="px-5 py-3 font-semibold">Status</th><th className="px-5 py-3 font-semibold">Platform</th><th className="px-5 py-3 font-semibold">Last sync</th><th className="px-5 py-3 font-semibold">Policy</th><th className="px-5 py-3 font-semibold">Actions</th></tr></thead><tbody className="divide-y divide-slate-100">{rows.map((device) => <tr key={device.device_uuid} className="hover:bg-slate-50"><td className="px-5 py-4 font-medium text-slate-900">{device.device_uuid}</td><td className="px-5 py-4"><span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">{device.status}</span></td><td className="px-5 py-4 text-slate-600">Android {device.android_version ?? 'unknown'}</td><td className="px-5 py-4 text-slate-600">{device.last_sync_at ? new Date(device.last_sync_at).toLocaleString() : 'Never'}</td><td className="px-5 py-4 text-slate-600">{device.active_policy_assignment?.policy_name ?? 'Unassigned'}</td><td className="px-5 py-4"><button type="button" onClick={() => onManage(device)} className="text-sm font-semibold text-emerald-700 hover:text-emerald-900">Manage</button></td></tr>)}</tbody></table></div>}{!loading && !empty && rows.length === 0 && <div className="p-10 text-center text-sm text-slate-500">No devices match the current filters.</div>}{empty && !loading && <div className="grid min-h-64 place-items-center p-8 text-center"><div><div className="mx-auto grid size-12 place-items-center rounded-2xl bg-slate-100 text-slate-500"><Icon className="size-6" /></div><h2 className="mt-4 font-semibold">No {title.toLowerCase()} yet</h2><p className="mt-1 text-sm text-slate-500">Create your first record to start managing this workspace.</p></div></div>}</div></section>
}
