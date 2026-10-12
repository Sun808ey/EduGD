import { Activity, AlertTriangle, CheckCircle2, CircleAlert, Clock3, CloudOff, Laptop, ListTodo, LockKeyhole, ShieldCheck, Smartphone, TriangleAlert } from 'lucide-react'
import { useQueries } from '@tanstack/react-query'
import { Link as RouterLink } from 'react-router-dom'
import { Box, Button, Divider, Paper, Stack, Typography } from '@mui/material'
import { adminService } from '@/services/admin.service'
import { publicHealthService } from '@/services/public-health.service'
import { ErrorState, LoadingState } from '@/components/ui/AsyncState'
import { formatDate } from '@/lib/format'
import { useOfflineStatus } from '@/context/OfflineContext'

export function DashboardPage() {
  const { pendingCount } = useOfflineStatus()
  const results = useQueries({ queries: [
    { queryKey: ['dpc-summary'], queryFn: ({ signal }) => adminService.getDpcSummary(signal) },
    { queryKey: ['audit', 1, 'all'], queryFn: ({ signal }) => adminService.listAuditEvents({ page: 1, perPage: 10 }, undefined, signal) },
    { queryKey: ['health'], queryFn: ({ signal }) => publicHealthService.checkHealth(signal) },
    { queryKey: ['readiness'], queryFn: ({ signal }) => publicHealthService.checkReadiness(signal) },
    { queryKey: ['violations', 'recent'], queryFn: ({ signal }) => adminService.listViolationReports({ page: 1, perPage: 1 }, {}, signal) },
    { queryKey: ['school'], queryFn: ({ signal }) => adminService.getSchool(signal) },
  ] })
  const [summary, audit, health, readiness, violations, school] = results

  if (summary.isLoading || audit.isLoading) return <LoadingState label="Loading control room..." />
  if (summary.isError || audit.isError || !summary.data) {
    return <ErrorState message="Control-room data is temporarily unavailable." retry={() => { void summary.refetch(); void audit.refetch() }} />
  }

  const deviceOverview = [
    { label: 'Total registered devices', value: summary.data.managed_devices, icon: Laptop, tone: 'primary.main', detail: 'All device records held by EDUGD.' },
    { label: 'Enrolled devices', icon: Smartphone, tone: 'success.main' },
    { label: 'Awaiting provisioning', icon: Clock3, tone: 'warning.main' },
    { label: 'Compliant devices', icon: CheckCircle2, tone: 'success.main' },
    { label: 'Non-compliant devices', icon: CircleAlert, tone: 'error.main' },
    { label: 'Offline for review', icon: CloudOff, tone: 'warning.main' },
    { label: 'Devices marked missing', icon: TriangleAlert, tone: 'error.main' },
    { label: 'Pending commands', value: pendingCount, icon: ListTodo, tone: 'warning.main', detail: 'Local changes waiting for synchronisation.' },
    { label: 'Reported violations', value: violations.data?.pagination.total, icon: AlertTriangle, tone: 'error.main', detail: 'Append-only events received from the Android DPC.' },
  ]
  const policySignals = [
    { label: 'Active policy assignments', value: summary.data.active_v3_assignments, icon: ShieldCheck, tone: 'success.main' },
    { label: 'Block overrides', value: summary.data.active_block_overrides, icon: LockKeyhole, tone: 'warning.main' },
    { label: 'Enforcement failures', value: summary.data.enforcement_failures, icon: AlertTriangle, tone: 'error.main' },
  ]

  return <Stack spacing={3.5}>
    <Box component="header"><Typography variant="overline" sx={{ color: 'primary.main', fontWeight: 800, letterSpacing: '.14em' }}>EduGD control room</Typography><Typography component="h1" variant="h4" sx={{ mt: .25, fontWeight: 800 }}>School devices at a glance</Typography><Typography variant="body2" sx={{ mt: 1, fontWeight: 700 }}>{school.data?.name ?? 'School profile pending'}</Typography><Typography variant="body2" color="text.secondary">A privacy-limited view of school-owned devices, their policies and reported status.</Typography></Box>
    <Box><Typography component="h2" variant="h6" sx={{ mb: .5, fontWeight: 750 }}>School device overview</Typography><Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>Offline is a connection state, not a compliance result. EDUGD shows a metric only after the backend reports it.</Typography><Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))', xl: 'repeat(3, minmax(0, 1fr))' }, gap: 2 }}>{deviceOverview.map(({ label, value, icon: Icon, tone, detail }) => <Paper key={label} variant="outlined" sx={{ position: 'relative', p: 2.25, borderRadius: 3, minHeight: 158, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', boxShadow: '0 1px 2px rgba(15, 23, 42, .04)' }}><Typography variant="body2" color="text.secondary">{label}</Typography>{value === undefined ? <><Typography component="div" variant="subtitle1" sx={{ mt: 2.5, fontWeight: 800 }}>Not reported</Typography><Typography variant="caption" color="text.secondary">This backend metric is not available yet.</Typography></> : <><Typography component="div" variant="h4" sx={{ mt: 2.5, fontWeight: 800 }}>{value}</Typography><Typography variant="caption" color="text.secondary">{detail}</Typography></>}<Box sx={{ position: 'absolute', top: 18, right: 18, display: 'grid', placeItems: 'center', width: 36, height: 36, borderRadius: 2, bgcolor: 'action.hover', color: tone }}><Icon size={19} aria-hidden="true" /></Box></Paper>)}</Box></Box>
    <Box><Typography component="h2" variant="h6" sx={{ mb: 1.5, fontWeight: 750 }}>Current policy signals</Typography><Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, minmax(0, 1fr))' }, gap: 2 }}>{policySignals.map(({ label, value, icon: Icon, tone }) => <Paper key={label} variant="outlined" sx={{ position: 'relative', p: 2.25, borderRadius: 3, minHeight: 146, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', boxShadow: '0 1px 2px rgba(15, 23, 42, .04)' }}><Typography variant="body2" color="text.secondary">{label}</Typography><Typography component="div" variant="h4" sx={{ mt: 2.5, fontWeight: 800 }}>{value}</Typography><Box sx={{ position: 'absolute', top: 18, right: 18, display: 'grid', placeItems: 'center', width: 36, height: 36, borderRadius: 2, bgcolor: 'action.hover', color: tone }}><Icon size={19} aria-hidden="true" /></Box></Paper>)}</Box></Box>
    <Paper variant="outlined" sx={{ borderRadius: 3, p: 2.25, boxShadow: '0 1px 2px rgba(15, 23, 42, .04)' }}><Typography component="h2" variant="subtitle1" sx={{ fontWeight: 800 }}>Next actions</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: .5 }}>Choose a guided workflow. Device information and violations come from the authenticated DPC.</Typography><Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 2, flexWrap: 'wrap' }}><Button component={RouterLink} to="/settings" variant="contained">Edit school profile</Button><Button component={RouterLink} to="/devices" variant="outlined">Devices and enrollment</Button><Button component={RouterLink} to="/policies" variant="outlined">Policies and assignments</Button><Button component={RouterLink} to="/policies/catalogue" variant="outlined">Applications &amp; domains</Button><Button component={RouterLink} to="/reports" variant="outlined">View violations</Button><Button component={RouterLink} to="/logs" variant="outlined">Audit evidence</Button></Stack></Paper>
    <Paper variant="outlined" sx={{ borderRadius: 3, overflow: 'hidden', boxShadow: '0 1px 2px rgba(15, 23, 42, .04)' }}><Stack direction="row" spacing={1.5} sx={{ p: 2.25, alignItems: 'center' }}><Box sx={{ display: 'grid', placeItems: 'center', width: 36, height: 36, borderRadius: 2, bgcolor: 'action.hover', color: 'primary.main' }}><Activity size={19} aria-hidden="true" /></Box><Box><Typography component="h2" variant="subtitle1" sx={{ fontWeight: 800 }}>Recent audit activity</Typography><Typography variant="body2" color="text.secondary">Latest events visible to this administrator.</Typography></Box></Stack><Divider />{audit.data?.audit_events.length ? <Box component="ul" sx={{ listStyle: 'none', m: 0, p: 0 }}>{audit.data.audit_events.map((event, index) => <Box component="li" key={event.event_uuid} sx={{ p: 2.25, display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, justifyContent: 'space-between', gap: 1, borderTop: index ? 1 : 0, borderColor: 'divider' }}><Typography sx={{ fontWeight: 700 }}>{event.event_type.replaceAll('_', ' ')}</Typography><Typography variant="body2" color="text.secondary">{event.category} - {formatDate(event.occurred_at)}</Typography></Box>)}</Box> : <Typography sx={{ p: 3 }} variant="body2" color="text.secondary">No audit events are available.</Typography>}</Paper>
    <Paper variant="outlined" sx={{ borderRadius: 3, p: 2.25, boxShadow: '0 1px 2px rgba(15, 23, 42, .04)' }}><Typography component="h2" variant="subtitle1" sx={{ fontWeight: 800 }}>API dependency status</Typography><Box sx={{ display: 'grid', gap: 1.5, mt: 1.5, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' } }}>{[{ label: 'Process health', query: health }, { label: 'Readiness', query: readiness }].map(({ label, query }) => <Box key={label} sx={{ borderRadius: 2, bgcolor: query.data?.status === 'ready' || query.data?.status === 'running' ? 'success.50' : 'warning.50', p: 1.5 }}><Typography variant="body2" sx={{ fontWeight: 700 }}>{label}: {query.data?.status ?? 'unavailable'}</Typography><Typography variant="caption" color="text.secondary">{query.data?.detail ?? 'The control room remains available, but this dependency check could not be completed.'}</Typography>{query.isError && <Button size="small" onClick={() => void query.refetch()} sx={{ mt: 1 }}>Retry check</Button>}</Box>)}</Box></Paper>
    <Stack direction="row" spacing={1} sx={{ color: 'text.secondary', alignItems: 'center' }}><Clock3 size={16} aria-hidden="true" /><Typography variant="caption">Screen-time and web-filter evidence appears only after a device reports it.</Typography></Stack>
  </Stack>
}
