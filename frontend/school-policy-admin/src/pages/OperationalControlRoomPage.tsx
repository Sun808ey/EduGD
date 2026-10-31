import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  ClipboardList,
  Cloud,
  FileKey2,
  FileText,
  RefreshCw,
  ShieldCheck,
  Smartphone,
  UsersRound,
  type LucideIcon,
} from 'lucide-react'
import { useQueries, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link as RouterLink } from 'react-router-dom'
import { Box, Button, Chip, Divider, FormControl, InputLabel, MenuItem, Paper, Select, Stack, Typography } from '@mui/material'
import { adminService } from '@/services/admin.service'
import { publicHealthService } from '@/services/public-health.service'
import { ErrorState, LoadingState } from '@/components/ui/AsyncState'
import { formatDate } from '@/lib/format'

const operationLinks: Array<{ label: string; to: string; icon: LucideIcon; description: string }> = [
  { label: 'Enforcement center', to: '/enforcement', icon: ShieldCheck, description: 'Review policy, catalogue, device, evidence, and synchronization workflows.' },
  { label: 'School profile', to: '/settings', icon: ClipboardList, description: 'Edit the registered school details and administrator-facing contact fields.' },
  { label: 'Device records', to: '/devices', icon: Smartphone, description: 'Review DPC-provided device records, lifecycle state, and evidence.' },
  { label: 'Policy builder', to: '/policies', icon: FileText, description: 'Create, revise, assign, and retire clear administrator policies.' },
  { label: 'Synchronization queue', to: '/sync', icon: RefreshCw, description: 'Inspect queued browser changes and their delivery state.' },
  { label: 'Policy changes', to: '/policy-changes', icon: FileText, description: 'Review assignments, replacements, clears, reasons, and outcomes.' },
  { label: 'Violation reports', to: '/reports', icon: AlertTriangle, description: 'Filter blocked applications, domains, settings, and kiosk events.' },
  { label: 'Provisioning', to: '/provisioning', icon: FileKey2, description: 'Issue, review, display once, and revoke enrollment credentials.' },
  { label: 'Audit events', to: '/logs', icon: ClipboardList, description: 'Review administrative, enrollment, assignment, sync, asset, and incident evidence.' },
  { label: 'Assignments', to: '/assignments', icon: UsersRound, description: 'Review class and department responsibility for shared devices.' },
  { label: 'Administrators', to: '/administrators', icon: UsersRound, description: 'Review operator identities, permissions, sessions, and account actions.' },
  { label: 'Translations', to: '/translations', icon: Cloud, description: 'Review approved-content translation operations.' },
]

type ReviewFilter = '' | 'today' | 'last7' | 'last10' | 'month'

const manualRefreshOptions = {
  staleTime: Infinity,
  refetchOnWindowFocus: false,
  refetchOnReconnect: false,
  refetchOnMount: false,
} as const

export function OperationalControlRoomPage() {
  const queryClient = useQueryClient()
  const results = useQueries({
    queries: [
      { ...manualRefreshOptions, queryKey: ['operations-school'], queryFn: ({ signal }) => adminService.getSchool(signal) },
      { ...manualRefreshOptions, queryKey: ['operations-summary'], queryFn: ({ signal }) => adminService.getDpcSummary(signal) },
      { ...manualRefreshOptions, queryKey: ['operations-devices'], queryFn: ({ signal }) => adminService.listDevices({ page: 1, perPage: 100 }, undefined, signal) },
      { ...manualRefreshOptions, queryKey: ['operations-policies'], queryFn: ({ signal }) => adminService.listAllPolicies(signal) },
      { ...manualRefreshOptions, queryKey: ['operations-audit'], queryFn: ({ signal }) => adminService.listAuditEvents({ page: 1, perPage: 100 }, undefined, signal) },
      { ...manualRefreshOptions, queryKey: ['operations-changes'], queryFn: ({ signal }) => adminService.listPolicyChanges({ page: 1, perPage: 100 }, signal) },
      { ...manualRefreshOptions, queryKey: ['operations-violations'], queryFn: ({ signal }) => adminService.listViolationReports({ page: 1, perPage: 100 }, {}, signal) },
      { ...manualRefreshOptions, queryKey: ['operations-tokens'], queryFn: ({ signal }) => adminService.listEnrollmentTokens({ page: 1, perPage: 25 }, undefined, signal) },
      { ...manualRefreshOptions, queryKey: ['operations-applications'], queryFn: ({ signal }) => adminService.listManagedApplications(signal) },
      { ...manualRefreshOptions, queryKey: ['operations-domains'], queryFn: ({ signal }) => adminService.listManagedDomains(signal) },
      { ...manualRefreshOptions, queryKey: ['operations-incidents'], queryFn: ({ signal }) => adminService.listIncidents({ page: 1, perPage: 25 }, undefined, signal) },
      { ...manualRefreshOptions, queryKey: ['operations-health'], queryFn: ({ signal }) => publicHealthService.checkHealth(signal) },
      { ...manualRefreshOptions, queryKey: ['operations-readiness'], queryFn: ({ signal }) => publicHealthService.checkReadiness(signal) },
    ],
  })
  const [school, summary, devices, policies, audit, changes, violations, tokens, applications, domains, incidents, health, readiness] = results
  const refreshOperations = () => void queryClient.invalidateQueries({ predicate: (query) => String(query.queryKey[0] ?? '').startsWith('operations-') })
  const primaryLoading = school.isLoading || devices.isLoading || policies.isLoading || audit.isLoading
  const primaryError = school.isError || devices.isError || policies.isError || audit.isError
  const [reviewFilter, setReviewFilter] = useState<ReviewFilter>('')

  if (primaryLoading) return <LoadingState label="Loading operational control room..." />
  if (primaryError || !school.data || !devices.data || !policies.data || !audit.data) {
    return <ErrorState message="Operational control-room data is temporarily unavailable." retry={refreshOperations} />
  }

  const onlineDevices = devices.data.devices.filter((device) => device.connection_status === 'ONLINE').length
  const compliantDevices = devices.data.devices.filter((device) => device.enforcement_status === 'COMPLIANT').length
  const activeTokens = tokens.data?.enrollment_tokens.filter((token) => token.status === 'active').length ?? 0
  const now = new Date()
  const reviewRange = (() => {
    if (!reviewFilter) return null
    const end = new Date(now)
    end.setHours(23, 59, 59, 999)
    const start = new Date(now)
    let label = 'Today'
    if (reviewFilter === 'today') {
      start.setHours(0, 0, 0, 0)
    } else if (reviewFilter === 'last7') {
      start.setDate(start.getDate() - 6)
      start.setHours(0, 0, 0, 0)
      label = 'Last 7 days'
    } else if (reviewFilter === 'last10') {
      start.setDate(start.getDate() - 10)
      start.setHours(0, 0, 0, 0)
      label = 'Last 10 days'
    } else {
      start.setDate(1)
      start.setHours(0, 0, 0, 0)
      label = 'This month'
    }
    return { start, end, label }
  })()
  const operationalDays = Array.from({ length: 11 }, (_, index) => {
    const date = new Date(now)
    date.setHours(12, 0, 0, 0)
    date.setDate(date.getDate() - (10 - index))
    const dayKey = date.toISOString().slice(0, 10)
    const dayAudit = audit.data.audit_events.filter((event) => event.occurred_at?.slice(0, 10) === dayKey)
    const dayViolations = violations.data?.violations.filter((violation) => violation.occurred_at?.slice(0, 10) === dayKey) ?? []
    const dayChanges = changes.data?.policy_changes.filter((change) => change.occurred_at?.slice(0, 10) === dayKey) ?? []
    return { date, dayKey, dayAudit, dayViolations, dayChanges }
  })
  const visibleOperationalDays = reviewRange
    ? operationalDays.filter(({ date }) => date >= reviewRange.start && date <= reviewRange.end)
    : []

  return (
    <Stack spacing={3.5} className="operational-control-room">
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ justifyContent: 'space-between', alignItems: { md: 'flex-end' } }}>
        <Box component="header">
          <Typography variant="overline" sx={{ color: 'primary.main', fontWeight: 800, letterSpacing: '.14em' }}>NDEJJE SS operations</Typography>
          <Typography component="h1" variant="h4" sx={{ mt: 0.25, fontWeight: 800 }}>Operational control room</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>Live administrator view of school profile, devices, policies, enforcement evidence, provisioning, synchronization, violations, and audit history.</Typography>
        </Box>
        <Button variant="outlined" startIcon={<RefreshCw size={16} />} onClick={refreshOperations}>Refresh operations</Button>
      </Stack>

      <Paper variant="outlined" sx={{ p: { xs: 2, sm: 3 }, borderRadius: 3 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ alignItems: { sm: 'center' }, justifyContent: 'space-between' }}>
          <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
            <CalendarDays size={19} aria-hidden="true" />
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 800 }}>Review records</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Choose a review period to inspect recorded enforcement, audit, and policy activity.</Typography>
            </Box>
          </Stack>
          <FormControl size="small" sx={{ minWidth: { xs: '100%', sm: 210 } }}>
            <InputLabel id="review-period-label">Review period</InputLabel>
            <Select labelId="review-period-label" label="Review period" value={reviewFilter} onChange={(event) => setReviewFilter(event.target.value as ReviewFilter)}>
              <MenuItem value="">Choose a period</MenuItem>
              <MenuItem value="today">Today</MenuItem>
              <MenuItem value="last7">Last 7 days</MenuItem>
              <MenuItem value="last10">Last 10 days</MenuItem>
              <MenuItem value="month">This month</MenuItem>
            </Select>
          </FormControl>
        </Stack>
        {reviewRange && <Box sx={{ mt: 2 }}>
          <Typography variant="body2" color="text.secondary">{reviewRange.label}: {formatDate(reviewRange.start.toISOString())} to {formatDate(reviewRange.end.toISOString())}</Typography>
          <Box sx={{ display: 'grid', gap: 1.25, mt: 1.5, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))', lg: 'repeat(3, minmax(0, 1fr))' } }}>
            {visibleOperationalDays.map(({ date, dayKey, dayAudit, dayViolations, dayChanges }) => (
              <Paper key={dayKey} variant="outlined" sx={{ p: 1.5, borderRadius: 2, bgcolor: 'background.default' }}>
                <Stack direction="row" spacing={1} sx={{ alignItems: 'center', justifyContent: 'space-between' }}>
                  <Typography variant="body2" sx={{ fontWeight: 800 }}>{date.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}</Typography>
                  <Chip size="small" color={dayViolations.length > 0 ? 'warning' : 'success'} label={dayViolations.length > 0 ? 'Action recorded' : 'No exception'} />
                </Stack>
                <Stack direction="row" spacing={0.75} sx={{ mt: 1, flexWrap: 'wrap' }}>
                  <Chip size="small" variant="outlined" label={`Enforcement ${dayViolations.length}`} />
                  <Chip size="small" variant="outlined" label={`Audit ${dayAudit.length}`} />
                  <Chip size="small" variant="outlined" label={`Policy ${dayChanges.length}`} />
                </Stack>
                <Button component={RouterLink} to={`/reports?from=${dayKey}&to=${dayKey}`} size="small" sx={{ mt: 0.75, px: 0 }}>Open records <ArrowRight size={14} /></Button>
              </Paper>
            ))}
          </Box>
        </Box>}
      </Paper>

      <Paper variant="outlined" sx={{ p: { xs: 2, sm: 3 }, borderRadius: 3 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ justifyContent: 'space-between' }}>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 800 }}>{school.data.name}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{school.data.district} · {school.data.school_type} · {school.data.timezone}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Administrator: {school.data.authorised_administrator_name} · Contact: {school.data.contact_person}</Typography>
          </Box>
          <Chip icon={<CheckCircle2 size={16} />} color="success" label={health.data?.status === 'running' && readiness.data?.status === 'ready' ? 'Services healthy' : 'Dependency review required'} />
        </Stack>
      </Paper>

      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))', lg: 'repeat(4, minmax(0, 1fr))' } }}>
        <Metric label="Registered devices" value={String(summary.data?.managed_devices ?? devices.data.devices.length)} detail={`${onlineDevices} online`} icon={Smartphone} />
        <Metric label="Compliant devices" value={String(compliantDevices)} detail={`${devices.data.devices.length} reporting`} icon={ShieldCheck} />
        <Metric label="Active policies" value={String(summary.data?.active_v3_assignments ?? policies.data.length)} detail={`${changes.data?.pagination.total ?? 0} policy changes`} icon={FileText} />
        <Metric label="Recorded violations" value={String(violations.data?.pagination.total ?? 0)} detail={`${incidents.data?.pagination.total ?? 0} incidents`} icon={AlertTriangle} />
      </Box>

      <Paper variant="outlined" sx={{ p: { xs: 2, sm: 3 }, borderRadius: 3 }}>
        <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
          <Activity size={19} aria-hidden="true" />
          <Box><Typography variant="h6" sx={{ fontWeight: 800 }}>Device operations</Typography><Typography variant="body2" color="text.secondary">Each record links to its complete asset, policy, provisioning, evidence, violation, and control history.</Typography></Box>
        </Stack>
        <Box sx={{ display: 'grid', gap: 2, mt: 2, gridTemplateColumns: { xs: '1fr', lg: 'repeat(2, minmax(0, 1fr))' } }}>
          {devices.data.devices.map((device) => (
            <Paper key={device.device_uuid} variant="outlined" sx={{ p: 2, borderRadius: 2.5 }}>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} sx={{ justifyContent: 'space-between' }}>
                <Box>
                  <Typography sx={{ fontWeight: 800 }}>{device.manufacturer} {device.model}</Typography>
                  <Typography variant="body2" color="text.secondary">{device.device_reference ?? device.asset_number} · {device.asset_number} · Android {device.android_version} / API {device.api_level}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{device.department} · {device.active_policy_assignment?.policy_name ?? 'No active policy'}</Typography>
                </Box>
                <Stack direction="row" spacing={1} sx={{ alignItems: 'flex-start' }}>
                  <Chip size="small" color={device.enforcement_status === 'COMPLIANT' ? 'success' : 'warning'} label={device.enforcement_status?.replaceAll('_', ' ') ?? 'Not reported'} />
                  <Chip size="small" variant="outlined" label={device.connection_status ?? 'Not reported'} />
                </Stack>
              </Stack>
              <Stack direction="row" spacing={1} sx={{ mt: 2, flexWrap: 'wrap' }}>
                <Button component={RouterLink} to={`/devices/${device.device_uuid}`} size="small" variant="contained" endIcon={<ArrowRight size={15} />}>Open device record</Button>
                <Button component={RouterLink} to={`/reports?device_uuid=${encodeURIComponent(device.device_uuid)}`} size="small" variant="outlined">View violations</Button>
              </Stack>
            </Paper>
          ))}
        </Box>
      </Paper>

      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', lg: '1.15fr .85fr' } }}>
        <Paper variant="outlined" sx={{ p: { xs: 2, sm: 3 }, borderRadius: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 800 }}>Operational timeline</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Recent server-recorded activity across enrollment, policy, synchronization, assets, incidents, and operators.</Typography>
          <Stack component="ol" spacing={1.25} sx={{ mt: 2, pl: 0, listStyle: 'none' }}>
            {audit.data.audit_events.slice(0, 8).map((event) => (
              <Box component="li" key={event.event_uuid} sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, borderTop: 1, borderColor: 'divider', pt: 1.25 }}>
                <Typography variant="body2" sx={{ fontWeight: 700 }}>{event.event_type.replaceAll('_', ' ')}</Typography>
                <Typography variant="caption" color="text.secondary">{event.category}{event.device_reference ? ` · ${event.device_reference}` : ''}</Typography>
              </Box>
            ))}
          </Stack>
        </Paper>
        <Paper variant="outlined" sx={{ p: { xs: 2, sm: 3 }, borderRadius: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 800 }}>Coverage status</Typography>
          <Stack spacing={1.25} sx={{ mt: 2 }}>
            <CoverageRow label="Provisioning records" value={`${tokens.data?.pagination.total ?? 0} tokens · ${activeTokens} active`} />
            <CoverageRow label="Application catalogue" value={`${applications.data?.length ?? 0} applications`} />
            <CoverageRow label="Domain catalogue" value={`${domains.data?.length ?? 0} enabled domains`} />
            <CoverageRow label="Audit records" value={`${audit.data.pagination.total} events`} />
          </Stack>
        </Paper>
      </Box>

      <Box>
        <Typography variant="h6" sx={{ fontWeight: 800, mb: 1.5 }}>Open every operational function</Typography>
        <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))', xl: 'repeat(3, minmax(0, 1fr))' } }}>
          {operationLinks.map(({ label, to, icon: Icon, description }) => (
            <Paper key={to} variant="outlined" sx={{ p: 2, borderRadius: 2.5, height: '100%' }}>
              <Stack direction="row" spacing={1.25} sx={{ alignItems: 'flex-start' }}>
                <Box sx={{ display: 'grid', placeItems: 'center', width: 34, height: 34, borderRadius: 1.5, bgcolor: 'action.hover', color: 'primary.main', flexShrink: 0 }}><Icon size={18} /></Box>
                <Box sx={{ minWidth: 0 }}>
                  <Typography sx={{ fontWeight: 800 }}>{label}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{description}</Typography>
                  <Button component={RouterLink} to={to} size="small" sx={{ mt: 1, px: 0 }}>Open function <ArrowRight size={15} /></Button>
                </Box>
              </Stack>
            </Paper>
          ))}
        </Box>
      </Box>

      <Divider />
      <Typography variant="caption" color="text.secondary">Emergency calling is preserved. The system does not read private messages, photographs, contacts, location, microphone recordings, or browsing history.</Typography>
    </Stack>
  )
}

function Metric({ label, value, detail, icon: Icon }: { label: string; value: string; detail: string; icon: LucideIcon }) {
  return <Paper variant="outlined" sx={{ p: 2, borderRadius: 2.5 }}><Stack direction="row" spacing={1.5} sx={{ alignItems: 'flex-start', justifyContent: 'space-between' }}><Box><Typography variant="body2" color="text.secondary">{label}</Typography><Typography variant="h4" sx={{ mt: 0.75, fontWeight: 800 }}>{value}</Typography><Typography variant="caption" color="text.secondary">{detail}</Typography></Box><Icon size={20} aria-hidden="true" /></Stack></Paper>
}

function CoverageRow({ label, value }: { label: string; value: string }) {
  return <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}><Typography variant="body2">{label}</Typography><Typography variant="body2" sx={{ fontWeight: 800, textAlign: 'right' }}>{value}</Typography></Box>
}

export default OperationalControlRoomPage
