import { Activity, AlertTriangle, Clock3, Laptop, LockKeyhole, ShieldCheck } from 'lucide-react'
import { useQueries } from '@tanstack/react-query'
import { Box, Divider, Paper, Stack, Typography } from '@mui/material'
import { adminService } from '@/services/admin.service'
import { ErrorState, LoadingState } from '@/components/ui/AsyncState'
import { formatDate } from '@/lib/format'

export function DashboardPage() {
  const results = useQueries({ queries: [
    { queryKey: ['dpc-summary'], queryFn: ({ signal }) => adminService.getDpcSummary(signal) },
    { queryKey: ['audit', 1, 'all'], queryFn: ({ signal }) => adminService.listAuditEvents({ page: 1, perPage: 10 }, undefined, signal) },
  ] })
  const [summary, audit] = results
  if (results.some((result) => result.isLoading)) return <LoadingState label="Loading control roomâ€¦" />
  if (results.some((result) => result.isError) || !summary.data) return <ErrorState message="Control-room data is temporarily unavailable." retry={() => results.forEach((result) => void result.refetch())} />
  const stats = [
    { label: 'Managed devices', value: summary.data.managed_devices, icon: Laptop, tone: 'primary.main' },
    { label: 'Active v3 policies', value: summary.data.active_v3_assignments, icon: ShieldCheck, tone: 'success.main' },
    { label: 'Block overrides', value: summary.data.active_block_overrides, icon: LockKeyhole, tone: 'warning.main' },
    { label: 'Enforcement failures', value: summary.data.enforcement_failures, icon: AlertTriangle, tone: 'error.main' },
  ]
  return <Stack spacing={3.5}>
    <Box component="header"><Typography variant="overline" sx={{ color: '#0d47a1', fontWeight: 800, letterSpacing: '.14em' }}>EduGD control room</Typography><Typography component="h1" variant="h4" sx={{ mt: .25, fontWeight: 800 }}>Device policy at a glance</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>Live, privacy-limited administration data from the EduGD API.</Typography></Box>
    <Box><Typography component="h2" variant="h6" sx={{ mb: 1.5, fontWeight: 750 }}>Overview</Typography><Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))', xl: 'repeat(4, minmax(0, 1fr))' }, gap: 2 }}>{stats.map(({ label, value, icon: Icon, tone }) => <Paper key={label} variant="outlined" sx={{ position: 'relative', p: 2.25, borderRadius: 3, minHeight: 146, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', boxShadow: '0 1px 2px rgba(15, 23, 42, .04)' }}><Typography variant="body2" color="text.secondary">{label}</Typography><Typography component="div" variant="h4" sx={{ mt: 2.5, fontWeight: 800 }}>{value}</Typography><Box sx={{ position: 'absolute', top: 18, right: 18, display: 'grid', placeItems: 'center', width: 36, height: 36, borderRadius: 2, bgcolor: 'action.hover', color: tone }}><Icon size={19} aria-hidden="true" /></Box></Paper>)}</Box></Box>
    <Paper variant="outlined" sx={{ borderRadius: 3, overflow: 'hidden', boxShadow: '0 1px 2px rgba(15, 23, 42, .04)' }}><Stack direction="row" spacing={1.5} sx={{ p: 2.25, alignItems: 'center' }}><Box sx={{ display: 'grid', placeItems: 'center', width: 36, height: 36, borderRadius: 2, bgcolor: 'action.hover', color: 'primary.main' }}><Activity size={19} aria-hidden="true" /></Box><Box><Typography component="h2" variant="subtitle1" sx={{ fontWeight: 800 }}>Recent audit activity</Typography><Typography variant="body2" color="text.secondary">Latest events visible to this administrator.</Typography></Box></Stack><Divider />{audit.data?.audit_events.length ? <Box component="ul" sx={{ listStyle: 'none', m: 0, p: 0 }}>{audit.data.audit_events.map((event, index) => <Box component="li" key={event.event_uuid} sx={{ p: 2.25, display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, justifyContent: 'space-between', gap: 1, borderTop: index ? 1 : 0, borderColor: 'divider' }}><Typography sx={{ fontWeight: 700 }}>{event.event_type.replaceAll('_', ' ')}</Typography><Typography variant="body2" color="text.secondary">{event.category} · {formatDate(event.occurred_at)}</Typography></Box>)}</Box> : <Typography sx={{ p: 3 }} variant="body2" color="text.secondary">No audit events are available.</Typography>}</Paper>
    <Stack direction="row" spacing={1} sx={{ color: 'text.secondary', alignItems: 'center' }}><Clock3 size={16} aria-hidden="true" /><Typography variant="caption">Screen-time and web-filter evidence appears only after a device reports it.</Typography></Stack>
  </Stack>
}
