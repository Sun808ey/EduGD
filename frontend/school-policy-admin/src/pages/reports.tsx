import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { adminService } from '@/services/admin.service'
import { ErrorState, LoadingState } from '@/components/ui/AsyncState'
import { Pagination } from '@/components/ui/Pagination'
import { formatDate } from '@/lib/format'

export function ReportsPage() {
  const [page, setPage] = useState(1)
  const [deviceUuid, setDeviceUuid] = useState('')
  const [className, setClassName] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [exportError, setExportError] = useState(false)
  const devices = useQuery({ queryKey: ['report-devices'], queryFn: ({ signal }) => adminService.listDevices({ page: 1, perPage: 100 }, undefined, signal) })
  const filters = useMemo(() => ({ deviceUuid: deviceUuid || undefined, className: className.trim() || undefined, from: from || undefined, to: to || undefined }), [deviceUuid, className, from, to])
  const report = useQuery({ queryKey: ['violation-report', page, filters], queryFn: ({ signal }) => adminService.listViolationReports({ page, perPage: 25 }, filters, signal) })

  async function exportCsv() {
    setExportError(false)
    try {
      const blob = await adminService.exportViolationReport(filters)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = 'edugd-violations.csv'
      anchor.click()
      URL.revokeObjectURL(url)
    } catch {
      setExportError(true)
    }
  }

  return <section className="space-y-6"><header><h1 className="text-3xl font-semibold">Violation reports</h1><p className="mt-2 max-w-3xl text-sm text-slate-600">Review DPC-recorded policy blocks, kiosk bypass attempts, restricted-setting changes, web-filter blocks and enforcement failures. The report reads append-only device evidence and does not expose private device content.</p></header>
    <section className="grid gap-3 rounded-2xl border bg-white p-4 md:grid-cols-2 xl:grid-cols-5"><label className="text-sm font-medium xl:col-span-2">Device<select value={deviceUuid} onChange={(event) => { setDeviceUuid(event.target.value); setPage(1) }} className="mt-2 h-10 w-full rounded-lg border bg-white px-3"><option value="">All devices</option>{devices.data?.devices.map((device) => <option key={device.device_uuid} value={device.device_uuid}>{device.asset_number ?? device.device_uuid}</option>)}</select></label><label className="text-sm font-medium">Class<input value={className} onChange={(event) => { setClassName(event.target.value); setPage(1) }} placeholder="Senior Five" className="mt-2 h-10 w-full rounded-lg border px-3" /></label><label className="text-sm font-medium">From<input type="date" value={from} onChange={(event) => { setFrom(event.target.value); setPage(1) }} className="mt-2 h-10 w-full rounded-lg border px-3" /></label><label className="text-sm font-medium">To<input type="date" value={to} onChange={(event) => { setTo(event.target.value); setPage(1) }} className="mt-2 h-10 w-full rounded-lg border px-3" /></label><button type="button" onClick={() => void exportCsv()} className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white xl:col-span-5 xl:justify-self-start">Export filtered CSV</button></section>
    {devices.isError && <p className="text-sm text-amber-700">Device filter options are temporarily unavailable.</p>}
    {exportError && <p role="alert" className="text-sm text-red-700">The filtered CSV could not be exported. Please retry.</p>}
    {report.isLoading && <LoadingState label="Loading violation report…" />}{report.isError && <ErrorState message="Violation reports are temporarily unavailable." retry={() => void report.refetch()} />}
    {report.data && <div className="overflow-hidden rounded-2xl border bg-white"><div className="overflow-x-auto"><table className="w-full min-w-280 text-left text-sm"><thead className="bg-slate-50"><tr><th className="p-4">Occurred</th><th className="p-4">Device / class</th><th className="p-4">Violation</th><th className="p-4">Policy / rule</th><th className="p-4">Details</th><th className="p-4">Chain evidence</th></tr></thead><tbody className="divide-y">{report.data.violations.map((item) => <tr key={item.event_uuid}><td className="p-4 align-top whitespace-nowrap">{formatDate(item.occurred_at)}</td><td className="p-4 align-top"><div className="font-semibold">{item.asset_number ?? item.device_uuid}</div><div className="text-xs text-slate-500">{item.class_name ?? 'Class not recorded'}</div></td><td className="p-4 align-top"><div className="font-semibold">{item.violation_type}</div><div className="text-xs text-slate-500">{item.event_code} · {item.outcome}</div></td><td className="p-4 align-top">{item.policy_name ? `${item.policy_name} v${item.policy_version ?? '?'}` : 'Policy not linked'}<div className="text-xs text-slate-500">{item.rule_id ?? 'No rule ID'}</div></td><td className="p-4 align-top text-xs">{Object.entries(item.details).map(([key, value]) => <div key={key}><span className="font-semibold">{key}:</span> {String(value)}</div>)}</td><td className="p-4 align-top text-xs"><div>Sequence {item.sequence}</div><div className="font-mono text-slate-500">{item.event_hash.slice(0, 16)}…</div></td></tr>)}</tbody></table></div>{report.data.violations.length === 0 && <p className="p-8 text-center text-sm text-slate-500">No violations match these filters.</p>}<Pagination value={report.data.pagination} onPage={setPage} /></div>}
  </section>
}
