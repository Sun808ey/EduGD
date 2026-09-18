import { Activity, AlertTriangle, Laptop, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { adminService } from '@/services/admin.service'

const stats = [
	{ label: 'Enrolled devices', value: '128', detail: '+8 this month', icon: Laptop, tone: 'sky' },
	{ label: 'Active policies', value: '24', detail: 'All schools covered', icon: ShieldCheck, tone: 'emerald' },
	{ label: 'Open alerts', value: '3', detail: 'Needs attention', icon: AlertTriangle, tone: 'amber' },
]

export function DashboardPage() {
	const [counts, setCounts] = useState({ devices: 0, policies: 0, alerts: 0 })
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState('')

	useEffect(() => {
		Promise.all([adminService.listDevices(), adminService.listPolicies(), adminService.listAuditEvents()])
			.then(([devices, policies, events]) => setCounts({ devices: devices.pagination.total, policies: policies.pagination.total, alerts: events.audit_events.filter((event) => event.failure_class).length }))
			.catch(() => setError('Dashboard data is temporarily unavailable.'))
			.finally(() => setLoading(false))
	}, [])

	const values = [counts.devices, counts.policies, counts.alerts]

	return (
		<section className="space-y-8">
			<PageHeading eyebrow="Overview" title="Good morning, administrator" description="A quick read on device health and policy coverage across your schools." />
			<div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
				{stats.map(({ label, detail, icon: Icon, tone }, index) => (
					<article key={label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
						<div className="flex items-start justify-between">
							<div><p className="text-sm text-slate-500">{label}</p><p className="mt-3 text-3xl font-semibold tracking-tight">{loading ? '...' : values[index]}</p></div>
							<div className={`grid size-10 place-items-center rounded-xl ${tone === 'sky' ? 'bg-sky-50 text-sky-700' : tone === 'emerald' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}><Icon className="size-5" aria-hidden="true" /></div>
						</div>
						{error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
						<p className="mt-5 text-xs font-medium text-slate-500">{detail}</p>
					</article>
				))}
			</div>
			<div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
				<div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><div className="flex items-center justify-between"><div><h3 className="font-semibold">Policy sync activity</h3><p className="mt-1 text-sm text-slate-500">Recent changes across managed devices</p></div><Activity className="size-5 text-emerald-600" /></div><div className="mt-8 grid h-40 place-items-center rounded-xl border border-dashed border-slate-200 bg-slate-50 text-sm text-slate-500">Activity data will appear here</div></div>
				<div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><h3 className="font-semibold">Attention needed</h3><p className="mt-1 text-sm text-slate-500">Items that may need review</p><div className="mt-8 rounded-xl bg-amber-50 p-4 text-sm text-amber-900">No critical incidents reported.</div></div>
			</div>
		</section>
	)
}

function PageHeading({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
	return <header><p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">{eyebrow}</p><h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">{title}</h1><p className="mt-2 max-w-2xl text-sm text-slate-600">{description}</p></header>
}
